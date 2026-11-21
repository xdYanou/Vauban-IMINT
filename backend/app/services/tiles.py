"""
High-resolution satellite imagery fetcher using multiple tile servers.

Supports multi-source capture: Esri, Google, and Bing provide imagery from
different capture dates, giving us temporal coverage for free.
Each source is treated as a separate observation date for change detection.
"""
import logging
import math
import asyncio
import httpx
from pathlib import Path
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta

from app.config import settings

logger = logging.getLogger("vauban.tiles")

TILE_SOURCES = {
    "esri": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "type": "zyx",
    },
    "google": {
        "url": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "type": "xyz",
    },
    "bing": {
        "url": "https://ecn.t0.tiles.virtualearth.net/tiles/a{q}.jpeg?g=587",
        "type": "quadkey",
    },
}

TILE_SIZE = 256


def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def tile_to_quadkey(x: int, y: int, z: int) -> str:
    qk = ""
    for i in range(z, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if (x & mask) != 0:
            digit += 1
        if (y & mask) != 0:
            digit += 2
        qk += str(digit)
    return qk


def meters_per_pixel(lat: float, zoom: int) -> float:
    return 156543.03 * math.cos(math.radians(lat)) / (2 ** zoom)


def zone_coverage_km(lat: float, zoom: int, grid_size: int) -> float:
    mpp = meters_per_pixel(lat, zoom)
    return grid_size * TILE_SIZE * mpp / 1000


def _build_tile_url(source_name: str, tx: int, ty: int, zoom: int) -> str:
    src = TILE_SOURCES[source_name]
    if src["type"] == "quadkey":
        return src["url"].format(q=tile_to_quadkey(tx, ty, zoom))
    elif src["type"] == "zyx":
        return src["url"].format(z=zoom, y=ty, x=tx)
    else:
        return src["url"].format(x=tx, y=ty, z=zoom)


class TileService:
    def __init__(self):
        pass

    async def fetch_area(
        self,
        latitude: float,
        longitude: float,
        airbase_name: str,
        zoom: int = 17,
        grid_size: int = 6,
        zone_label: str = None,
        source: str = "esri",
    ) -> tuple[Path, int, int]:
        """
        Fetch a grid of tiles from a specific source and stitch into one image.
        Returns (image_path, width_px, height_px).
        """
        center_x, center_y = lat_lon_to_tile(latitude, longitude, zoom)
        half = grid_size // 2

        coverage = zone_coverage_km(latitude, zoom, grid_size)
        logger.info(
            f"Fetching {grid_size}x{grid_size} tiles z{zoom} [{source}] "
            f"(~{coverage:.1f}km) for {airbase_name}"
            f"{f' [{zone_label}]' if zone_label else ''}"
        )

        tile_coords = []
        for dy in range(-half, half):
            for dx in range(-half, half):
                tile_coords.append((dx, dy, center_x + dx, center_y + dy))

        async with httpx.AsyncClient(
            headers={"User-Agent": "Vauban-IMINT/1.0"},
            timeout=15.0,
            limits=httpx.Limits(max_connections=10),
        ) as client:
            async def fetch_tile(dx, dy, tx, ty):
                url = _build_tile_url(source, tx, ty, zoom)
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

        img_w = grid_size * TILE_SIZE
        img_h = grid_size * TILE_SIZE
        stitched = Image.new("RGB", (img_w, img_h))

        for (gx, gy), data in tiles.items():
            try:
                stitched.paste(Image.open(BytesIO(data)), (gx * TILE_SIZE, gy * TILE_SIZE))
            except Exception:
                pass

        storage_dir = Path(settings.image_storage_path) / airbase_name.replace(" ", "_")
        storage_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zone_suffix = f"_{zone_label}" if zone_label else ""
        filename = f"{airbase_name.replace(' ', '_')}_z{zoom}{zone_suffix}_{source}_{timestamp}.png"
        output_path = storage_dir / filename
        stitched.save(output_path, "PNG")

        logger.info(f"Stitched {len(tiles)} tiles -> {output_path} ({img_w}x{img_h}px)")
        return output_path, img_w, img_h


tile_service = TileService()
