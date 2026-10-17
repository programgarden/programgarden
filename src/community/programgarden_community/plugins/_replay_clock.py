"""The replay fixture clock for plugins that read the current date or time.

A credential-free replay (programgarden ``validation_replay``) runs a workflow
at one fixed instant, ``context.validation_as_of`` (an ISO-8601 string with a
timezone). A plugin that compares a stored or parsed date with "now" reads that
instant instead of the wall clock, so the same replay always takes the same
branch. Live contexts have no ``validation_as_of`` and keep the wall clock.
"""

from datetime import datetime
from typing import Any, Optional


def fixture_now(context: Any) -> Optional[datetime]:
    """The replay instant as a naive datetime in its own offset, or None live.

    Same rule as ``programgarden_core.expression.evaluator.DateNamespace``: the
    instant keeps the wall time of the offset it was written in.
    """
    value = getattr(context, "validation_as_of", None) if context is not None else None
    if not isinstance(value, str) or not value:
        return None
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if instant.tzinfo is None or instant.utcoffset() is None:
        return None
    return instant.replace(tzinfo=None)

