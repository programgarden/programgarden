# Account continuation, reconnect registration and retry control

Finance 2.0.3. Sources: LS OpenAPI TR guide v20261012053652748 (guide) and the
offline tests named below. Nothing here was verified against a live broker
continuation page.

## Header-only continuation for six account TRs

`CSPAQ13700`, `COSAQ00102`, `COSOQ00201`, `CIDBQ01500`, `CIDBQ01800` and
`CIDBQ02400` gained `occurs_req(callback=None, delay=1, *, max_pages=100)` and
`occurs_req_async(...)`.

- The guide gives these TRs the common request headers `tr_cont` and
  `tr_cont_key` ("연속일 경우 그전에 내려온 연속키 값 올림") and no body cursor.
  The next page re-sends the same body with `tr_cont="Y"` and the previous
  response's `tr_cont_key`.
- `SrtOrdNo2` (CSPAQ13700) and `SrtOrdNo` (COSAQ00102) are starting values in
  the guide (reverse 999999999, forward 0); they are not changed between
  pages. Earlier SDK docstrings described a body cursor ("smallest order number
  minus 1", "feed back an OrdNo"); that rule had no source and was removed.
- Every page passes the TR's own rate limiter; `delay` seconds are slept
  between pages.
- The result is the list of page responses. Rows are never merged.
- A failed page is kept as the last element. The walk also stops, keeping the
  last successful page (still `tr_cont="Y"`), when the key is blank, repeats,
  or `max_pages` is reached.
- `programgarden_finance.ls.tr_helpers.occurs_complete(pages)` is true only
  when no page failed and the last page did not announce another page.
  Consumers must treat anything else as a partial list.
- The request header's `tr_cont`/`tr_cont_key` are restored after the walk.

The older `t0425`-style `occurs_req` helpers on other TRs are unchanged (they
drop a failed later page and report it only through the callback).

Tests: `tests/test_account_continuation.py` (real request/response models,
mocked HTTP, sockets denied).

## Account-event registration after a reconnect

`Real(..., reregister_account_events_on_reconnect=True)` (also on the
`real()` factories of the three product clients) re-sends the account
registration (`tr_type="1"`) of every family still in use after a reconnect,
right after the existing market-data resubscription:

| Product | Flag | Registration sent |
|---|---|---|
| Overseas stock | `_as01234_connect` | `AS1`, `tr_key=""` |
| Domestic stock | `_sc01234_connect` | `SC1`, `tr_key=""` |
| Overseas futures | `_tc123_connect` | `TC1`, `tr_key=""` |

A registration is a message on one socket, so the default assumes it does not
survive a new connection. Phase-0 item F3 checks this on paper futures; if LS
keeps the registration, the default becomes `False`. With `False` the flags
are left as they were (previous behaviour).

Reconnects are now detected by "this loop already had an open socket" rather
than `backoff > 1.0`, which missed reconnects when `max_backoff <= 1`.

Tests: `tests/test_real_account_reregistration.py` (local websocket server).

## Overseas futures account unregister

When the last listener of a futures `Real` is removed, the client sends one
`tr_type="2"` frame with the same body it registered with (`tr_cd="TC1"`,
`tr_key=""`) and clears `_tc123_connect`; a later listener registers again.
The guide marks only `tr_key` as optional for account register/unregister, so
`tr_cd` is kept. Whether an unregister on one session affects another session
on the same key is not yet observed (phase-0 F2).

The stock clients' unregister paths are unchanged: `_on_remove_message`
clears `_as01234_connect`/`_sc01234_connect` before calling the unregister
methods, so those methods never send. This is recorded, not changed here.

## `SetupOptions.transient_retries`

`None` (default) keeps the 0.5/1.5/3.0 s spaced retries for transient read
failures (5xx, 429, timeouts). `n` (0–3) keeps the first `n` delays. With `0`
the SDK neither retries nor performs the "ladder exhausted → reissue the token"
step, so a caller that paces requests itself (for example through a shared
lane) never triggers a competing token on a rate-limit error. Explicit token
failures follow the token manager's policy as before. Order endpoints never
retry transient failures.

Tests: `tests/test_transient_retries_option.py`.
