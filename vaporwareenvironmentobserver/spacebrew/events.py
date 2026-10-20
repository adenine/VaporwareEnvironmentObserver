import json


def location(latitude: float, longitude: float, accuracy: float) -> tuple[str, str]:
    payload = {"latitude": latitude, "longitude": longitude, "accuracy": accuracy}
    return "location", json.dumps(payload)


def location_latlong(latitude: float, longitude: float) -> tuple[str, str]:
    """Plain "lat,long" form, for simple downstream consumers that don't want to parse JSON."""
    return "location_latlong", f"{latitude},{longitude}"


def weather(temperature_c: float, humidity_pct: float, wind_kph: float, condition: str) -> tuple[str, str]:
    payload = {
        "temperature_c": temperature_c,
        "humidity_pct": humidity_pct,
        "wind_kph": wind_kph,
        "condition": condition,
    }
    return "weather", json.dumps(payload)


def air_quality(us_aqi: float, pm2_5: float, pm10: float, ozone: float, nitrogen_dioxide: float) -> tuple[str, str]:
    payload = {
        "us_aqi": us_aqi,
        "pm2_5": pm2_5,
        "pm10": pm10,
        "ozone": ozone,
        "nitrogen_dioxide": nitrogen_dioxide,
    }
    return "air_quality", json.dumps(payload)


def place(city: str) -> tuple[str, str]:
    """Plain city-name string, resolved from GPS via reverse geocoding."""
    return "place", city
