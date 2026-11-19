"""
High-resolution satellite imagery fetcher using map tile servers.

Fetches tiles at high zoom levels (17-18) which give ~1-2m/pixel resolution,
enough to detect and classify individual aircraft.

Tile sources:
- Esri World Imagery: Best general coverage, ~0.3-1m resolution
- Google Satellite: Excellent but stricter ToS
"""
import logging
import math
import httpx
from pathlib import Path
from PIL import Image
from io import BytesIO

from app.config import settings

logger = logging.getLogger("vauban.tiles")

TILE_SOURCES = {
    "esri": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "google": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
}

TILE_SIZE = 256  # Standard tile size in pixels


def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert lat/lon to tile coordinates at a given zoom level."""
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def tile_to_lat_lon(x: int, y: int, zoom: int) -> tuple[float, float]:
    """Convert tile coordinates back to lat/lon (NW corner of tile)."""
    n = 2 ** zoom
    lon = x / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def meters_per_pixel(lat: float, zoom: int) -> float:
    """Approximate meters per pixel at a given latitude and zoom."""
    return 156543.03 * math.cos(math.radians(lat)) / (2 ** zoom)


class TileService:
    def __init__(self, source: str = "esri"):
        self.url_template = TILE_SOURCES[source]
        self.source = source

    async def fetch_area(
        self,
        latitude: float,
        longitude: float,
        airbase_name: str,
        zoom: int = 17,
        grid_size: int = 4,
    ) -> Path:
        """
        Fetch a grid of tiles centered on coordinates and stitch into one image.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            airbase_name: For file naming
            zoom: Zoom level (17 = ~1.2m/px, 18 = ~0.6m/px)
            grid_size: Number of tiles per side (4x4 = 1024x1024px at 256px tiles)

        Returns:
            Path to the stitched image
        """
        center_x, center_y = lat_lon_to_tile(latitude, longitude, zoom)
        half = grid_size // 2

        mpp = meters_per_pixel(latitude, zoom)
        area_m = grid_size * TILE_SIZE * mpp
        logger.info(
            f"Fetching {grid_size}x{grid_size} tiles at zoom {zoom} "
            f"({mpp:.2f} m/px, ~{area_m/1000:.1f}km area) for {airbase_name}"
        )

        # Fetch all tiles in parallel
        import asyncio
        tiles = {}
        tile_coords = []
        for dy in range(-half, half):
            for dx in range(-half, half):
                tile_coords.append((dx, dy, center_x + dx, center_y + dy))

        async with httpx.AsyncClient(
            headers={"User-Agent": "Vauban-IMINT/0.1"},
            timeout=15.0,
            limits=httpx.Limits(max_connections=10),
        ) as client:
            async def fetch_tile(dx, dy, tx, ty):
                url = self.url_template.format(x=tx, y=ty, z=zoom)
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        return (dx + half, dy + half, resp.content)
                except Exception:
                    pass
                return None

            results = await asyncio.gather(*[
                fetch_tile(dx, dy, tx, ty) for dx, dy, tx, ty in tile_coords
            ])
            for r in results:
                if r:
                    tiles[(r[0], r[1])] = r[2]

        if not tiles:
            raise RuntimeError("No tiles fetched — area may not have imagery coverage")

        # Stitch tiles into one image
        img_size = grid_size * TILE_SIZE
        stitched = Image.new("RGB", (img_size, img_size))

        for (gx, gy), data in tiles.items():
            try:
                tile_img = Image.open(BytesIO(data))
                stitched.paste(tile_img, (gx * TILE_SIZE, gy * TILE_SIZE))
            except Exception as e:
                logger.warning(f"Failed to paste tile ({gx},{gy}): {e}")

        # Save
        storage_dir = Path(settings.image_storage_path) / airbase_name.replace(" ", "_")
        storage_dir.mkdir(parents=True, exist_ok=True)

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{airbase_name.replace(' ', '_')}_z{zoom}_{timestamp}.png"
        output_path = storage_dir / filename
        stitched.save(output_path, "PNG")

        logger.info(f"Stitched {len(tiles)} tiles -> {output_path} ({img_size}x{img_size}px)")
        return output_path


tile_service = TileService(source="esri")
