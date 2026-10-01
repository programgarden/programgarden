# Calendar scheduling runtime correction

The scheduler registers without firing descendants immediately. Only the source
of a due schedule_tick opens that timer's branch; another timer cannot fire a
future dated branch. Dry-run retains its existing single synthetic cycle.
Seven-field cron is seconds-first with an explicit year. Exhausted dates complete
normally after queued ticks drain; they do not roll into another year or idle
forever. The supported year range1970-2099 is searched explicitly.

Validation:26 schedule/dry-run tests and64 traversal, order-idempotency and replay
regressions. No credentials, broker calls or orders. Calendar tests execute the
actual local async engine, with future waiting, due execution, separate timers,
expired dates, leap days, day31 and2099 coverage.

This is a development candidate based on engine2.5.4. No PyPI publication or
production rollout is implied. Dev images must record this exact source commit.
