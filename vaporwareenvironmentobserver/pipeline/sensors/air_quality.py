from __future__ import annotations

import requests

from pipeline.sensors.base import BaseSensor


class OpenMeteoAirQualitySensor(BaseSensor):
    """Fetches current air quality for a lat/lon from Open-Meteo's free Air
    Quality API (no API key or signup required) — same provider as
    OpenMeteoWeatherSensor. Needs a location set via set_location() before
    it has anything to fetch — read() returns None until then, same as the
    weather sensor.
    """

    BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

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
            "current": "us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide",
        }
        response = requests.get(self.BASE_URL, params=params, timeout=self._timeout)
        response.raise_for_status()
        current = response.json().get("current")
        if not current:
            return None

        return {
            "us_aqi": current.get("us_aqi"),
            "pm2_5": current.get("pm2_5"),
            "pm10": current.get("pm10"),
            "ozone": current.get("ozone"),
            "nitrogen_dioxide": current.get("nitrogen_dioxide"),
        }
