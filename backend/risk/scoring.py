"""Deterministic rule-based flood risk calculation."""

from typing import Any

from .models import FactorResult, RiskResult
from .normalization import built_up_score, elevation_score, rainfall_score, slope_score, water_distance_score
from .thresholds import RISK_LEVELS, WEIGHTS


def _level(score: float) -> str:
    for limit, label in RISK_LEVELS:
        if score < limit:
            return label
    return "VERY_HIGH"


def _rainfall_input(weather: dict[str, Any]) -> tuple[float | None, str]:
    rainfall = weather.get("rainfall", weather)
    for key, window in (("next_6h_mm", "6h"), ("rain_6h", "6h"), ("next_3h_mm", "3h"), ("rain_3h", "3h"), ("next_1h_mm", "1h"), ("rain_1h", "1h")):
        if rainfall.get(key) is not None:
            return float(rainfall[key]), window
    return None, "none"


def calculate_risk(weather: dict[str, Any], geo_features: dict[str, Any]) -> RiskResult:
    """Calculate a transparent score using only available factors."""
    rain_mm, rainfall_window = _rainfall_input(weather)
    min_elevation = geo_features.get("min_elevation_m"); max_elevation = geo_features.get("max_elevation_m")
    raw = {"rainfall": rainfall_score(rain_mm) if rain_mm is not None else None,
           "slope": slope_score(float(geo_features["slope_deg"])) if geo_features.get("slope_deg") is not None else None,
           "elevation": elevation_score(float(geo_features["elevation_m"]), float(min_elevation), float(max_elevation)) if None not in (geo_features.get("elevation_m"), min_elevation, max_elevation) else None,
           "built_up": built_up_score(float(geo_features["built_up"])) if geo_features.get("built_up") is not None else None,
           "water_distance": water_distance_score(float(geo_features["water_distance_m"])) if geo_features.get("water_distance_m") is not None and geo_features.get("water_distance_m") == geo_features.get("water_distance_m") else None}
    explanations = {"rainfall": "Heavy rainfall is expected.", "slope": "The area has low slope.", "elevation": "The location is relatively low.", "built_up": "Built-up coverage is high.", "water_distance": "The location is close to a waterway."}
    factors = {}
    for name, score in raw.items():
        available = score is not None
        value = float(score or 0.0)
        factors[name] = FactorResult(value, WEIGHTS[name], value * WEIGHTS[name], explanations[name] if available else "Data is unavailable.", available)
    available_names = [name for name, factor in factors.items() if factor.available]
    weight_sum = sum(WEIGHTS[name] for name in available_names) or 1.0
    total = max(0.0, min(100.0, sum(factors[n].contribution for n in available_names) * 100.0 / weight_sum))
    ordered = sorted(available_names, key=lambda name: factors[name].contribution, reverse=True)
    explanation = [explanations[n] for n in ordered if factors[n].score >= 50]
    unavailable = [name for name, factor in factors.items() if not factor.available]
    return RiskResult(total, _level(total), factors, ordered[:3], explanation, rainfall_window, unavailable)
