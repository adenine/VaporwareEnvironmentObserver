import sys

from PyQt6.QtWidgets import QApplication

from app.window import MainWindow

# Keeps a reference to the returned activity token for the process's whole
# lifetime; letting it get garbage-collected re-enables App Nap.
_app_nap_activity = None


def _disable_app_nap():
    """macOS App Nap throttles timers/threads for GUI apps that are
    backgrounded or occluded — which stalls Pipeline's polling loop (it's
    just a QThread doing time.sleep()) whenever this window loses focus or
    is covered by another window. There's no Info.plist to set
    NSSupportsSuddenTermination/NSAppSleepDisabled since this runs as a
    plain script, not a signed .app bundle, so opt out at runtime instead.
    """
    global _app_nap_activity
    try:
        from Foundation import NSActivityLatencyCritical, NSActivityUserInitiated, NSProcessInfo

        options = NSActivityUserInitiated | NSActivityLatencyCritical
        _app_nap_activity = NSProcessInfo.processInfo().beginActivityWithOptions_reason_(
            options, "Continuous environmental sensing on a poll timer"
        )
    except Exception:  # noqa: BLE001
        pass  # non-macOS or pyobjc unavailable — sensors that need it will error on their own


def main():
    _disable_app_nap()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
