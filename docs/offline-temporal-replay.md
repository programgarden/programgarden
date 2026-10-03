# Bounded offline temporal replay

October 3 candidate, not packaged or deployed. The default `replay()` and worker
behavior remain limited to 32 subsequent events. An offline acceptance caller
may explicitly supply `event_limit=N`, an integer from 0 through 4096, to both
`programgarden.validation_replay.replay` and
`programgarden.replay_scenarios.check_final_expectations`. A fixture cannot raise
its own limit. The existing total timeout still applies.

This executes every recorded event in the actual scheduler with one disposable
SQLite store, clock and simulated order book. It neither restarts state between
days nor skips quiet minutes. Schedule events must remain the next configured
cron instant, and configured count/duration bounds still apply. The event list
is checked before initial execution. A runtime pass alone is not acceptance:
independent initial/per-event output, path and financial assertions are required.
Skipped descendants may retain their previous output; verify non-execution and
unchanged financial state rather than assuming all skipped outputs become empty.

```python
result = await replay(graph, fixture, timeout=180, event_limit=1440)
assert result.passed, result.errors
check_final_expectations(result, fixture, graph, event_limit=1440)
```

Long acceptance must run in an isolated, credential-free environment. This change
does not automatically lengthen chat save checks, expose a new worker endpoint,
certify exchange holiday calendars, persist across process restarts, or authorize
live orders. Native source identity changes, so any future host/worker rollout
must keep the existing matching-runtime checks; no existing proof is reusable.

Validation: 32 focused replay/SQLite tests, including 48 hourly events across two
days, fresh state on a separate run, rejection of a missing cron instant, bounded
integer limits and a wrong intermediate state despite a correct final count.
An unchanged owner-only QA minute strategy also passed 1,382 consecutive events
in a networkless Linux container: one entry per date, exit after each entry,
no closed-session calculation/orders, four exact simulated orders, and independent
cash/reservation/position/order assertions at every event. This was 5.736 seconds
for that fixture, not a chat latency benchmark. Synthetic weekdays/full immediate
fills do not establish holidays, partial fills, rejection or arbitrary strategies.

The separate default replay/workspace/contracts/scenario regression set passed87
tests. Both sets exclude broker/model calls. No running preview was restarted.
