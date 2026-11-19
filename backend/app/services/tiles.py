"""
High-resolution satellite imagery fetcher using map tile servers.

Each airbase has explicit capture zones (center point + zoom + grid_size).
The tile service fetches and stitches tiles for each zone.
"""
import logging
import math
import asyncio
import httpx
from pathlib import Path
from PIL import Image
from io import BytesIO
from datetime import datetime

from app.config import settings

logger = logging.getLogger("vauban.tiles")

TILE_SOURCES = {
    "esri": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "google": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
}

TILE_SIZE = 256


def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def meters_per_pixel(lat: float, zoom: int) -> float:
    return 156543.03 * math.cos(math.radians(lat)) / (2 ** zoom)


def zone_coverage_km(lat: float, zoom: int, grid_size: int) -> float:
    """Return approximate coverage in km for a zone config."""
    mpp = meters_per_pixel(lat, zoom)
    return grid_size * TILE_SIZE * mpp / 1000


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
        grid_size: int = 6,
        zone_label: str = None,
    ) -> tuple[Path, int, int]:
        """
        Fetch a grid of tiles centered on a point and stitch into one image.
        Returns (image_path, width_px, height_px).
        """
        center_x, center_y = lat_lon_to_tile(latitude, longitude, zoom)
        half = grid_size // 2

        coverage = zone_coverage_km(latitude, zoom, grid_size)
        logger.info(
            f"Fetching {grid_size}x{grid_size} tiles z{zoom} "
            f"(~{coverage:.1f}km) for {airbase_name}"
            f"{f' [{zone_label}]' if zone_label else ''}"
        )

        # Fetch all tiles in parallel
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
            tiles = {}
            for r in results:
                if r:
                    tiles[(r[0], r[1])] = r[2]

        if not tiles:
            raise RuntimeError("No tiles fetched")

        # Stitch
        img_w = grid_size * TILE_SIZE
        img_h = grid_size * TILE_SIZE
        stitched = Image.new("RGB", (img_w, img_h))

        for (gx, gy), data in tiles.items():
            try:
                stitched.paste(Image.open(BytesIO(data)), (gx * TILE_SIZE, gy * TILE_SIZE))
            except Exception:
                pass

        # Save
        storage_dir = Path(settings.image_storage_path) / airbase_name.replace(" ", "_")
        storage_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zone_suffix = f"_{zone_label}" if zone_label else ""
        filename = f"{airbase_name.replace(' ', '_')}_z{zoom}{zone_suffix}_{timestamp}.png"
        output_path = storage_dir / filename
        stitched.save(output_path, "PNG")

        logger.info(f"Stitched {len(tiles)} tiles -> {output_path} ({img_w}x{img_h}px)")
        return output_path, img_w, img_h


tile_service = TileService(source="esri")
