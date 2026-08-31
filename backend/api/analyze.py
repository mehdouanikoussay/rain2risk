"""Global on-demand analysis orchestration."""

from typing import Any

from api.weather import get_weather
from geo.global_data import GlobalDataError, get_global_grid
from risk.scoring import calculate_risk


def analyze(lat: float, lon: float) -> dict[str, Any]:
    grid_payload = get_global_grid(lat, lon)
    cells, gis_sources = grid_payload[:2]
    data_quality = grid_payload[2] if len(grid_payload) > 2 else {}
    weather = get_weather(lat, lon)
    elevations = [c["elevation_m"] for c in cells]
    grid_features = []
    for cell in cells:
        geo = {
            "elevation_m": cell["elevation_m"], "slope_deg": cell["slope_deg"],
            "built_up": cell["built_up_fraction"], "water_distance_m": cell["water_distance_m"],
            "min_elevation_m": min(elevations), "max_elevation_m": max(elevations),
        }
        result = calculate_risk(weather, geo)
        grid_features.append({
            "type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
                [cell["bounds"][0][1], cell["bounds"][0][0]], [cell["bounds"][1][1], cell["bounds"][0][0]],
                [cell["bounds"][1][1], cell["bounds"][1][0]], [cell["bounds"][0][1], cell["bounds"][1][0]],
                [cell["bounds"][0][1], cell["bounds"][0][0]],
            ]]}, "properties": {
                "cell_id": cell["cell_id"], "lat": cell["lat"], "lon": cell["lon"],
                "elevation_m": cell["elevation_m"], "slope_deg": cell["slope_deg"],
                "built_up_fraction": cell["built_up_fraction"], "water_fraction": cell["water_fraction"],
                "water_distance_m": cell["water_distance_m"], "building_count": cell["building_count"],
                "land_cover_class": cell["land_cover_class"], "raw_class_codes": cell.get("raw_class_codes"),
                "land_cover_fractions": {k: v for k, v in cell.items() if k.endswith("_fraction")},
                "risk_score": round(result.score), "risk_level": result.level,
                "risk_reasons": getattr(result, "reasons", []),
            }
        })
    selected = min(cells, key=lambda c: (c["lat"] - lat) ** 2 + (c["lon"] - lon) ** 2)
    selected_geo = {"elevation_m": selected["elevation_m"], "slope_deg": selected["slope_deg"], "built_up": selected["built_up_fraction"], "water_distance_m": selected["water_distance_m"], "min_elevation_m": min(elevations), "max_elevation_m": max(elevations)}
    risk = calculate_risk(weather, selected_geo).to_dict()
    data_quality["weather"] = {"available": True, "source": "OpenWeather forecast", "coverage_hours": weather.get("rainfall", {}).get("coverage_hours", {})}
    return {"location": {"lat": lat, "lon": lon}, "weather": weather, "grid": {"type": "FeatureCollection", "features": grid_features}, "risk": risk, "sources": {"weather": "OpenWeather", **gis_sources}, "data_quality": data_quality}
