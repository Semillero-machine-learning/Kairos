"""The one place where "today" is decided.

Due dates are calendar days in Colombia, not instants (data-model.md 5): a task
due on the 20th is late on the 21st in Bogotá, whatever the server's clock says.
Timestamps are stored in UTC (RNF-06), so both helpers live here together and no
module has to remember which of the two it needs.

A bare ``datetime.now()`` anywhere in the codebase is a bug: on Render the
process runs in UTC, so at 7 p.m. Bogotá time it already believes it is tomorrow
and would mark a task overdue a day early.
"""

import datetime
from zoneinfo import ZoneInfo

BOGOTA_TZ = ZoneInfo("America/Bogota")


def now_utc() -> datetime.datetime:
    """Current instant, timezone-aware, for columns stored as timestamptz."""
    return datetime.datetime.now(datetime.UTC)


def today_in_bogota() -> datetime.date:
    """The calendar day due dates are compared against (RN-26 fixes the zone)."""
    return datetime.datetime.now(BOGOTA_TZ).date()
