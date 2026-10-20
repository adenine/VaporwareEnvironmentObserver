import json


def location_updated(
    latitude: float, longitude: float, accuracy: float, topic_base: str = "vaporwareenvironmentobserver"
) -> tuple[str, str]:
    payload = {"latitude": latitude, "longitude": longitude, "accuracy": accuracy}
    return f"{topic_base}/location/updated", json.dumps(payload)


def weather_updated(
    temperature_c: float,
    humidity_pct: float,
    wind_kph: float,
    condition: str,
    topic_base: str = "vaporwareenvironmentobserver",
) -> tuple[str, str]:
    payload = {
        "temperature_c": temperature_c,
        "humidity_pct": humidity_pct,
        "wind_kph": wind_kph,
        "condition": condition,
    }
    return f"{topic_base}/weather/updated", json.dumps(payload)


def air_quality_updated(
    us_aqi: float,
    pm2_5: float,
    pm10: float,
    ozone: float,
    nitrogen_dioxide: float,
    topic_base: str = "vaporwareenvironmentobserver",
) -> tuple[str, str]:
    payload = {
        "us_aqi": us_aqi,
        "pm2_5": pm2_5,
        "pm10": pm10,
        "ozone": ozone,
        "nitrogen_dioxide": nitrogen_dioxide,
    }
    return f"{topic_base}/air_quality/updated", json.dumps(payload)
