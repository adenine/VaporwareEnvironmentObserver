# Architecture

This document covers how Vaporware EnvironmentObserver's pipeline, plugin interfaces, and UI
widgets fit together, and how to extend it with a new sensor or actuator.
For what the app does and how to run it, see the [top-level README](../README.md).

---

## Pipeline: per-sensor cadence, multi-sensor

`pipeline/pipeline.py`'s `Pipeline(QThread)` is the single background thread
that owns the poll loop and dispatches to whichever sensors are enabled.
Unlike VaporwareSoundObserver's pipeline — which needs dual cadences because
both sources share one live mic stream through named, independently-
flushable buffers — EnvironmentObserver has no shared stream to manage: each
sensor's `read()` is a point-in-time snapshot fetched on demand. So instead
of hardcoding one cadence per sensor as separate attributes, `Pipeline`
keeps three parallel dicts keyed by source name (`"location"`,
`"location_name"`, `"weather"`, `"air_quality"`): `_intervals`, `_sensors`,
`_enabled`. `run()` tracks a
`next_poll[source]` deadline per entry and polls each independently once its
own interval has elapsed — Location defaults to a much faster 10s cadence
(`DEFAULT_INTERVALS["location"]`) than Weather/Air Quality's 60s, since GPS
fixes are cheap and local while the other two are rate-limited network
calls. Every sensor's interval is user-configurable (an "Update every" spin
box directly under its row in the Sensors column) and persisted
independently in `config/settings.py`.

Adding a sensor with genuinely different needs is just one more dict entry
in `DEFAULT_INTERVALS` plus wiring — see "Adding a new sensor" below.

### App Nap

`main.py`'s `_disable_app_nap()` opts the whole process out of macOS App
Nap at startup, via `NSProcessInfo.beginActivityWithOptions_reason_` (kept
alive for the process's lifetime in the module-level `_app_nap_activity`
— releasing that token re-enables App Nap). Without this, macOS
aggressively throttles timers and background threads for GUI apps that are
backgrounded or fully occluded by another window, which stalls
`Pipeline`'s poll loop — it's just a `QThread` doing `time.sleep(0.1)` — the
moment the window isn't frontmost/visible, making sensors appear to "stop
updating" until the window is focused again. There's no Info.plist to set
`NSSupportsSuddenTermination`/`LSUIElement`-style App Nap opt-outs since
this runs as a plain script rather than a signed `.app` bundle, so it's
done at runtime instead.

`_run_sensor` runs each poll **synchronously**, and has one piece of
cross-sensor logic: after a successful Location poll, it feeds that fix to
every sensor listed in `LOCATION_DEPENDENT_SENSORS` (`weather`,
`air_quality`, `location_name`) via their `set_location(lat, lon)`. Because
Location polls on its own faster cadence, all three dependent sensors get
whatever the freshest known position was, independent of their own slower
poll timing.

Two signals carry pipeline state out to the UI:

- **`sensor_activity(str)`** — emitted the instant a sensor is polled
  (e.g. `"location"`, `"weather"`, `"air_quality"`, `"location_name"`),
  *before* the blocking call returns. `window.py` pulses that input's LED
  on this signal — the LED reflects "this sensor was polled," not "the poll
  returned a reading." This keeps the LED honest even when a poll comes
  back empty (e.g. Weather with no location set yet).
- **`environment_event(dict)`** — emitted on a successful reading. Every
  payload carries `event` (`"LocationUpdated"`, `"WeatherUpdated"`,
  `"AirQualityUpdated"`, or `"LocationNameUpdated"`, from the `EVENT_NAMES`
  dict) and a `source` key identifying which sensor produced it, plus the
  event-specific fields.

---

## Plugin interface

Adding a new sensor means implementing `BaseSensor` and wiring it into
`Pipeline` + the Sensors column — nothing else in the pipeline needs to
change.

### `BaseSensor` (`pipeline/sensors/base.py`)

```python
class BaseSensor(ABC):
    @abstractmethod
    def read(self) -> dict | None: ...
```

Returns a dict of reading fields, or `None` if there's nothing to report yet
(e.g. Weather/Air Quality before any location is known). Existing
implementations:
- `location.py` — `GPSLocationSensor`, via macOS's `CLLocationManager`.
  Unlike Speech.framework's dispatch-queue-delivered completion handler
  (see VaporwareSoundObserver's `AppleSpeechTranscriber`), CLLocationManager
  schedules its delegate callback on the *run loop of whichever thread
  called `requestLocation()`* — and `Pipeline`'s QThread never pumps one, it
  just `time.sleep()`s. So `read()` doesn't block on a bare
  `threading.Event.wait()`; it pumps that thread's CFRunLoop in short bursts
  via `CFRunLoopRunInMode` while checking the event, which is what actually
  lets CoreLocation's callback (and even the permission prompt) fire
  regardless of which thread calls `read()`. Authorization
  (`requestWhenInUseAuthorization`) is requested lazily on first use, which
  is what triggers macOS's one-time Location Services prompt.
- `weather.py` — `OpenMeteoWeatherSensor`, a plain `requests.get` against
  Open-Meteo's `/v1/forecast` with no auth.
- `air_quality.py` — `OpenMeteoAirQualitySensor`, same shape as
  `weather.py` but against Open-Meteo's separate Air Quality API
  (`air-quality-api.open-meteo.com/v1/air-quality`) — same provider, no
  auth, no signup.
- `geocoding.py` — `NominatimReverseGeocoder`, against OpenStreetMap's
  free `/reverse` endpoint. Unlike Weather/Air Quality, it doesn't just
  fetch on every `read()` — Nominatim's usage policy discourages needless
  repeat lookups, so results are cached keyed on lat/lon rounded to 2
  decimals (~1km); a poll landing in the same cell reuses the cached city
  name instead of re-querying.

  `weather.py`, `air_quality.py`, and `geocoding.py` all need
  `set_location(lat, lon)` called before `read()` returns anything —
  `Pipeline._run_sensor` calls this automatically after a successful
  Location poll (see `LOCATION_DEPENDENT_SENSORS`), and `window.py` seeds
  all three from a manual lat/lon in Settings when Location is off.

### Adding a new sensor

1. Implement `BaseSensor`.
2. In `pipeline.py`, add the source name to `DEFAULT_INTERVALS` (and to
   `LOCATION_DEPENDENT_SENSORS` if it needs a lat/lon) and `EVENT_NAMES`.
   Wire it up from `window.py` via the generic `Pipeline.set_sensor(source,
   sensor, enabled)` and `Pipeline.set_interval(source, seconds)` — no new
   `Pipeline` methods needed, the dict-keyed design in `__init__`/`run()`
   already covers it.
3. In `window.py`, add an `IORow` to `_build_sensors_column`, plus a
   caption (`_build_caption`) naming the service/sensor and an interval row
   (`_build_interval_row`) right under it, wire the `IORow.toggled` signal
   to lazily construct the sensor and call `Pipeline.set_sensor`, wire the
   interval spin box's `valueChanged` to `Pipeline.set_interval`, and add
   its name to the `sensor_activity` → LED lookup dict in
   `_on_sensor_activity`.
4. Add persisted `<name>_enabled` and `<name>_poll_interval_seconds`
   properties to `config/settings.py` (copy the `location_enabled` /
   `location_poll_interval_seconds` pattern).
5. Add a Spacebrew payload builder in `spacebrew/events.py` (type suffix in
   `SpacebrewClient.PUBLISHERS` must match the payload shape — `:json` for
   a JSON object, `:string` for plain text) and a branch in `window.py`'s
   `_on_environment_event` / `_publish_event`. MQTT is optional per event —
   `location_name` (the `place` pub) is Spacebrew-only with no
   `mqtt_events` builder at all, since there was no need for it; add one in
   `mqtt/events.py` too if the new sensor should also reach MQTT
   subscribers.

A stub sensor with no backend yet (e.g. **Air Quality Sensor**, a
placeholder for a future physical sensor) skips all of this — it's just an
`IORow` with `set_disabled_stub(...)` and no `Pipeline` wiring at all, same
as VaporwareSoundObserver's Song Generator placeholder. It gets a caption
too (e.g. "TBD — no sensor connected yet") but no interval row, since
there's nothing to schedule.

### Adding a new actuator

No actuator engine exists yet — `_build_actuators_column` in `window.py`
holds three disabled stub rows (Thermostat, Scent Emitter, Air Filter),
each an `IORow.set_disabled_stub(...)` with no backend wired up, mirroring
VaporwareSoundObserver's Song Generator placeholder. When one of these (or
a new one) gets a real backend, follow VaporwareSoundObserver's output
pattern: a plain function in a new `actuators/` package, swap that row's
stub for a live `toggled` connection, a persisted toggle in
`config/settings.py`, and — if it does network I/O — dispatch on a
`threading.Thread(daemon=True)` so it never blocks the Qt main thread.

---

## Session recording

`app/session_recorder.py`'s `SessionRecorder` gives every Start/Stop
Session cycle its own file in `Sessions/` (project root, resolved via
`Path(__file__).resolve().parent.parent.parent` from
`app/session_recorder.py`, so it lands next to `README.md` regardless of
the working directory the app was launched from). `window.py` owns one
`SessionRecorder` instance for the window's lifetime and drives it
alongside `Pipeline.start()`/`stop()` in `_toggle_session`:

- `start()` creates `Sessions/` if needed, opens
  `<YYYY-MM-DD_HH-MM-SS>.jsonl` named for the moment the session started,
  and writes a `SessionStarted` line.
- Every `environment_event` — regardless of the MQTT/Spacebrew publish
  toggles, which only gate *external* publishing — gets a `record(event)`
  call in `_on_environment_event`, appending a line with an added
  `timestamp` field.
- `stop()` writes a `SessionStopped` line and closes the file. `closeEvent`
  calls it too, so quitting mid-session still closes the file cleanly
  instead of leaving it open.

JSONL (one JSON object per line, `flush()`ed after every write) rather
than a single JSON array, so a crash mid-session leaves everything up to
that point readable instead of one truncated, unparseable file.

---

## Widgets

`app/widgets/` (`LedIndicator`, `ToggleSwitch`, `IORow`, `LiveFeedWidget`)
and `app/style.py` are carried over from VaporwareSoundObserver unchanged —
see that project's `docs/ARCHITECTURE.md` for the full rationale. Adaptations
here: `style.py` renames the sound app's `#micStatus` selector to the more
generic `#statusLabel`, drops the speech-specific `#wordTicker` style, and
adds `#sensorCaption` — a small muted style used by `window.py`'s
`_build_caption` for the "which service/sensor is this" label under each
Sensors-column row, and reused (via `#statusLabel`) for the "Update every"
text in `_build_interval_row`.

---

## Settings persistence

`config/settings.py` wraps `QSettings("Vaporware", "VaporwareEnvironmentObserver")`,
following the same flat `@property`/`@x.setter` pattern as the sibling
app's `config/settings.py` — one pair per persisted value, deliberately not
abstracted further since there are only a handful.
