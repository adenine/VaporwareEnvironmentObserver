from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from config.settings import Settings

DEFAULT_MQTT_PORT = 1883
DEFAULT_SPACEBREW_PORT = 1883


def _format_server(host: str, port: int, default_port: int) -> str:
    """"localhost" when on the default port, "localhost:8080" otherwise."""
    return host if port == default_port else f"{host}:{port}"


def _parse_server(text: str, default_port: int) -> tuple[str, int]:
    """Inverse of _format_server — "host" or "host:port", falling back to
    the default port when no ":port" suffix is given or it doesn't parse."""
    text = text.strip()
    if ":" in text:
        host, _, port_str = text.rpartition(":")
        host = host.strip()
        try:
            return host or "localhost", int(port_str)
        except ValueError:
            pass
    return text or "localhost", default_port


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumWidth(360)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_location_group())
        layout.addWidget(self._build_mqtt_group())
        layout.addWidget(self._build_spacebrew_group())
        layout.addWidget(self._build_buttons())

    def _build_location_group(self) -> QGroupBox:
        group = QGroupBox("Manual Location Fallback")
        form = QFormLayout(group)

        self._manual_lat = QDoubleSpinBox()
        self._manual_lat.setRange(-90.0, 90.0)
        self._manual_lat.setDecimals(6)
        self._manual_lat.setSpecialValueText("—")
        self._manual_lat.setValue(self._settings.manual_latitude or self._manual_lat.minimum())
        form.addRow("Latitude:", self._manual_lat)

        self._manual_lon = QDoubleSpinBox()
        self._manual_lon.setRange(-180.0, 180.0)
        self._manual_lon.setDecimals(6)
        self._manual_lon.setSpecialValueText("—")
        self._manual_lon.setValue(self._settings.manual_longitude or self._manual_lon.minimum())
        form.addRow("Longitude:", self._manual_lon)

        form.addRow(QLabel("Used to feed Weather and Digital Service Air Quality when the Location (GPS) input is off."))

        return group

    def _build_mqtt_group(self) -> QGroupBox:
        group = QGroupBox("MQTT Broker")
        form = QFormLayout(group)

        self._mqtt_server = QLineEdit(
            _format_server(self._settings.mqtt_host, self._settings.mqtt_port, DEFAULT_MQTT_PORT)
        )
        self._mqtt_server.setPlaceholderText("localhost:8080")
        form.addRow("Server:", self._mqtt_server)

        self._topic_base = QLineEdit(self._settings.mqtt_topic_base)
        self._topic_base.setPlaceholderText("vaporwareenvironmentobserver")
        form.addRow("Topic base:", self._topic_base)

        form.addRow(QLabel("Topics will be published as <base>/location/updated etc."))

        return group

    def _build_spacebrew_group(self) -> QGroupBox:
        group = QGroupBox("Spacebrew")
        form = QFormLayout(group)

        self._spacebrew_server = QLineEdit(
            _format_server(self._settings.spacebrew_host, self._settings.spacebrew_port, DEFAULT_SPACEBREW_PORT)
        )
        self._spacebrew_server.setPlaceholderText("localhost:8080")
        form.addRow("Server:", self._spacebrew_server)

        form.addRow(QLabel("Publishes location, weather, and air quality messages."))

        return group

    def _build_buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        return buttons

    def _save(self):
        self._settings.manual_latitude = (
            None if self._manual_lat.value() == self._manual_lat.minimum() else self._manual_lat.value()
        )
        self._settings.manual_longitude = (
            None if self._manual_lon.value() == self._manual_lon.minimum() else self._manual_lon.value()
        )
        mqtt_host, mqtt_port = _parse_server(self._mqtt_server.text(), DEFAULT_MQTT_PORT)
        self._settings.mqtt_host = mqtt_host
        self._settings.mqtt_port = mqtt_port
        self._settings.mqtt_topic_base = self._topic_base.text().strip() or "vaporwareenvironmentobserver"

        spacebrew_host, spacebrew_port = _parse_server(self._spacebrew_server.text(), DEFAULT_SPACEBREW_PORT)
        self._settings.spacebrew_host = spacebrew_host
        self._settings.spacebrew_port = spacebrew_port
        self.accept()
