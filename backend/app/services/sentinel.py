"""
Sentinel-2 satellite imagery via Copernicus Data Space Ecosystem.

Uses:
- OData Catalog API for searching available imagery
- Sentinel Hub Process API for fetching imagery as PNG (no need to download full ZIPs)

The Process API lets us request a specific bounding box and resolution directly,
which is perfect for monitoring individual airbases.
"""
import logging
import httpx
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings

logger = logging.getLogger("vauban.sentinel")

CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_ODATA_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1"
CDSE_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# Evalscript: True Color Image with brightness boost for visibility
TCI_EVALSCRIPT = """//VERSION=3
function setup() {
  return { input: ["B04", "B03", "B02"], output: { bands: 3 } };
}
function evaluatePixel(sample) {
  return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
}
"""


class SentinelService:
    def __init__(self):
        self.access_token = None
        self.token_expiry = None

    async def _authenticate(self):
        """Get access token from Copernicus Data Space."""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                CDSE_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.copernicus_client_id,
                    "client_secret": settings.copernicus_client_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self.access_token = data["access_token"]
            self.token_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 600) - 60)
            logger.info("Authenticated with Copernicus Data Space")
            return self.access_token

    async def search_images(
        self,
        latitude: float,
        longitude: float,
        date_from: str,
        date_to: str,
        max_cloud_cover: float = 20.0,
        bbox_size_km: float = 5.0,
    ) -> list[dict]:
        """Search for Sentinel-2 L2A images covering an area around a point."""
        deg_offset = bbox_size_km * 0.009
        bbox = (
            f"POLYGON(({longitude - deg_offset} {latitude - deg_offset},"
            f"{longitude + deg_offset} {latitude - deg_offset},"
            f"{longitude + deg_offset} {latitude + deg_offset},"
            f"{longitude - deg_offset} {latitude + deg_offset},"
            f"{longitude - deg_offset} {latitude - deg_offset}))"
        )

        filter_str = (
            f"Collection/Name eq 'SENTINEL-2' "
            f"and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
            f"and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A') "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{bbox}') "
            f"and ContentDate/Start gt {date_from}T00:00:00.000Z "
            f"and ContentDate/Start lt {date_to}T23:59:59.999Z "
            f"and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
            f"and att/OData.CSC.DoubleAttribute/Value lt {max_cloud_cover})"
        )

        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                f"{CDSE_ODATA_URL}/Products",
                params={
                    "$filter": filter_str,
                    "$orderby": "ContentDate/Start desc",
                    "$top": 10,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            results = resp.json().get("value", [])

        logger.info(f"Found {len(results)} Sentinel-2 images")
        return [
            {
                "id": r["Id"],
                "name": r["Name"],
                "date": r["ContentDate"]["Start"],
                "cloud_cover": next(
                    (a["Value"] for a in r.get("Attributes", []) if a.get("Name") == "cloudCover"),
                    None,
                ),
                "footprint": r.get("Footprint"),
            }
            for r in results
        ]

    async def fetch_image(
        self,
        latitude: float,
        longitude: float,
        date_from: str,
        date_to: str,
        airbase_name: str,
        bbox_size_km: float = 2.0,
    ) -> Path:
        """
        Fetch a Sentinel-2 TCI image for an area using the Process API.

        Uses native 10m resolution. For a 2km bbox = 400x400 pixels at 10m/px.
        This is the maximum detail Sentinel-2 can provide.
        """
        token = await self._authenticate()

        # Convert km to degrees (approximate at mid-latitudes)
        import math
        lat_offset = bbox_size_km / 111.0  # 1 deg lat ≈ 111km
        lon_offset = bbox_size_km / (111.0 * math.cos(math.radians(latitude)))
        bbox = [
            longitude - lon_offset,
            latitude - lat_offset,
            longitude + lon_offset,
            latitude + lat_offset,
        ]

        # Request at 10m native resolution
        width_m = bbox_size_km * 2 * 1000  # full width in meters
        resolution_px = int(width_m / 10)  # 10m per pixel

        logger.info(f"Bbox: {bbox}, Resolution: {resolution_px}x{resolution_px}px")

        payload = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {
                                "from": f"{date_from}T00:00:00Z",
                                "to": f"{date_to}T23:59:59Z",
                            },
                            "maxCloudCoverage": 20,
                            "mosaickingOrder": "mostRecent",
                        },
                    }
                ],
            },
            "output": {
                "width": resolution_px,
                "height": resolution_px,
                "responses": [
                    {"identifier": "default", "format": {"type": "image/png"}}
                ],
            },
            "evalscript": TCI_EVALSCRIPT,
        }

        logger.info(f"Fetching Sentinel-2 image for {airbase_name} ({date_from} to {date_to})")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                CDSE_PROCESS_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60.0,
            )
            resp.raise_for_status()

        # Save image
        storage_dir = Path(settings.image_storage_path) / airbase_name.replace(" ", "_")
        storage_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{airbase_name.replace(' ', '_')}_{date_from}_{timestamp}.png"
        image_path = storage_dir / filename
        with open(image_path, "wb") as f:
            f.write(resp.content)

        logger.info(f"Saved {len(resp.content)} bytes to {image_path}")
        return image_path

    async def fetch_for_date(
        self,
        latitude: float,
        longitude: float,
        product_name: str,
        airbase_name: str,
        bbox_size_km: float = 3.0,
        resolution: int = 1024,
    ) -> Path:
        """
        Fetch imagery for a specific product date.
        Uses a 3-day window around the product date to ensure coverage,
        with mostRecent mosaicking to get the closest-in-time image.
        """
        # Product name format: S2A_MSIL2A_20261012T085431_...
        # Use a 10-day window centered on the product date to ensure coverage
        date_str = product_name.split("_")[2][:8]
        from datetime import datetime as dt, timedelta
        center = dt.strptime(date_str, "%Y%m%d")
        date_from = (center - timedelta(days=5)).strftime("%Y-%m-%d")
        date_to = (center + timedelta(days=5)).strftime("%Y-%m-%d")

        return await self.fetch_image(
            latitude=latitude,
            longitude=longitude,
            date_from=date_from,
            date_to=date_to,
            airbase_name=airbase_name,
            bbox_size_km=bbox_size_km,
            resolution=resolution,
        )


sentinel_service = SentinelService()
