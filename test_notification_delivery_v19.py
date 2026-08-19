from datetime import datetime, time
from types import SimpleNamespace
from app.services.notification_delivery_service import in_quiet_hours, next_allowed_time


def test_overnight_quiet_hours():
    prefs = SimpleNamespace(quiet_hours_enabled=True, quiet_start='22:00', quiet_end='08:00')
    assert in_quiet_hours(prefs, datetime(2026, 7, 31, 23, 0))
    assert in_quiet_hours(prefs, datetime(2026, 8, 1, 7, 30))
    assert not in_quiet_hours(prefs, datetime(2026, 8, 1, 12, 0))
    assert next_allowed_time(prefs, datetime(2026, 7, 31, 23, 0)) == datetime(2026, 8, 1, 8, 0)
