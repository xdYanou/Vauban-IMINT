"""
High-resolution satellite imagery fetcher using map tile servers.

Supports:
- Adaptive coverage: grid size calculated from base's capture_radius_km
- Multi-zone capture: split large bases into overlapping zones for full coverage
- Image metadata tracking: dimensions stored for bbox overlay scaling
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


def calc_grid_size(radius_km: float, lat: float, zoom: int) -> int:
    """Calculate how many tiles we need per side to cover radius_km from center."""
    mpp = meters_per_pixel(lat, zoom)
    area_m = radius_km * 2 * 1000  # diameter in meters
    tiles_needed = math.ceil(area_m / (TILE_SIZE * mpp))
    # Ensure even number and minimum 4
    tiles_needed = max(4, tiles_needed + (tiles_needed % 2))
    return min(tiles_needed, 16)  # cap at 16x16 to avoid huge requests


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
        grid_size: int = None,
        radius_km: float = 1.5,
        zone_label: str = None,
    ) -> tuple[Path, int, int]:
        """
        Fetch a grid of tiles and stitch into one image.

        If grid_size is None, it's auto-calculated from radius_km.
        Returns (image_path, width_px, height_px).
        """
        if grid_size is None:
            grid_size = calc_grid_size(radius_km, latitude, zoom)

        center_x, center_y = lat_lon_to_tile(latitude, longitude, zoom)
        half = grid_size // 2

        mpp = meters_per_pixel(latitude, zoom)
        area_km = grid_size * TILE_SIZE * mpp / 1000
        logger.info(
            f"Fetching {grid_size}x{grid_size} tiles at z{zoom} "
            f"({mpp:.2f}m/px, ~{area_km:.1f}km) for {airbase_name}"
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
            raise RuntimeError("No tiles fetched — area may not have imagery coverage")

        # Stitch tiles
        img_w = grid_size * TILE_SIZE
        img_h = grid_size * TILE_SIZE
        stitched = Image.new("RGB", (img_w, img_h))

        for (gx, gy), data in tiles.items():
            try:
                tile_img = Image.open(BytesIO(data))
                stitched.paste(tile_img, (gx * TILE_SIZE, gy * TILE_SIZE))
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

    async def fetch_full_base(
        self,
        latitude: float,
        longitude: float,
        airbase_name: str,
        zoom: int = 17,
        radius_km: float = 1.5,
    ) -> list[tuple[Path, int, int, str]]:
        """
        Smart capture that covers the full base.

        For small bases (radius <= 1.5km): single capture.
        For large bases (radius > 1.5km): multi-zone with overlapping tiles.

        Returns list of (path, width, height, zone_label).
        """
        if radius_km <= 2.0:
            # Single capture covers it
            path, w, h = await self.fetch_area(
                latitude, longitude, airbase_name,
                zoom=zoom, radius_km=radius_km, zone_label="full",
            )
            return [(path, w, h, "full")]

        # Multi-zone: capture overview at lower zoom + detail zones
        results = []

        # Overview at zoom-2 (covers 4x the area)
        path, w, h = await self.fetch_area(
            latitude, longitude, airbase_name,
            zoom=max(14, zoom - 2), radius_km=radius_km, zone_label="overview",
        )
        results.append((path, w, h, "overview"))

        # Detail zones: split the area into quadrants
        offset_km = radius_km * 0.5
        offset_lat = offset_km / 111.0
        offset_lon = offset_km / (111.0 * math.cos(math.radians(latitude)))

        zones = [
            ("north", latitude + offset_lat, longitude),
            ("south", latitude - offset_lat, longitude),
            ("east", latitude, longitude + offset_lon),
            ("west", latitude, longitude - offset_lon),
        ]

        for zone_name, lat, lon in zones:
            path, w, h = await self.fetch_area(
                lat, lon, airbase_name,
                zoom=zoom, radius_km=radius_km * 0.6, zone_label=zone_name,
            )
            results.append((path, w, h, zone_name))

        return results


tile_service = TileService(source="esri")
