import signal
import threading


def install_signal_handlers() -> threading.Event:
    """Return an Event set on SIGINT/SIGTERM, for a clean blocking shutdown wait.

    Replaces the old SIGINTHandler polling-flag class; app.py should
    `stop_event.wait()` and treat any wakeup as "shut down".
    """
    stop_event = threading.Event()

    def _handle(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    return stop_event
