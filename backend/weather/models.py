"""Normalized weather data models with explicit forecast coverage."""

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class WeatherForecast:
    latitude: float
    longitude: float
    temperature_c: float
    weather: str
    rain_1h: float
    rain_3h: float
    rain_6h: float
    rain_24h: float
    coverage_1h: float
    coverage_3h: float
    coverage_6h: float
    coverage_24h: float

    def to_dict(self) -> dict[str, Any]:
        return {"location": {"lat": self.latitude, "lon": self.longitude},
                "current": {"temperature_c": self.temperature_c, "weather": self.weather},
                "rainfall": {
                    "next_1h_mm": self.rain_1h, "next_3h_mm": self.rain_3h, "next_6h_mm": self.rain_6h,
                    "next_24h_mm": self.rain_24h, "rain_1h_mm": self.rain_1h, "rain_3h_mm": self.rain_3h,
                    "rain_6h_mm": self.rain_6h, "rain_24h_mm": self.rain_24h,
                    "coverage_hours": {"1h": self.coverage_1h, "3h": self.coverage_3h, "6h": self.coverage_6h, "24h": self.coverage_24h}
                }, "source": "openweather"}
