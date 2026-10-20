# Vaporware EnvironmentObserver

The Vaporware EnvironmentObserver helps you observe conditions in the physical space around you — where you are, what's in the air, and what the weather's doing. Sibling project to [VaporwareSoundObserver](../VaporwareSoundObserver); same architecture, environmental sensing instead of audio.

Vaporware EnvironmentObserver polls a set of independently-switchable sensors on a timer, and publishes structured events over MQTT and/or Spacebrew 2.0. It is designed for both prototyping and permanent installations.

---

## Interface

The app window is a control surface split into three columns, matching VaporwareSoundObserver's layout:

| Column | Purpose |
|--------|---------|
| **Sensors** | One row per sensor — Location (GPS), Place, Digital Service Air Quality, Air Quality Sensor, Weather Service. Each working sensor has its own on/off switch, an LED that pulses the instant it's polled, a small caption naming the service/sensor behind it, and its own "Update every" interval control. |
| **Settings** | The Start/Stop Session button, MQTT/Spacebrew publish toggles (each with a steady connection-status LED plus a publish pulse), and a live Readings feed showing what's being sensed in real time. |
| **Actuators** | Three stub rows for future exploration — Thermostat, Scent Emitter, Air Filter. All disabled ("TBD"); no engines exist yet. |

All toggle states persist across restarts.

---

## Sensors

| Sensor | What it does | Status |
|--------|---------------|--------|
| **Location (GPS)** | On-device location via macOS's `CoreLocation` (`CLLocationManager.requestLocation`). Triggers a one-time macOS Location Services permission prompt on first use. A successful fix feeds the Place, Weather, and Digital Service Air Quality sensors' coordinates. Default update interval: **10s**. | Working |
| **Place** | Resolves the last known GPS fix to a human-readable place name (city/town) via [OpenStreetMap Nominatim](https://nominatim.org)'s free reverse-geocoding API (no API key required). Results are cached by lat/lon rounded to ~1km so sitting still doesn't re-query Nominatim on every poll — respects their fair-use policy. Default update interval: 60s. | Working |
| **Digital Service Air Quality** | Fetches current air quality (US AQI, PM2.5, PM10, ozone, NO₂) from [Open-Meteo](https://open-meteo.com)'s free Air Quality API (no API key required) for the last known location. Default update interval: 60s. | Working |
| **Air Quality Sensor** | Placeholder row (disabled, "TBD — sensor not chosen yet") for a future physical sensor. No hardware has been chosen yet. | Not started |
| **Weather Service** | Fetches current conditions from [Open-Meteo](https://open-meteo.com)'s free forecast API (no API key required) for the last known location. If Location (GPS) is off, a manual latitude/longitude set in Settings is used instead. Default update interval: 60s. | Working |

Each working sensor has its own "Update every" control right under its row in the Sensors column (persisted independently), so e.g. Location can poll every 10s while Weather, Air Quality, and Place poll every 60s — no shared/global poll interval.

Readings are tagged with their source sensor (e.g. `[location]`, `[weather]`, `[air_quality]`, `[place]`) in the Readings feed and in the `source` field of published MQTT payloads.

## Actuators

| Actuator | What it does | Status |
|----------|---------------|--------|
| **Thermostat** | Placeholder row (disabled, "TBD — integration not chosen yet (e.g. Nest)"). No integration has been chosen yet. | Not started |
| **Scent Emitter** | Placeholder row (disabled, "TBD — device not chosen yet"). No device has been chosen yet. | Not started |
| **Air Filter** | Placeholder row (disabled, "TBD — on/off control, device not chosen yet"). No device has been chosen yet. | Not started |

All three are stubs for future exploration — nothing is wired to the pipeline yet.

---

## MQTT

Vaporware EnvironmentObserver is a **publisher only** — it connects to an external MQTT broker. The Settings column's "MQTT publish" switch gates whether events actually go out (independent of connection state, which is shown by the LED next to it). Topics follow the pattern:

```
<topic_base>/location/updated
<topic_base>/weather/updated
<topic_base>/air_quality/updated
```

Default topic base: `vaporwareenvironmentobserver`. Configurable via Settings.

Example payload (`vaporwareenvironmentobserver/weather/updated`):
```json
{
  "temperature_c": 18.4,
  "humidity_pct": 62,
  "wind_kph": 9.1,
  "condition": "Partly cloudy"
}
```

## Spacebrew 2.0

Vaporware EnvironmentObserver also registers as a node on a [Spacebrew 2.0](https://github.com) router (itself just an MQTT client speaking a small registration protocol on top of the same broker). The Settings column's "Spacebrew 2.0 publish" switch gates outbound publishing the same way the MQTT switch does.

Publishes (`VaporwareEnvironmentObserver/<name>`):
- `location` (JSON) — latitude/longitude/accuracy, as GPS fixes come in
- `location_latlong` (string) — the same fix as a plain `"lat,long"` string, for simple downstream consumers that don't want to parse JSON
- `weather` (JSON) — temperature/humidity/wind/condition, as readings come in
- `air_quality` (JSON) — US AQI/PM2.5/PM10/ozone/NO₂, as readings come in
- `place` (string) — the resolved city/town name from Place, e.g. `"Oakbrook Terrace"`. Spacebrew-only — there's no MQTT topic for this one.

No subscriptions yet — there's no output engine to route incoming messages to.

---

## Deployment Tiers

| Tier | Hardware | Notes |
|------|----------|-------|
| High performance | Laptop or NVIDIA Jetson Orin Nano | Full sensor set, including any future local air-quality hardware |
| Edge | Raspberry Pi 4 or 5 | Weather + external air-quality sensor (no CoreLocation — GPS would need a USB/serial module) |
| MQTT client | ESP32 or Arduino (real air-quality/particulate sensor) | Subscriber/actuator only, feeding readings up over MQTT |

---

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.9+ |
| UI | PyQt6 desktop window, custom-painted LED/toggle widgets, QSS dark theme |
| Location | macOS `CoreLocation` (`pyobjc-framework-CoreLocation`) |
| Place (reverse geocoding) | [OpenStreetMap Nominatim](https://nominatim.org) free reverse-geocoding REST API (`requests`) |
| Air quality (digital) | [Open-Meteo](https://open-meteo.com) free Air Quality REST API (`requests`) |
| Air quality (physical sensor) | TBD |
| Weather | [Open-Meteo](https://open-meteo.com) free forecast REST API (`requests`) |
| Transport | paho-mqtt (publisher + Spacebrew 2.0 registration) |
| Config | QSettings (per-sensor poll intervals, manual lat/lon fallback, service URLs, all input toggle states) |

---

## Project Structure

```
VaporwareEnvironmentObserver/                # project root
├── README.md
├── requirements.txt
├── Run VaporwareEnvironmentObserver.command  # double-clickable Finder launcher
├── Sessions/                                 # one <timestamp>.jsonl file per Start/Stop Session cycle
└── vaporwareenvironmentobserver/
    ├── main.py                            # Entry point; also disables App Nap at startup
    ├── app/
    │   ├── window.py                      # MainWindow — 3-column layout, wiring
    │   ├── style.py                       # QSS dark theme
    │   ├── session_recorder.py            # Writes each session's readings to Sessions/
    │   ├── dialogs/
    │   │   └── settings_dialog.py         # Manual lat/lon, MQTT/Spacebrew settings
    │   └── widgets/
    │       ├── led_indicator.py           # Custom-painted LED (steady state + pulse)
    │       ├── toggle_switch.py           # iOS-style animated on/off switch
    │       ├── io_row.py                  # label + LED + switch, one row per channel
    │       └── live_feed.py               # Titled scrolling list (Readings)
    ├── pipeline/
    │   ├── pipeline.py                    # QThread orchestrator: per-sensor cadence poll → sense → publish
    │   └── sensors/
    │       ├── base.py                    # Abstract sensor interface
    │       ├── location.py                # CoreLocation GPS sensor
    │       ├── geocoding.py               # Nominatim reverse-geocoding client
    │       ├── weather.py                 # Open-Meteo current-conditions client
    │       └── air_quality.py             # Open-Meteo air quality client
    ├── mqtt/
    │   ├── client.py                      # paho-mqtt v2 client wrapper
    │   └── events.py                      # JSON payload builders per event type
    ├── spacebrew/
    │   ├── client.py                      # Spacebrew 2.0 registration + pub wrapper
    │   └── events.py                      # Spacebrew message name/value builders
    └── config/
        └── settings.py                    # QSettings wrapper (all persisted app state)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the pipeline's polling model, the sensor plugin interface, and how to add a new sensor or actuator.

---

## Running

Location works out of the box on macOS (no external service). Weather and Digital Service Air Quality require outbound internet access to `api.open-meteo.com` / `air-quality-api.open-meteo.com` (no signup/API key). MQTT publishing requires a broker (e.g. `mosquitto`) reachable at the configured server.

**Create the virtualenv outside iCloud Drive.** This project's source lives in an iCloud-synced folder, but if `.venv` is created here too, PyQt6 fails to start with `qt.qpa.plugin: Could not find the Qt platform plugin "cocoa"` (same issue documented in VaporwareSoundObserver's README). Confirmed fix: put the venv anywhere outside `~/Library/Mobile Documents/`, e.g.:

```bash
python3 -m venv ~/.venvs/vaporwareenvironmentobserver
~/.venvs/vaporwareenvironmentobserver/bin/pip install -r requirements.txt
cd vaporwareenvironmentobserver
~/.venvs/vaporwareenvironmentobserver/bin/python main.py
```

On first run with Location (GPS) enabled, macOS will prompt for Location Services access — granted to whatever process is running Python (e.g. "Terminal" or "Python"), visible under System Settings → Privacy & Security → Location Services.

## Settings

Each working sensor's update interval is set inline, right under its row in the Sensors column — there's no separate dialog for it. Open **Vaporware EnvironmentObserver → Settings…** for everything else: a manual latitude/longitude fallback (used by Weather, Digital Service Air Quality, and Place when GPS is off), the MQTT broker server/topic base, and the Spacebrew broker server. Both broker "Server" fields default to `localhost` and take an optional `:port` suffix, e.g. `localhost:8080` or `broker.local:1883` — no port means the standard default (1883) is used. All of this, along with every sensor toggle and interval, is saved automatically between sessions.

---

## Session Recordings

Every Start/Stop Session cycle is saved to its own file in the **`Sessions/`** folder at the project root (sibling to this README and the `.command` launcher) — one file per session, named by the timestamp it started at, e.g. `2026-07-11_19-05-57.jsonl`.

Each file is JSONL (one JSON object per line, flushed immediately after every write — a crash mid-session still leaves everything up to that point readable): a `SessionStarted` line, one line per sensor reading (with its own `timestamp` plus whatever fields that event type carries), and a `SessionStopped` line. This is independent of the MQTT/Spacebrew publish toggles — a session is recorded locally regardless of whether external publishing is on.

---

## Status

| Component | Status |
|-----------|--------|
| Per-sensor polling pipeline (independent interval per sensor, each persisted) | Working — timing verified: measured gaps land within ~0.1s of the configured interval in isolation, small (<1s) jitter possible when another sensor's network call overlaps a poll's due time |
| App Nap disabled at startup (`main.py`), so backgrounding the window doesn't stall the poll loop | Implemented — root-caused via macOS's known GUI-app timer throttling; not independently reproduced in an automated test |
| Session recording to `Sessions/<timestamp>.jsonl` | Working — verified live through the real Start/Stop Session flow |
| Location (GPS) via CoreLocation | Working — verified live: real GPS fixes published over MQTT and Spacebrew |
| Weather via Open-Meteo | Working — verified live against Open-Meteo's `/v1/forecast` contract |
| Digital Service Air Quality via Open-Meteo | Working — verified live against Open-Meteo's Air Quality `/v1/air-quality` contract |
| Place via Nominatim | Working — verified live against Nominatim's `/reverse` contract, resolved a real fix to its city name and published over Spacebrew |
| Air Quality Sensor (physical) | Not started — disabled stub row, no hardware chosen yet |
| Actuators column | Not started — Thermostat, Scent Emitter, Air Filter are disabled stub rows, no engine designed |
| MQTT/Spacebrew publish toggles | Implemented, same pattern as VaporwareSoundObserver |
| Settings persistence (all toggles, per-sensor intervals, connection settings, manual lat/lon) | Implemented |

## History

Built as a sibling to [VaporwareSoundObserver](../VaporwareSoundObserver), reusing its 3-column control-surface pattern (Sensors / Settings / Actuators), custom-painted widgets, dark QSS theme, and MQTT/Spacebrew publishing plumbing — swapping the continuous mic-buffer pipeline for a simpler timer-driven poll loop, since environmental readings are point-in-time snapshots rather than a shared audio stream.
