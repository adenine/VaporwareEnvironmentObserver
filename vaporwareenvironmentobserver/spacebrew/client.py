import paho.mqtt.client as mqtt
from PyQt6.QtCore import QObject, pyqtSignal


class SpacebrewClient(QObject):
    """Registers with a Spacebrew 2.0 router (github.com/.../Spacebrew2.0), which
    is itself just an MQTT client speaking a small registration protocol on top
    of the same broker: publish "name, desc, pubs(p:t,...), subs(s:t,...)" to
    the `YuxiSpace` topic, then publish routed data to `<name>/<pub>`.
    """

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)

    # No commas allowed here — _register()'s registration string is comma-
    # delimited ("name, description, pubs(...), subs(...)") and the router
    # parses it positionally, so a comma inside DESCRIPTION corrupts the
    # pubs/subs fields that follow it.
    DESCRIPTION = "Vaporware EnvironmentObserver location / weather / air quality publisher"
    # Kept in sync with spacebrew/events.py's message names. Type suffix
    # matches each message's actual payload shape — location/weather/
    # air_quality carry JSON objects, location_latlong and place carry
    # plain strings.
    PUBLISHERS = [
        "location:json",
        "location_latlong:string",
        "weather:json",
        "air_quality:json",
        "place:string",
    ]
    # No outputs are wired up yet, so nothing to subscribe to.
    SUBSCRIBERS: list[str] = []

    def __init__(self, host: str = "localhost", port: int = 1883, name: str = "VaporwareEnvironmentObserver"):
        super().__init__()
        self._host = host
        self._port = port
        self._name = name
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, name)
        self._client.will_set("YuxiSpace/leave", payload=name, qos=1)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def connect_broker(self):
        try:
            self._client.connect_async(self._host, self._port)
            self._client.loop_start()
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))

    def publish(self, name: str, value: str):
        self._client.publish(f"{self._name}/{name}", value, qos=1)

    def disconnect(self):
        try:
            self._client.publish("YuxiSpace/leave", self._name, qos=1).wait_for_publish()
        except Exception:  # noqa: BLE001
            pass
        self._client.loop_stop()
        self._client.disconnect()

    def _register(self):
        pubs_str = ", ".join(self.PUBLISHERS)
        subs_str = ", ".join(self.SUBSCRIBERS)
        registration = f"{self._name}, {self.DESCRIPTION}, pubs({pubs_str}), subs({subs_str})"
        self._client.publish("YuxiSpace", registration)

    # paho-mqtt v2 on_connect: (client, userdata, connect_flags, reason_code, properties)
    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if reason_code.is_failure:
            self.error.emit(f"Spacebrew connect failed: {reason_code}")
        else:
            self._register()
            self.connected.emit()

    # paho-mqtt v2 on_disconnect: (client, userdata, disconnect_flags, reason_code, properties)
    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.disconnected.emit()
