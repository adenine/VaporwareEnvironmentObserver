from __future__ import annotations

from PyQt6.QtCore import QSettings


class Settings:
    def __init__(self):
        self._qs = QSettings("Vaporware", "VaporwareEnvironmentObserver")

    def _bool(self, key: str, default: bool) -> bool:
        v = self._qs.value(key, default)
        if isinstance(v, bool):
            return v
        return str(v).lower() in ("true", "1")

    @property
    def weather_poll_interval_seconds(self) -> int:
        return int(self._qs.value("pipeline/weather_poll_interval_seconds", 60))

    @weather_poll_interval_seconds.setter
    def weather_poll_interval_seconds(self, value: int):
        self._qs.setValue("pipeline/weather_poll_interval_seconds", value)

    @property
    def location_poll_interval_seconds(self) -> int:
        return int(self._qs.value("inputs/location_poll_interval_seconds", 10))

    @location_poll_interval_seconds.setter
    def location_poll_interval_seconds(self, value: int):
        self._qs.setValue("inputs/location_poll_interval_seconds", value)

    @property
    def digital_air_quality_poll_interval_seconds(self) -> int:
        return int(self._qs.value("inputs/digital_air_quality_poll_interval_seconds", 60))

    @digital_air_quality_poll_interval_seconds.setter
    def digital_air_quality_poll_interval_seconds(self, value: int):
        self._qs.setValue("inputs/digital_air_quality_poll_interval_seconds", value)

    @property
    def location_name_poll_interval_seconds(self) -> int:
        return int(self._qs.value("inputs/location_name_poll_interval_seconds", 60))

    @location_name_poll_interval_seconds.setter
    def location_name_poll_interval_seconds(self, value: int):
        self._qs.setValue("inputs/location_name_poll_interval_seconds", value)

    @property
    def manual_latitude(self) -> float | None:
        v = self._qs.value("location/manual_latitude", "")
        return float(v) if v not in ("", None) else None

    @manual_latitude.setter
    def manual_latitude(self, value: float | None):
        self._qs.setValue("location/manual_latitude", value if value is not None else "")

    @property
    def manual_longitude(self) -> float | None:
        v = self._qs.value("location/manual_longitude", "")
        return float(v) if v not in ("", None) else None

    @manual_longitude.setter
    def manual_longitude(self, value: float | None):
        self._qs.setValue("location/manual_longitude", value if value is not None else "")

    @property
    def mqtt_host(self) -> str:
        return self._qs.value("mqtt/host", "localhost")

    @mqtt_host.setter
    def mqtt_host(self, value: str):
        self._qs.setValue("mqtt/host", value)

    @property
    def mqtt_port(self) -> int:
        return int(self._qs.value("mqtt/port", 1883))

    @mqtt_port.setter
    def mqtt_port(self, value: int):
        self._qs.setValue("mqtt/port", value)

    @property
    def mqtt_topic_base(self) -> str:
        return self._qs.value("mqtt/topic_base", "vaporwareenvironmentobserver")

    @mqtt_topic_base.setter
    def mqtt_topic_base(self, value: str):
        self._qs.setValue("mqtt/topic_base", value)

    @property
    def spacebrew_host(self) -> str:
        return self._qs.value("spacebrew/host", "localhost")

    @spacebrew_host.setter
    def spacebrew_host(self, value: str):
        self._qs.setValue("spacebrew/host", value)

    @property
    def spacebrew_port(self) -> int:
        return int(self._qs.value("spacebrew/port", 1883))

    @spacebrew_port.setter
    def spacebrew_port(self, value: int):
        self._qs.setValue("spacebrew/port", value)

    @property
    def location_enabled(self) -> bool:
        return self._bool("inputs/location_enabled", True)

    @location_enabled.setter
    def location_enabled(self, value: bool):
        self._qs.setValue("inputs/location_enabled", value)

    @property
    def weather_enabled(self) -> bool:
        return self._bool("inputs/weather_enabled", True)

    @weather_enabled.setter
    def weather_enabled(self, value: bool):
        self._qs.setValue("inputs/weather_enabled", value)

    @property
    def digital_air_quality_enabled(self) -> bool:
        return self._bool("inputs/digital_air_quality_enabled", True)

    @digital_air_quality_enabled.setter
    def digital_air_quality_enabled(self, value: bool):
        self._qs.setValue("inputs/digital_air_quality_enabled", value)

    @property
    def location_name_enabled(self) -> bool:
        return self._bool("inputs/location_name_enabled", True)

    @location_name_enabled.setter
    def location_name_enabled(self, value: bool):
        self._qs.setValue("inputs/location_name_enabled", value)

    @property
    def mqtt_publish_enabled(self) -> bool:
        return self._bool("mqtt/publish_enabled", True)

    @mqtt_publish_enabled.setter
    def mqtt_publish_enabled(self, value: bool):
        self._qs.setValue("mqtt/publish_enabled", value)

    @property
    def spacebrew_publish_enabled(self) -> bool:
        return self._bool("spacebrew/publish_enabled", True)

    @spacebrew_publish_enabled.setter
    def spacebrew_publish_enabled(self, value: bool):
        self._qs.setValue("spacebrew/publish_enabled", value)
