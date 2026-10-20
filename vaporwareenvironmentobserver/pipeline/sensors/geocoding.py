from __future__ import annotations

import requests

from pipeline.sensors.base import BaseSensor


class NominatimReverseGeocoder(BaseSensor):
    """Resolves a lat/lon to a human-readable place name (city/town) via
    OpenStreetMap's free Nominatim reverse-geocoding API — no API key or
    signup required. Needs a location set via set_location() before it has
    anything to fetch — read() returns None until then, same as the weather
    and air quality sensors.

    Nominatim's usage policy asks for a descriptive User-Agent and no more
    than ~1 request/second, and discourages needless repeat lookups. Since
    a stationary device would otherwise re-resolve the same place on every
    poll, results are cached by lat/lon rounded to 2 decimals (~1km) — a
    poll that lands in the same ~1km cell reuses the cached name instead of
    hitting the network again.
    """

    BASE_URL = "https://nominatim.openstreetmap.org/reverse"
    USER_AGENT = "VaporwareEnvironmentObserver/1.0 (local desktop sensing app; no public deployment)"
    CACHE_PRECISION = 2  # decimal places ~= 1.1km at the equator

    def __init__(self, timeout: float = 10.0):
        self._timeout = timeout
        self._latitude: float | None = None
        self._longitude: float | None = None
        self._cache_key: tuple[float, float] | None = None
        self._cached_name: str | None = None

    def set_location(self, latitude: float, longitude: float):
        self._latitude = latitude
        self._longitude = longitude

    def read(self) -> dict | None:
        if self._latitude is None or self._longitude is None:
            return None

        cache_key = (round(self._latitude, self.CACHE_PRECISION), round(self._longitude, self.CACHE_PRECISION))
        if cache_key != self._cache_key:
            self._cached_name = self._lookup(self._latitude, self._longitude)
            self._cache_key = cache_key

        if not self._cached_name:
            return None
        return {"city": self._cached_name}

    def _lookup(self, latitude: float, longitude: float) -> str | None:
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "zoom": 10,  # city/town-level detail, not full street address
            "addressdetails": 1,
        }
        headers = {"User-Agent": self.USER_AGENT}
        response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=self._timeout)
        response.raise_for_status()
        address = response.json().get("address", {})
        return (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("county")
            or address.get("state")
        )
