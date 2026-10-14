"""Use fresh account-scoped broker dates for paper futures order inquiries.

The published same-day blank-date contract conflicts with an observed paper
response. This adapter uses CIDBQ01500's explicit current-date echo, never a
machine date, and does not cache it across calls or relax unavailable evidence.
"""
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import re
import time

from programgarden.database.broker_evidence import StartupEvidenceUnavailable, checked_body


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
    day: str
    account: str = field(repr=False)
    scope: PaperFuturesScope = field(repr=False)

    async def check_orders(self, ls, response, query):
        self.scope.check(ls)
        body = await checked_body(response, "CIDBQ02400", query, paper_trading=True)
        echo = body["CIDBQ02400OutBlock1"]
        request = next(iter(query.request_data.body.values()))
        expected = request.model_dump(exclude={"RecCnt"})
        if (request.ThdayTpCode != "1" or request.QrySrtDt != self.day
                or request.QryEndDt != self.day or not isinstance(echo, dict)
                or echo.get("AcntNo") != self.account
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
    day, account = echo.get("QryDt"), echo.get("AcntNo")
    if not isinstance(day, str) or not re.fullmatch(r"[0-9]{8}", day):
        raise StartupEvidenceUnavailable("CIDBQ01500: unavailable_business_date")
    try:
        datetime.strptime(day, "%Y%m%d")
    except ValueError:
        raise StartupEvidenceUnavailable("CIDBQ01500: invalid_business_date") from None
    if not isinstance(account, str) or not account.strip():
        raise StartupEvidenceUnavailable("CIDBQ01500: unavailable_account_echo")
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
