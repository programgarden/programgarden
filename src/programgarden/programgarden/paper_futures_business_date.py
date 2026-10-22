"""Use fresh account-scoped broker dates for paper futures order inquiries.

The published same-day blank-date contract conflicts with an observed paper
response. This adapter uses CIDBQ01500's explicit current-date echo, never a
machine date, and does not cache it across calls or relax unavailable evidence.

When the paper server returns no business date at all (observed on weekends,
when its overseas futures day is closed), the order inquiry uses the published
blank-date same-day form instead, with the same response checks. This is the
form the server startup gate already uses for that answer, so a start the
server admits is not refused here.

That answer is not an error, but the run then waits for the market to open.
``BusinessDayNotice`` tells the run's listeners so through an informational
``RiskEvent`` (``broker_business_day_unavailable``), and clears it
(``broker_business_day_available``) as soon as a later read carries a date.
Its details never carry a date, an account or key material.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import logging
import re
import time

from programgarden.database.broker_evidence import StartupEvidenceUnavailable, broker_message, checked_body

logger = logging.getLogger(__name__)

_RESPONSE_CODE_REASON = "CIDBQ02400: unverified_response_code="


def broker_business_day(value):
    """The broker's explicit YYYYMMDD business date, or "" when none was given.

    A blank, missing, padded or impossible value is "no date". It is never
    replaced by a local, previous or cached date.
    """
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{8}", value):
        return ""
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError:
        return ""
    return value


def blank_date_unverified(response):
    """No business date, and the blank-date answer's code was not accepted."""
    return (f"CIDBQ02400: blank_date_unverified rsp_cd={getattr(response, 'rsp_cd', None)} "
            f"rsp_msg={broker_message(getattr(response, 'rsp_msg', None))}")


def is_paper_client(ls):
    return getattr(getattr(ls, "token_manager", None), "paper_trading", None) is True


@dataclass(frozen=True)
class PaperFuturesScope:
    manager: object = field(repr=False)
    key_digest: str = field(repr=False)
    started: float

    @classmethod
    def capture(cls, ls):
        manager = getattr(ls, "token_manager", None)
        key = getattr(manager, "appkey", None)
        if not is_paper_client(ls) or not isinstance(key, str) or not key:
            raise StartupEvidenceUnavailable("paper_futures_business_date: unavailable_client_scope")
        return cls(manager, hashlib.sha256(key.encode()).hexdigest(), time.monotonic())

    def check(self, ls):
        current = self.capture(ls)
        if current.manager is not self.manager or current.key_digest != self.key_digest:
            raise StartupEvidenceUnavailable("paper_futures_business_date: client_scope_changed")
        age = time.monotonic() - self.started
        if age < 0 or age > 60:
            raise StartupEvidenceUnavailable("paper_futures_business_date: expired_observation")


@dataclass(frozen=True)
class PaperFuturesBusinessDate:
    """One fresh CIDBQ01500 observation for the following CIDBQ02400 read.

    ``day`` is the broker's explicit business date, or "" when the paper server
    returned none; "" selects the published blank-date same-day query (both
    dates blank). ``account`` is the positions echo; it is always present with
    a date and may be "" only on a blank-date answer.
    """
    day: str
    account: str = field(repr=False)
    scope: PaperFuturesScope = field(repr=False)

    @property
    def blank_date(self):
        return not self.day

    async def check_orders(self, ls, response, query):
        self.scope.check(ls)
        try:
            body = await checked_body(response, "CIDBQ02400", query, paper_trading=True)
        except StartupEvidenceUnavailable as exc:
            # Without a business date the published blank-date form is the only
            # query left; name that case, with the broker's answer, when its
            # response code is not accepted. Other failures keep their reasons.
            if self.blank_date and str(exc).startswith(_RESPONSE_CODE_REASON):
                raise StartupEvidenceUnavailable(blank_date_unverified(response)) from None
            raise
        echo = body["CIDBQ02400OutBlock1"]
        request = next(iter(query.request_data.body.values()))
        expected = request.model_dump(exclude={"RecCnt"})
        # A dated observation always carries its account; a blank-date one binds
        # the account only when LS echoed it (the credential scope check below
        # still proves both reads used the same token, key and paper mode).
        if (request.ThdayTpCode != "1" or request.QrySrtDt != self.day
                or request.QryEndDt != self.day or not isinstance(echo, dict)
                or (self.account and echo.get("AcntNo") != self.account)
                or any(name not in echo or echo[name] != value for name, value in expected.items())):
            raise StartupEvidenceUnavailable("CIDBQ02400: business_date_scope_mismatch")
        self.scope.check(ls)
        return response.block2


async def from_current_positions(ls, response, query, scope):
    """Validate a just-fetched positions response without making another call."""
    scope.check(ls)
    body = await checked_body(response, "CIDBQ01500", query, paper_trading=True)
    echo = body["CIDBQ01500OutBlock1"]
    request = next(iter(query.request_data.body.values()))
    expected = {"AcntTpCode": "1", "QryDt": "", "BalTpCode": "2", "FcmAcntNo": ""}
    if any(getattr(request, name) != value for name, value in expected.items()):
        raise StartupEvidenceUnavailable("CIDBQ01500: current_date_query_required")
    if not isinstance(echo, dict) or any(echo.get(name) != value for name, value in expected.items() if name != "QryDt"):
        raise StartupEvidenceUnavailable("CIDBQ01500: business_date_scope_mismatch")
    day, account = broker_business_day(echo.get("QryDt")), echo.get("AcntNo")
    if not isinstance(account, str) or not account.strip():
        if day:
            raise StartupEvidenceUnavailable("CIDBQ01500: unavailable_account_echo")
        account = ""
    if not day:
        # Weekend paper answers carry no business date. The server startup gate
        # uses the blank-date order form for this answer; so does the engine.
        logger.info("CIDBQ01500: paper server returned no business date; "
                    "using the published blank-date CIDBQ02400 same-day form")
    scope.check(ls)
    return PaperFuturesBusinessDate(day, account, scope)


async def read_current_business_date(ls):
    """One bounded read; the SDK retains its existing shared-key rate limiter."""
    from programgarden_finance import CIDBQ01500

    scope = PaperFuturesScope.capture(ls)
    query = ls.overseas_futureoption().accno().CIDBQ01500(body=CIDBQ01500.CIDBQ01500InBlock1(
        RecCnt=1, AcntTpCode="1", FcmAcntNo="", QryDt="", BalTpCode="2"))
    response = await query.req_async()
    return await from_current_positions(ls, response, query, scope)


# --- Waiting notice: the paper server gave no business date -------------------
#
# A blank CIDBQ01500 QryDt is not an error (see above), but the run then has no
# broker business day: on a weekend or before the open nothing trades until the
# market opens. Hosts forward RiskEvent to their screens unchanged, so the
# notice uses that existing event with severity "info" and two event types.
# It is never a failure, never halts or releases an order, and its details never
# carry a date or time (not the missing business date, not a local or previous
# one), an account echo or key material; hosts stamp their own receive time.

BUSINESS_DAY_UNAVAILABLE = "broker_business_day_unavailable"
BUSINESS_DAY_AVAILABLE = "broker_business_day_available"
INFORMATIONAL_BROKER_EVENT_TYPES = frozenset({BUSINESS_DAY_UNAVAILABLE, BUSINESS_DAY_AVAILABLE})
MARKET_OPEN_WAIT_NOTICE = "market_open_wait"
# At most one extra CIDBQ01500 read per this many seconds while the notice is
# active, and only when the run is doing work (a broker node cycle or a
# realtime event). Nothing is read on a quiet weekend.
RECHECK_AFTER_SEC = 300
# A still-active notice is repeated at most this often, for screens that join
# while the run waits. No broker read is made for a repeat.
REPEAT_AFTER_SEC = 60
RECHECK_TIMEOUT_SEC = 30


class BusinessDayNotice:
    """Per-run state of the waiting notice (one ExecutionContext).

    Observations are applied in the order their reads started, so a slower
    read that began before a newer answer cannot undo it. A re-check that is
    refused or fails keeps the current state and sends nothing.
    """

    def __init__(self):
        self.active = False
        self.broker_node_id = None
        self._ls = None
        self._last_read = None
        self._last_applied_read = None
        self._last_sent = None
        self._in_flight = False
        self._background = None

    def due(self, now=None):
        """Active and no read has started for RECHECK_AFTER_SEC seconds."""
        now = time.monotonic() if now is None else now
        return (self.active and not self._in_flight and self._ls is not None
                and (self._last_read is None or now - self._last_read >= RECHECK_AFTER_SEC))

    def _repeat_due(self, now):
        return self._last_sent is not None and now - self._last_sent >= REPEAT_AFTER_SEC

    def needs_refresh(self, now=None):
        """A re-check or a repeat is due (cheap; no broker call)."""
        now = time.monotonic() if now is None else now
        return self.active and not self._in_flight and (self.due(now) or self._repeat_due(now))

    async def observe(self, context, paper_day, *, source, ls, broker_node_id=None):
        """Apply one validated CIDBQ01500 observation (no extra call)."""
        if paper_day is None:
            return
        started = paper_day.scope.started
        if self._last_applied_read is not None and started < self._last_applied_read:
            return
        self._last_applied_read = started
        self._last_read = started if self._last_read is None else max(self._last_read, started)
        if broker_node_id and not self.broker_node_id:
            self.broker_node_id = broker_node_id
        if paper_day.day:
            if self.active:
                self.active, self._ls = False, None
                logger.info("CIDBQ01500: paper server returned a business date again; waiting notice cleared")
                await self._send(context, active=False, source=source)
            return
        self._ls = ls
        if not self.active:
            self.active = True
            await self._send(context, active=True, source=source)
        elif self._last_sent is None or self._repeat_due(time.monotonic()):
            await self._send(context, active=True, source=source)

    async def refresh(self, context, source):
        """At a work moment: re-read when due, else repeat a still-active notice."""
        if not self.active or self._in_flight:
            return
        now = time.monotonic()
        if self.due(now):
            await self.recheck(context, source)
        elif self._repeat_due(now):
            await self._send(context, active=True, source=source)

    async def recheck(self, context, source):
        """One bounded CIDBQ01500 read on the run's existing client."""
        ls = self._ls
        if not self.active or self._in_flight or ls is None or not is_paper_client(ls):
            return
        if not getattr(context, "is_running", True) or getattr(context, "is_shutdown", False):
            return
        self._in_flight = True
        self._last_read = time.monotonic()
        try:
            paper_day = await asyncio.wait_for(read_current_business_date(ls), timeout=RECHECK_TIMEOUT_SEC)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Refused, partial or unreachable: keep the notice, try again later.
            logger.info("CIDBQ01500 business-date re-check unavailable (%s); waiting notice kept",
                        type(exc).__name__)
            return
        finally:
            self._in_flight = False
        await self.observe(context, paper_day, source=source, ls=ls)

    async def _send(self, context, *, active, source):
        from programgarden_core.bases.listener import RiskEvent

        self._last_sent = time.monotonic()
        notify = getattr(context, "notify_risk_event", None)
        if notify is None:
            return
        try:
            await notify(RiskEvent(
                job_id=getattr(context, "job_id", None),
                event_type=BUSINESS_DAY_UNAVAILABLE if active else BUSINESS_DAY_AVAILABLE,
                severity="info",
                action_hint="advisory",
                details={
                    "notice": MARKET_OPEN_WAIT_NOTICE,
                    "active": active,
                    "broker_node_id": self.broker_node_id,
                    "product": "overseas_futures",
                    "trading_mode": "paper",
                    "source": source,
                    "evidence": "CIDBQ01500.QryDt",
                    "recheck_after_sec": RECHECK_AFTER_SEC,
                    "is_error": False,
                    "is_trade": False,
                },
            ))
        except Exception as exc:  # A listener problem never fails the run.
            logger.warning("Waiting notice delivery failed: %s", type(exc).__name__)


def business_day_notice(context):
    """This run's notice, or None where none may be sent.

    dry_run, deep_validate and replay validation (a dry_run) never send it, and
    an object that is not an execution context (a bare test double) has none.
    """
    if getattr(context, "is_dry_run", False) or not hasattr(context, "_business_day_notice"):
        return None
    notice = context._business_day_notice
    if notice is None:
        notice = context._business_day_notice = BusinessDayNotice()
    return notice


async def observe_business_day(context, paper_day, *, source, ls, broker_node_id=None):
    """Record a paper observation without ever failing the caller."""
    notice = business_day_notice(context)
    if notice is None or paper_day is None or not is_paper_client(ls):
        return
    try:
        await notice.observe(context, paper_day, source=source, ls=ls, broker_node_id=broker_node_id)
    except Exception as exc:
        logger.warning("Waiting notice update failed: %s", type(exc).__name__)


def refresh_business_day_notice_in_background(context, source, start_task):
    """Schedule one refresh when due, through the caller's task registry.

    For work moments that must not wait for a broker read (realtime updates
    and later broker-node cycles).
    ``start_task(coroutine)`` returns the task, or None when the run is
    shutting down. At most one refresh is pending at a time.
    """
    notice = business_day_notice(context)
    if notice is None or not notice.needs_refresh():
        return None
    if notice._background is not None and not notice._background.done():
        return None
    notice._background = start_task(refresh_business_day_notice(context, source))
    return notice._background


async def refresh_business_day_notice(context, source):
    """Re-check an active notice at a work moment without ever failing the caller."""
    notice = business_day_notice(context)
    if notice is None or not notice.active:
        return
    try:
        await notice.refresh(context, source)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("Waiting notice re-check failed: %s", type(exc).__name__)
