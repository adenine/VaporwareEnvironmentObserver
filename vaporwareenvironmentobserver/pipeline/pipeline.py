from __future__ import annotations

import time

from PyQt6.QtCore import QThread, pyqtSignal

from pipeline.sensors.base import BaseSensor

EVENT_NAMES = {
    "location": "LocationUpdated",
    "weather": "WeatherUpdated",
    "air_quality": "AirQualityUpdated",
    "location_name": "LocationNameUpdated",
}

# Sensors that need a lat/lon fed to them whenever Location gets a fresh fix.
LOCATION_DEPENDENT_SENSORS = ("weather", "air_quality", "location_name")

# Location gets its own, faster default cadence — GPS fixes are cheap and
# local, so polling more often than a rate-limited network call (Weather,
# Air Quality, Location Name) costs nothing and keeps the last-known
# position fresher.
DEFAULT_INTERVALS = {
    "location": 10,
    "weather": 60,
    "air_quality": 60,
    "location_name": 60,
}


class Pipeline(QThread):
    environment_event = pyqtSignal(dict)
    status_changed = pyqtSignal(dict)
    # Emitted the moment a sensor is polled (before its result comes back)
    # so the UI can pulse that source's LED immediately.
    sensor_activity = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._running = False
        self._intervals: dict[str, int] = dict(DEFAULT_INTERVALS)
        self._sensors: dict[str, BaseSensor | None] = dict.fromkeys(DEFAULT_INTERVALS)
        self._enabled: dict[str, bool] = dict.fromkeys(DEFAULT_INTERVALS, False)

    def set_interval(self, source: str, seconds: int):
        self._intervals[source] = max(1, seconds)

    def set_sensor(self, source: str, sensor: BaseSensor | None, enabled: bool):
        self._sensors[source] = sensor
        self._enabled[source] = enabled

    def run(self):
        self._running = True
        self.status_changed.emit({"pipeline": "started"})

        start = time.monotonic()
        next_poll = dict.fromkeys(self._intervals, start)
        while self._running:
            time.sleep(0.1)
            now = time.monotonic()
            for source, interval in self._intervals.items():
                if now >= next_poll[source]:
                    next_poll[source] = now + interval
                    self._poll(source)

        self.status_changed.emit({"pipeline": "stopped"})

    def _poll(self, source: str):
        sensor = self._sensors.get(source)
        if self._enabled.get(source) and sensor:
            self._run_sensor(source, sensor)

    def _run_sensor(self, source: str, sensor: BaseSensor):
        self.sensor_activity.emit(source)
        try:
            result = sensor.read()
        except Exception as e:  # noqa: BLE001
            self.status_changed.emit({"error": f"{source}: {e}"})
            return

        if not result:
            return

        if source == "location":
            for dependent in LOCATION_DEPENDENT_SENSORS:
                dependent_sensor = self._sensors.get(dependent)
                if dependent_sensor:
                    dependent_sensor.set_location(result["latitude"], result["longitude"])

        self.environment_event.emit({"event": EVENT_NAMES[source], "source": source, **result})

    def stop(self):
        self._running = False
        self.wait()
