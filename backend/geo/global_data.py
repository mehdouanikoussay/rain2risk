"""Orchestrate global providers; provider details live in separate modules."""

import json
import time
from pathlib import Path

from .dem import DEMError, derive_slopes, fetch_elevations
from .features import build_features
from .grid import make_grid
from .osm import OSMError, fetch_osm
from .worldcover import WorldCoverError, fetch_worldcover, WORLD_COVER_TILE_URL
from .osm import extract_facts as _attach_osm_features

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache"

class GlobalDataError(RuntimeError):
    """A required remote layer failed without inventing replacement values."""


def _key(lat, lon):
    return f"{float(lat):.4f}_{float(lon):.4f}"


def _cached(name, key, loader):
    folder = CACHE / name; folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{key}.json"
    if path.exists():
        try: return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError): path.unlink(missing_ok=True)
    value = loader(); path.write_text(json.dumps(value), encoding="utf-8"); return value


def get_global_grid(lat, lon):
    cells = make_grid(lat, lon)
    min_lat = min(c["bounds"][0][0] for c in cells); max_lat = max(c["bounds"][1][0] for c in cells)
    min_lon = min(c["bounds"][0][1] for c in cells); max_lon = max(c["bounds"][1][1] for c in cells)
    key = _key(lat, lon)
    try:
        dem = _cached("dem", key, lambda: fetch_elevations(cells))
        cover = _cached("worldcover-v2", key, lambda: fetch_worldcover(cells))
    except (DEMError, WorldCoverError, KeyError, ValueError) as error:
        raise GlobalDataError(str(error)) from error
    try:
        osm = _cached("osm", key, lambda: {"payload": fetch_osm(min_lat, min_lon, max_lat, max_lon), "source": "OpenStreetMap via Overpass", "available": True})
        osm_quality = {"available": True, "source": osm["source"]}
    except (OSMError, KeyError, ValueError) as error:
        osm = {"payload": None, "source": "OpenStreetMap via Overpass", "available": False}
        osm_quality = {"available": False, "source": osm["source"], "reason": str(error)}
    cells = build_features(cells, dem["values"], cover["cells"], osm["payload"], derive_slopes)
    if osm["payload"] is None:
        for cell in cells:
            cell.update({"waterway_present": None, "building_count": None, "water_distance_m": None, "landuse_tags": None})
    sources = {"elevation": dem["source"], "land_cover": cover["source"], "osm": osm["source"]}
    quality = {"dem": {"available": True, "source": dem["source"]}, "worldcover": {"available": True, "source": cover["source"]}, "osm": osm_quality}
    return cells, sources, quality
