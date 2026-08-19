from __future__ import annotations

from datetime import datetime
from pathlib import Path
import atexit
import faulthandler
import os
import sys
import threading
import traceback

_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _ROOT / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_CRASH_LOG = _LOG_DIR / "runtime_crash_v23618.log"
_FAULT_LOG = _LOG_DIR / "runtime_faulthandler_v23618.log"

_fault_handle = None
_installed = False


def _stamp() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def _append(message: str) -> None:
    try:
        with _CRASH_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"[{_stamp()}] pid={os.getpid()} {message}\n")
    except Exception:
        pass


def install_runtime_crash_diagnostics_v23618() -> None:
    global _installed, _fault_handle
    if _installed:
        return
    _installed = True

    _append("DIAGNOSTICS_INSTALLED")

    try:
        _fault_handle = _FAULT_LOG.open("a", encoding="utf-8")
        faulthandler.enable(file=_fault_handle, all_threads=True)
        _append(f"FAULTHANDLER_ENABLED path={_FAULT_LOG}")
    except Exception as exc:
        _append(f"FAULTHANDLER_ENABLE_FAILED {type(exc).__name__}: {exc}")

    previous_sys_hook = sys.excepthook

    def sys_hook(exc_type, exc_value, exc_tb):
        try:
            rendered = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            _append("UNHANDLED_MAIN_EXCEPTION\n" + rendered)
        finally:
            previous_sys_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = sys_hook

    previous_thread_hook = getattr(threading, "excepthook", None)

    def thread_hook(args):
        try:
            rendered = "".join(
                traceback.format_exception(
                    args.exc_type,
                    args.exc_value,
                    args.exc_traceback,
                )
            )
            _append(
                f"UNHANDLED_THREAD_EXCEPTION thread={getattr(args.thread,'name',None)}\n"
                + rendered
            )
        finally:
            if previous_thread_hook is not None:
                previous_thread_hook(args)

    if previous_thread_hook is not None:
        threading.excepthook = thread_hook

    def on_exit():
        _append("PROCESS_ATEXIT")
        try:
            if _fault_handle is not None:
                _fault_handle.flush()
        except Exception:
            pass

    atexit.register(on_exit)


def crash_diagnostics_status_v23618() -> dict[str, str | bool | int]:
    return {
        "installed": _installed,
        "pid": os.getpid(),
        "crash_log": str(_CRASH_LOG),
        "fault_log": str(_FAULT_LOG),
    }
