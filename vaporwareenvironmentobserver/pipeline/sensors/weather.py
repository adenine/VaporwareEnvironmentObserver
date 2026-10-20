from __future__ import annotations

import requests

from pipeline.sensors.base import BaseSensor

# WMO weather interpretation codes (subset), per Open-Meteo's docs.
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class OpenMeteoWeatherSensor(BaseSensor):
    """Fetches current conditions for a lat/lon from Open-Meteo's free
    forecast API (no API key or signup required). Needs a location set via
    set_location() before it has anything to fetch — read() returns None
    until then, same as an unavailable/not-yet-enabled sensor.
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout: float = 10.0):
        self._timeout = timeout
        self._latitude: float | None = None
        self._longitude: float | None = None

    def set_location(self, latitude: float, longitude: float):
        self._latitude = latitude
        self._longitude = longitude

    def read(self) -> dict | None:
        if self._latitude is None or self._longitude is None:
            return None

        params = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        }
        response = requests.get(self.BASE_URL, params=params, timeout=self._timeout)
        response.raise_for_status()
        current = response.json().get("current")
        if not current:
            return None

        return {
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "wind_kph": current.get("wind_speed_10m"),
            "condition": WEATHER_CODES.get(current.get("weather_code"), "Unknown"),
        }
