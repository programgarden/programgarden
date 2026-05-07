"""Pydantic models for LS Securities OpenAPI FOCCQ33600 (Account Periodic Return Detail).

FOCCQ33600 returns periodic performance metrics for a Korean cash-equity
account over a date range, broken down at daily / weekly / monthly
granularity per ``TermTp``. Three response blocks are returned:
    - ``FOCCQ33600OutBlock1`` (block1): echo-back of the input parameters.
    - ``FOCCQ33600OutBlock2`` (block2): account-level summary — display
      name, total trade contract amount, deposits and withdrawals, average
      invested principal balance, total invested PnL and total invested
      return rate.
    - ``FOCCQ33600OutBlock3`` (block3): per-period rows — base date, opening
      and closing valuation, average invested principal balance, trade
      contract amount, securities-equivalent in / out flows, evaluation PnL,
      period return rate and a benchmark index value.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class FOCCQ33600RequestHeader(BlockRequestHeader):
    """FOCCQ33600 request header. Inherits the standard LS request header schema."""
    pass


class FOCCQ33600ResponseHeader(BlockResponseHeader):
    """FOCCQ33600 response header. Standard LS response header schema."""
    pass


class FOCCQ33600InBlock1(BaseModel):
    """FOCCQ33600InBlock1 — input block for account periodic return detail.

    Specify the date range with ``QrySrtDt`` / ``QryEndDt`` (YYYYMMDD) and
    the per-row granularity with ``TermTp`` (daily / weekly / monthly).
    """

    QrySrtDt: str = Field(
        default="",
        title="조회시작일 (Query start date, YYYYMMDD)",
        description="Inclusive lower bound of the query date range.",
        examples=["", "20260101", "20260201"],
    )
    QryEndDt: str = Field(
        default="",
        title="조회종료일 (Query end date, YYYYMMDD)",
        description="Inclusive upper bound of the query date range.",
        examples=["", "20260131", "20260228"],
    )
    TermTp: Literal["1", "2", "3"] = Field(
        default="1",
        title="기간구분 (Period granularity)",
        description=(
            "Per-row granularity. '1' = 일별 (daily, default), '2' = 주별 "
            "(weekly), '3' = 월별 (monthly). Length 1."
        ),
        examples=["1", "2", "3"],
    )


class FOCCQ33600Request(BaseModel):
    """FOCCQ33600 full request envelope (header + body + setup options)."""

    header: FOCCQ33600RequestHeader = FOCCQ33600RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="FOCCQ33600",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: dict[Literal["FOCCQ33600InBlock1"], FOCCQ33600InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="FOCCQ33600",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class FOCCQ33600OutBlock1(BaseModel):
    """FOCCQ33600OutBlock1 — input echo-back block."""

    QrySrtDt: str = Field(
        default="",
        title="조회시작일 (Query start date, YYYYMMDD)",
        description="Echo of the input ``QrySrtDt``.",
        examples=["", "20260101"],
    )
    QryEndDt: str = Field(
        default="",
        title="조회종료일 (Query end date, YYYYMMDD)",
        description="Echo of the input ``QryEndDt``.",
        examples=["", "20260131"],
    )
    TermTp: str = Field(
        default="1",
        title="기간구분 (Period granularity)",
        description=(
            "Echo of the input ``TermTp`` ('1' = daily, '2' = weekly, "
            "'3' = monthly)."
        ),
        examples=["1", "2", "3"],
    )


class FOCCQ33600OutBlock2(BaseModel):
    """FOCCQ33600OutBlock2 — account-level return summary block.

    Returns aggregate metrics across the requested date range: trade
    contract amount, total deposits and withdrawals, average invested
    principal balance, total invested PnL and total invested return rate.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of records returned. Always 1 for this summary block.",
        examples=[0, 1],
    )
    AcntNm: str = Field(
        default="",
        title="계좌명 (Account display name)",
        description="Korean display name of the account.",
        examples=["", "홍길동"],
    )
    BnsctrAmt: int = Field(
        default=0,
        title="매매약정금액 (Trade contract amount)",
        description=(
            "Total trade contract amount across the requested date range. "
            "Currency: KRW."
        ),
        examples=[0, 100_000_000],
    )
    MnyinAmt: int = Field(
        default=0,
        title="입금 (Deposit)",
        description=(
            "Total deposit amount across the requested date range. "
            "Currency: KRW."
        ),
        examples=[0, 5_000_000],
    )
    MnyoutAmt: int = Field(
        default=0,
        title="출금 (Withdrawal)",
        description=(
            "Total withdrawal amount across the requested date range. "
            "Currency: KRW."
        ),
        examples=[0, 1_000_000],
    )
    InvstAvrbalPramt: int = Field(
        default=0,
        title="투자원금평잔 (Average invested principal balance)",
        description=(
            "Average invested principal balance across the requested date "
            "range, used as the denominator of the invested return rate. "
            "Currency: KRW."
        ),
        examples=[0, 80_000_000],
    )
    InvstPlAmt: int = Field(
        default=0,
        title="투자손익 (Invested PnL)",
        description=(
            "Total invested profit and loss across the requested date range. "
            "Sign convention follows LS server output. Currency: KRW."
        ),
        examples=[0, 5_000_000, -1_500_000],
    )
    InvstErnrat: float = Field(
        default=0.0,
        title="투자수익률 (Invested return rate)",
        description=(
            "Invested return rate across the requested date range, in percent. "
            "LS may serialize this value as a string; Pydantic auto-coerces "
            "to float."
        ),
        examples=[0.0, 6.25, -1.84],
    )


class FOCCQ33600OutBlock3(BaseModel):
    """FOCCQ33600OutBlock3 — per-period return detail row.

    Each row describes one period at the granularity selected by ``TermTp``,
    with opening / closing valuation, average invested principal balance,
    trade contract amount, securities-equivalent in / out flows, evaluation
    PnL, period return rate and a benchmark index value.
    """

    BaseDt: str = Field(
        default="",
        title="기준일 (Base date, YYYYMMDD)",
        description=(
            "Base date of the period (period-end date for weekly / monthly "
            "rows)."
        ),
        examples=["", "20260203", "20260228"],
    )
    FdEvalAmt: int = Field(
        default=0,
        title="기초평가 (Opening valuation)",
        description=(
            "Account valuation at the start of the period. Currency: KRW."
        ),
        examples=[0, 80_000_000],
    )
    EotEvalAmt: int = Field(
        default=0,
        title="기말평가 (Closing valuation)",
        description=(
            "Account valuation at the end of the period. Currency: KRW."
        ),
        examples=[0, 82_500_000],
    )
    InvstAvrbalPramt: int = Field(
        default=0,
        title="투자원금평잔 (Average invested principal balance)",
        description=(
            "Average invested principal balance over the period. "
            "Currency: KRW."
        ),
        examples=[0, 80_000_000],
    )
    BnsctrAmt: int = Field(
        default=0,
        title="매매약정 (Trade contract amount)",
        description=(
            "Total trade contract amount during the period. Currency: KRW."
        ),
        examples=[0, 5_000_000],
    )
    MnyinSecinAmt: int = Field(
        default=0,
        title="입금고액 (Deposit / securities-in amount)",
        description=(
            "Total deposit amount and securities-in (transfer-in) value during "
            "the period. Currency: KRW."
        ),
        examples=[0, 1_000_000],
    )
    MnyoutSecoutAmt: int = Field(
        default=0,
        title="출금고액 (Withdrawal / securities-out amount)",
        description=(
            "Total withdrawal amount and securities-out (transfer-out) value "
            "during the period. Currency: KRW."
        ),
        examples=[0, 500_000],
    )
    EvalPnlAmt: int = Field(
        default=0,
        title="평가손익 (Evaluation PnL)",
        description=(
            "Evaluation profit and loss for the period. Sign convention "
            "follows LS server output. Currency: KRW."
        ),
        examples=[0, 2_500_000, -800_000],
    )
    TermErnrat: float = Field(
        default=0.0,
        title="기간수익률 (Period return rate)",
        description=(
            "Period return rate in percent. LS may serialize this value as a "
            "string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 3.13, -1.00],
    )
    Idx: float = Field(
        default=0.0,
        title="지수 (Benchmark index)",
        description=(
            "Benchmark index value reported alongside the period return. The "
            "specific index used is not declared in the available LS source — "
            "consume as returned by LS."
        ),
        examples=[0.0, 2_500.50, 850.20],
    )


class FOCCQ33600Response(BaseModel):
    """FOCCQ33600 full API response envelope."""

    header: Optional[FOCCQ33600ResponseHeader] = None
    block1: Optional[FOCCQ33600OutBlock1] = Field(
        default=None,
        title="FOCCQ33600OutBlock1 (Input echo-back)",
        description="Echo-back of the input parameters.",
    )
    block2: Optional[FOCCQ33600OutBlock2] = Field(
        default=None,
        title="FOCCQ33600OutBlock2 (Return summary)",
        description=(
            "Account-level summary across the requested date range: trade "
            "contract amount, deposits / withdrawals, average invested "
            "principal balance, invested PnL and return rate."
        ),
    )
    block3: List[FOCCQ33600OutBlock3] = Field(
        default_factory=list,
        title="FOCCQ33600OutBlock3 (Per-period detail list)",
        description=(
            "List of per-period rows at the granularity selected by ``TermTp``."
        ),
    )
    status_code: Optional[int] = Field(default=None, title="HTTP status code")
    rsp_cd: str = Field(default="", title="Response code")
    rsp_msg: str = Field(default="", title="Response message")
    error_msg: Optional[str] = Field(default=None, title="Error message")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
