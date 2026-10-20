from __future__ import annotations

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.dialogs.settings_dialog import SettingsDialog
from app.session_recorder import SessionRecorder
from app.style import STYLESHEET
from app.widgets.io_row import IORow
from app.widgets.led_indicator import ERROR_COLOR, IDLE_ON_COLOR, OFF_COLOR
from app.widgets.live_feed import LiveFeedWidget
from config.settings import Settings
from mqtt import events as mqtt_events
from mqtt.client import MQTTClient
from pipeline.pipeline import Pipeline
from pipeline.sensors.air_quality import OpenMeteoAirQualitySensor
from pipeline.sensors.geocoding import NominatimReverseGeocoder
from pipeline.sensors.location import GPSLocationSensor
from pipeline.sensors.weather import OpenMeteoWeatherSensor
from spacebrew import events as spacebrew_events
from spacebrew.client import SpacebrewClient


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._settings = Settings()
        self.setWindowTitle("Vaporware EnvironmentObserver")
        self.setMinimumSize(940, 640)
        self.setStyleSheet(STYLESHEET)

        self._location_sensor: GPSLocationSensor | None = None
        self._weather_sensor: OpenMeteoWeatherSensor | None = None
        self._air_quality_sensor: OpenMeteoAirQualitySensor | None = None
        self._location_name_sensor: NominatimReverseGeocoder | None = None
        self._session_recorder = SessionRecorder()

        self._pipeline = Pipeline()
        self._pipeline.set_interval("location", self._settings.location_poll_interval_seconds)
        self._pipeline.set_interval("weather", self._settings.weather_poll_interval_seconds)
        self._pipeline.set_interval("air_quality", self._settings.digital_air_quality_poll_interval_seconds)
        self._pipeline.set_interval("location_name", self._settings.location_name_poll_interval_seconds)
        self._pipeline.environment_event.connect(self._on_environment_event)
        self._pipeline.status_changed.connect(self._on_status)
        self._pipeline.sensor_activity.connect(self._on_sensor_activity)

        self._mqtt = MQTTClient(self._settings.mqtt_host, self._settings.mqtt_port)
        self._mqtt.connected.connect(self._on_mqtt_connected)
        self._mqtt.disconnected.connect(self._on_mqtt_disconnected)
        self._mqtt.error.connect(self._on_mqtt_error)

        self._spacebrew = SpacebrewClient(self._settings.spacebrew_host, self._settings.spacebrew_port)
        self._spacebrew.connected.connect(self._on_spacebrew_connected)
        self._spacebrew.disconnected.connect(self._on_spacebrew_disconnected)
        self._spacebrew.error.connect(self._on_spacebrew_error)

        self._build_menu()
        self._build_central()
        self._apply_initial_source_states()

        self._mqtt.connect_broker()
        self._spacebrew.connect_broker()

    # ---- construction -------------------------------------------------

    def _build_menu(self):
        menu = self.menuBar()
        app_menu = menu.addMenu("Vaporware EnvironmentObserver")
        app_menu.addAction("Settings…", self._open_settings)
        app_menu.addSeparator()
        app_menu.addAction("Quit", self.close)

    def _build_central(self):
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.addWidget(self._build_header())

        columns = QHBoxLayout()
        columns.setSpacing(10)
        columns.addWidget(self._build_sensors_column(), stretch=1)
        columns.addWidget(self._build_settings_column(), stretch=1)
        columns.addWidget(self._build_actuators_column(), stretch=1)
        outer.addLayout(columns)

        self.setCentralWidget(central)

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(2)

        title = QLabel("Vaporware EnvironmentObserver")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        description = QLabel(
            "The Vaporware EnvironmentObserver helps you observe conditions in the "
            "physical space around you — where you are, what's in the air, and what "
            "the weather's doing."
        )
        description.setObjectName("appDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        return header

    def _build_sensors_column(self) -> QGroupBox:
        group = QGroupBox("Sensors")
        layout = QVBoxLayout(group)

        self._location_row = IORow("Location (GPS)", checked=self._settings.location_enabled)
        self._location_row.toggled.connect(self._on_location_toggled)
        layout.addWidget(self._location_row)
        layout.addWidget(self._build_caption("macOS CoreLocation"))
        layout.addWidget(
            self._build_interval_row(self._settings.location_poll_interval_seconds, self._on_location_interval_changed)
        )

        self._location_name_row = IORow("Place", checked=self._settings.location_name_enabled)
        self._location_name_row.toggled.connect(self._on_location_name_toggled)
        layout.addWidget(self._location_name_row)
        layout.addWidget(self._build_caption("OpenStreetMap Nominatim"))
        layout.addWidget(
            self._build_interval_row(
                self._settings.location_name_poll_interval_seconds, self._on_location_name_interval_changed
            )
        )

        self._digital_air_quality_row = IORow(
            "Digital Service Air Quality", checked=self._settings.digital_air_quality_enabled
        )
        self._digital_air_quality_row.toggled.connect(self._on_digital_air_quality_toggled)
        layout.addWidget(self._digital_air_quality_row)
        layout.addWidget(self._build_caption("Open-Meteo Air Quality API"))
        layout.addWidget(
            self._build_interval_row(
                self._settings.digital_air_quality_poll_interval_seconds, self._on_air_quality_interval_changed
            )
        )

        self._air_quality_sensor_row = IORow("Air Quality Sensor", checked=False)
        self._air_quality_sensor_row.set_disabled_stub("TBD — sensor not chosen yet")
        layout.addWidget(self._air_quality_sensor_row)
        layout.addWidget(self._build_caption("TBD — no sensor connected yet"))

        self._weather_row = IORow("Weather Service", checked=self._settings.weather_enabled)
        self._weather_row.toggled.connect(self._on_weather_toggled)
        layout.addWidget(self._weather_row)
        layout.addWidget(self._build_caption("Open-Meteo Forecast API"))
        layout.addWidget(
            self._build_interval_row(self._settings.weather_poll_interval_seconds, self._on_weather_interval_changed)
        )

        layout.addStretch()
        return group

    def _build_caption(self, text: str) -> QLabel:
        """Small muted label naming the service/sensor backing a Sensors-column row."""
        label = QLabel(text)
        label.setObjectName("sensorCaption")
        label.setContentsMargins(30, 0, 6, 4)
        return label

    def _build_interval_row(self, initial_seconds: int, on_changed) -> QWidget:
        """A small "Update every [N] s" row, nested directly under a sensor's IORow."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(30, 0, 6, 8)
        layout.setSpacing(6)

        label = QLabel("Update every")
        label.setObjectName("statusLabel")
        layout.addWidget(label)

        spin = QSpinBox()
        spin.setRange(1, 3600)
        spin.setSuffix(" s")
        spin.setValue(initial_seconds)
        spin.valueChanged.connect(on_changed)
        layout.addWidget(spin)

        layout.addStretch()
        return row

    def _build_settings_column(self) -> QGroupBox:
        group = QGroupBox("Settings")
        layout = QVBoxLayout(group)

        self._session_button = QPushButton("Start Session")
        self._session_button.setObjectName("sessionButton")
        self._session_button.clicked.connect(self._toggle_session)
        layout.addWidget(self._session_button)

        self._status_label = QLabel("Pipeline: stopped")
        self._status_label.setObjectName("statusLabel")
        layout.addWidget(self._status_label)

        self._mqtt_row = IORow("MQTT publish", checked=self._settings.mqtt_publish_enabled)
        self._mqtt_row.toggled.connect(self._on_mqtt_publish_toggled)
        layout.addWidget(self._mqtt_row)

        self._spacebrew_row = IORow("Spacebrew 2.0 publish", checked=self._settings.spacebrew_publish_enabled)
        self._spacebrew_row.toggled.connect(self._on_spacebrew_publish_toggled)
        layout.addWidget(self._spacebrew_row)

        self._readings_feed = LiveFeedWidget("Readings")
        layout.addWidget(self._readings_feed, stretch=1)

        return group

    def _build_actuators_column(self) -> QGroupBox:
        group = QGroupBox("Actuators")
        layout = QVBoxLayout(group)

        self._thermostat_row = IORow("Thermostat", checked=False)
        self._thermostat_row.set_disabled_stub("TBD — integration not chosen yet (e.g. Nest)")
        layout.addWidget(self._thermostat_row)

        self._scent_emitter_row = IORow("Scent Emitter", checked=False)
        self._scent_emitter_row.set_disabled_stub("TBD — device not chosen yet")
        layout.addWidget(self._scent_emitter_row)

        self._air_filter_row = IORow("Air Filter", checked=False)
        self._air_filter_row.set_disabled_stub("TBD — on/off control, device not chosen yet")
        layout.addWidget(self._air_filter_row)

        layout.addStretch()
        return group

    def _apply_initial_source_states(self):
        if self._weather_row.is_on():
            self._weather_sensor = self._make_weather_sensor()
        self._pipeline.set_sensor("weather", self._weather_sensor, self._weather_row.is_on())

        if self._digital_air_quality_row.is_on():
            self._air_quality_sensor = self._make_air_quality_sensor()
        self._pipeline.set_sensor("air_quality", self._air_quality_sensor, self._digital_air_quality_row.is_on())

        if self._location_name_row.is_on():
            self._location_name_sensor = self._make_location_name_sensor()
        self._pipeline.set_sensor("location_name", self._location_name_sensor, self._location_name_row.is_on())

        if self._location_row.is_on():
            self._location_sensor = GPSLocationSensor()
        self._pipeline.set_sensor("location", self._location_sensor, self._location_row.is_on())

    def _make_weather_sensor(self) -> OpenMeteoWeatherSensor:
        sensor = OpenMeteoWeatherSensor()
        lat, lon = self._settings.manual_latitude, self._settings.manual_longitude
        if lat is not None and lon is not None:
            sensor.set_location(lat, lon)
        return sensor

    def _make_air_quality_sensor(self) -> OpenMeteoAirQualitySensor:
        sensor = OpenMeteoAirQualitySensor()
        lat, lon = self._settings.manual_latitude, self._settings.manual_longitude
        if lat is not None and lon is not None:
            sensor.set_location(lat, lon)
        return sensor

    def _make_location_name_sensor(self) -> NominatimReverseGeocoder:
        sensor = NominatimReverseGeocoder()
        lat, lon = self._settings.manual_latitude, self._settings.manual_longitude
        if lat is not None and lon is not None:
            sensor.set_location(lat, lon)
        return sensor

    # ---- settings dialog ------------------------------------------------

    def _open_settings(self):
        dialog = SettingsDialog(self._settings, parent=self)
        if dialog.exec():
            lat, lon = self._settings.manual_latitude, self._settings.manual_longitude
            if lat is not None and lon is not None:
                if self._weather_sensor:
                    self._weather_sensor.set_location(lat, lon)
                if self._air_quality_sensor:
                    self._air_quality_sensor.set_location(lat, lon)
                if self._location_name_sensor:
                    self._location_name_sensor.set_location(lat, lon)
            self._reconnect_mqtt()
            self._reconnect_spacebrew()

    def _reconnect_mqtt(self):
        self._mqtt.disconnect()
        self._mqtt = MQTTClient(self._settings.mqtt_host, self._settings.mqtt_port)
        self._mqtt.connected.connect(self._on_mqtt_connected)
        self._mqtt.disconnected.connect(self._on_mqtt_disconnected)
        self._mqtt.error.connect(self._on_mqtt_error)
        self._mqtt_row.led.set_state(OFF_COLOR, lit=False)
        self._mqtt.connect_broker()

    def _reconnect_spacebrew(self):
        self._spacebrew.disconnect()
        self._spacebrew = SpacebrewClient(self._settings.spacebrew_host, self._settings.spacebrew_port)
        self._spacebrew.connected.connect(self._on_spacebrew_connected)
        self._spacebrew.disconnected.connect(self._on_spacebrew_disconnected)
        self._spacebrew.error.connect(self._on_spacebrew_error)
        self._spacebrew_row.led.set_state(OFF_COLOR, lit=False)
        self._spacebrew.connect_broker()

    # ---- session --------------------------------------------------------

    def _toggle_session(self):
        if self._pipeline.isRunning():
            self._pipeline.stop()
            self._session_recorder.stop()
            self._session_button.setText("Start Session")
        else:
            path = self._session_recorder.start()
            self._pipeline.start()
            self._session_button.setText("Stop Session")
            self.statusBar().showMessage(f"Recording session to {path}", 4000)

    # ---- input toggles ----------------------------------------------------

    def _on_location_toggled(self, checked: bool):
        self._settings.location_enabled = checked
        if checked and self._location_sensor is None:
            self._location_sensor = GPSLocationSensor()
        self._pipeline.set_sensor("location", self._location_sensor, checked)

    def _on_weather_toggled(self, checked: bool):
        self._settings.weather_enabled = checked
        if checked and self._weather_sensor is None:
            self._weather_sensor = self._make_weather_sensor()
        self._pipeline.set_sensor("weather", self._weather_sensor, checked)

    def _on_digital_air_quality_toggled(self, checked: bool):
        self._settings.digital_air_quality_enabled = checked
        if checked and self._air_quality_sensor is None:
            self._air_quality_sensor = self._make_air_quality_sensor()
        self._pipeline.set_sensor("air_quality", self._air_quality_sensor, checked)

    def _on_location_name_toggled(self, checked: bool):
        self._settings.location_name_enabled = checked
        if checked and self._location_name_sensor is None:
            self._location_name_sensor = self._make_location_name_sensor()
        self._pipeline.set_sensor("location_name", self._location_name_sensor, checked)

    # ---- update-interval controls -------------------------------------

    def _on_location_interval_changed(self, value: int):
        self._settings.location_poll_interval_seconds = value
        self._pipeline.set_interval("location", value)

    def _on_weather_interval_changed(self, value: int):
        self._settings.weather_poll_interval_seconds = value
        self._pipeline.set_interval("weather", value)

    def _on_air_quality_interval_changed(self, value: int):
        self._settings.digital_air_quality_poll_interval_seconds = value
        self._pipeline.set_interval("air_quality", value)

    def _on_location_name_interval_changed(self, value: int):
        self._settings.location_name_poll_interval_seconds = value
        self._pipeline.set_interval("location_name", value)

    def _on_sensor_activity(self, source: str):
        row = {
            "location": self._location_row,
            "weather": self._weather_row,
            "air_quality": self._digital_air_quality_row,
            "location_name": self._location_name_row,
        }.get(source)
        if row:
            row.pulse()

    # ---- publish toggles --------------------------------------------------

    def _on_mqtt_publish_toggled(self, checked: bool):
        self._settings.mqtt_publish_enabled = checked

    def _on_spacebrew_publish_toggled(self, checked: bool):
        self._settings.spacebrew_publish_enabled = checked

    # ---- environment events -------------------------------------------------

    def _on_environment_event(self, event: dict):
        kind = event["event"]
        if kind == "LocationUpdated":
            self._readings_feed.add_entry(
                f'[location] {event["latitude"]:.5f}, {event["longitude"]:.5f} '
                f'(±{event["accuracy"]:.0f}m)'
            )
        elif kind == "WeatherUpdated":
            self._readings_feed.add_entry(
                f'[weather] {event["condition"]}, {event["temperature_c"]:.1f}°C, '
                f'{event["humidity_pct"]:.0f}% humidity, {event["wind_kph"]:.1f} km/h wind'
            )
        elif kind == "AirQualityUpdated":
            self._readings_feed.add_entry(
                f'[air_quality] US AQI {event["us_aqi"]:.0f}, PM2.5 {event["pm2_5"]:.1f}, '
                f'PM10 {event["pm10"]:.1f} µg/m³'
            )
        elif kind == "LocationNameUpdated":
            self._readings_feed.add_entry(f'[place] {event["city"]}')
        self._session_recorder.record(event)
        self._publish_event(event)

    def _publish_event(self, event: dict):
        kind = event["event"]
        base = self._settings.mqtt_topic_base

        if kind == "LocationUpdated":
            topic, payload = mqtt_events.location_updated(
                event["latitude"], event["longitude"], event["accuracy"], base
            )
            if self._mqtt_row.is_on():
                self._mqtt.publish(topic, payload)
                self._mqtt_row.pulse()
            if self._spacebrew_row.is_on():
                sb_name, sb_value = spacebrew_events.location(event["latitude"], event["longitude"], event["accuracy"])
                self._spacebrew.publish(sb_name, sb_value)
                latlong_name, latlong_value = spacebrew_events.location_latlong(event["latitude"], event["longitude"])
                self._spacebrew.publish(latlong_name, latlong_value)
                self._spacebrew_row.pulse()
        elif kind == "WeatherUpdated":
            topic, payload = mqtt_events.weather_updated(
                event["temperature_c"], event["humidity_pct"], event["wind_kph"], event["condition"], base
            )
            if self._mqtt_row.is_on():
                self._mqtt.publish(topic, payload)
                self._mqtt_row.pulse()
            if self._spacebrew_row.is_on():
                sb_name, sb_value = spacebrew_events.weather(
                    event["temperature_c"], event["humidity_pct"], event["wind_kph"], event["condition"]
                )
                self._spacebrew.publish(sb_name, sb_value)
                self._spacebrew_row.pulse()
        elif kind == "AirQualityUpdated":
            topic, payload = mqtt_events.air_quality_updated(
                event["us_aqi"], event["pm2_5"], event["pm10"], event["ozone"], event["nitrogen_dioxide"], base
            )
            if self._mqtt_row.is_on():
                self._mqtt.publish(topic, payload)
                self._mqtt_row.pulse()
            if self._spacebrew_row.is_on():
                sb_name, sb_value = spacebrew_events.air_quality(
                    event["us_aqi"], event["pm2_5"], event["pm10"], event["ozone"], event["nitrogen_dioxide"]
                )
                self._spacebrew.publish(sb_name, sb_value)
                self._spacebrew_row.pulse()
        elif kind == "LocationNameUpdated":
            # Spacebrew only, by design — no MQTT topic for this one.
            if self._spacebrew_row.is_on():
                sb_name, sb_value = spacebrew_events.place(event["city"])
                self._spacebrew.publish(sb_name, sb_value)
                self._spacebrew_row.pulse()

    # ---- status / connection indicators --------------------------------

    def _on_status(self, status: dict):
        parts = []
        for key, value in status.items():
            if key == "pipeline":
                self._status_label.setText(f"Pipeline: {value}")
                parts.append(f"Pipeline: {value}")
            elif key == "error":
                parts.append(f"Error: {value}")
            else:
                parts.append(f"{key}: {value}")
        if parts:
            self.statusBar().showMessage("  |  ".join(parts))

    def _on_mqtt_connected(self):
        self._mqtt_row.led.set_state(IDLE_ON_COLOR, lit=True)
        host = self._settings.mqtt_host
        port = self._settings.mqtt_port
        self.statusBar().showMessage(f"MQTT connected: {host}:{port}", 3000)

    def _on_mqtt_disconnected(self):
        self._mqtt_row.led.set_state(OFF_COLOR, lit=False)

    def _on_mqtt_error(self, message: str):
        self._mqtt_row.led.set_state(ERROR_COLOR, lit=True)
        self.statusBar().showMessage(f"MQTT: {message}", 5000)

    def _on_spacebrew_connected(self):
        self._spacebrew_row.led.set_state(IDLE_ON_COLOR, lit=True)
        host = self._settings.spacebrew_host
        port = self._settings.spacebrew_port
        self.statusBar().showMessage(f"Spacebrew connected: {host}:{port}", 3000)

    def _on_spacebrew_disconnected(self):
        self._spacebrew_row.led.set_state(OFF_COLOR, lit=False)

    def _on_spacebrew_error(self, message: str):
        self._spacebrew_row.led.set_state(ERROR_COLOR, lit=True)
        self.statusBar().showMessage(f"Spacebrew: {message}", 5000)

    def closeEvent(self, event):
        if self._pipeline.isRunning():
            self._pipeline.stop()
            self._session_recorder.stop()
        self._mqtt.disconnect()
        self._spacebrew.disconnect()
        super().closeEvent(event)
