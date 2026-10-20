from __future__ import annotations

import threading
import time

from pipeline.sensors.base import BaseSensor

_LocationDelegate = None  # built lazily by _build_delegate_class(), see below


def _build_delegate_class():
    global _LocationDelegate
    if _LocationDelegate is not None:
        return _LocationDelegate

    import objc
    from Foundation import NSObject

    class _Delegate(NSObject):
        def init(self):
            self = objc.super(_Delegate, self).init()
            if self is None:
                return None
            self.result = {}
            self.done = threading.Event()
            return self

        def locationManager_didUpdateLocations_(self, manager, locations):
            loc = locations[-1]
            coord = loc.coordinate()
            self.result["latitude"] = coord.latitude
            self.result["longitude"] = coord.longitude
            self.result["accuracy"] = loc.horizontalAccuracy()
            self.done.set()

        def locationManager_didFailWithError_(self, manager, error):
            self.result["error"] = str(error)
            self.done.set()

    _LocationDelegate = _Delegate
    return _LocationDelegate


class GPSLocationSensor(BaseSensor):
    """On-device GPS/location via macOS's CoreLocation (CLLocationManager).

    Unlike Speech.framework's completion handler (delivered on a
    framework-owned dispatch queue, so a plain threading.Event.wait() is
    enough — see AppleSpeechTranscriber), CLLocationManager delivers its
    delegate callbacks by scheduling them on the *run loop of whichever
    thread called requestLocation()*. Pipeline calls read() from its QThread,
    which only does a plain time.sleep() loop — no run loop ever gets pumped
    there — so a bare Event.wait() would block forever with the callback
    (and even the permission prompt) never actually firing. Instead, read()
    pumps that thread's CFRunLoop in short bursts via CFRunLoopRunInMode
    while checking the event, so whichever thread calls read() actually
    services CoreLocation's callbacks. Authorization is requested lazily on
    first use, which is what triggers macOS's one-time Location Services
    prompt (shown against the running process, e.g. "Python" or "Terminal"
    — no Info.plist is required for a plain command-line interpreter).
    """

    def __init__(self, timeout: float = 15.0):
        self._timeout = timeout
        self._manager = None
        self._delegate = None

    def _ensure_manager(self):
        if self._manager is not None:
            return
        import CoreLocation

        delegate_cls = _build_delegate_class()
        self._delegate = delegate_cls.alloc().init()
        self._manager = CoreLocation.CLLocationManager.alloc().init()
        self._manager.setDelegate_(self._delegate)
        self._manager.setDesiredAccuracy_(CoreLocation.kCLLocationAccuracyBest)
        self._manager.requestWhenInUseAuthorization()

    def read(self) -> dict | None:
        self._ensure_manager()

        self._delegate.result.clear()
        self._delegate.done.clear()
        self._manager.requestLocation()

        import CoreFoundation

        deadline = time.monotonic() + self._timeout
        while not self._delegate.done.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("GPS location request timed out")
            CoreFoundation.CFRunLoopRunInMode(CoreFoundation.kCFRunLoopDefaultMode, min(remaining, 0.1), False)

        result = self._delegate.result
        if "error" in result:
            raise RuntimeError(result["error"])

        return {
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "accuracy": result["accuracy"],
        }
