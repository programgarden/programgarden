"""Pydantic models for LS Securities OpenAPI t1664 (investor trading aggregate chart / 투자자매매종합(차트)).

t1664 returns a flattened chart-friendly per-bucket investor net-buy
time series across a single market segment. Unlike t1601 / t1602 / t1617
which group categories under separate response blocks, t1664 returns a
single ``OutBlock1`` (no ``OutBlock``) with one row per bucket and
``tjj01``…``tjj18`` columns for each investor category alongside
program-trade decomposition (cha / bicha / totcha) and basis.

Investor-category code mapping for ``tjjNN``:
    01 = 증권 / 02 = 보험 / 03 = 투신 / 04 = 은행 / 05 = 종금 /
    06 = 기금 / 07 = 기타 / 08 = 개인 / 17 = 외국인 / 18 = 기관계.
(Same numeric coding as t1601 / t1602 family; see those modules for the
full 12-category mapping. t1664 omits 11 = 국가 / 00 = 사모펀드.)

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - The unit of every per-investor column is determined by
      ``InBlock.vagubun`` (1 = quantity / 2 = amount). Sign convention
      on ``tjjNN`` net-buy columns NOT declared — [+, -, 0] examples
      preserve symmetry.
    - Program-trade decomposition (``cha`` 차익 / ``bicha`` 비차익 /
      ``totcha`` 종합) and ``basis`` semantics not further declared in
      the available source; consume as returned by LS.
    - The ``dt`` field is documented as 일자시간 (datetime) per source —
      time ordering of rows NOT declared.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1664.py``
      (``mgubun='1'``, ``vagubun='1'``, ``bdgubun='1'`` → KOSPI quantity
      time-bucket, 20 rows).
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1664RequestHeader(BlockRequestHeader):
    """t1664 request header. Inherits the standard LS request header schema."""
    pass


class T1664ResponseHeader(BlockResponseHeader):
    """t1664 response header. Inherits the standard LS response header schema."""
    pass


class T1664InBlock(BaseModel):
    """t1664InBlock — input block for the investor trading-aggregate chart query."""

    mgubun: Literal["1", "2", "3", "4", "5"] = Field(
        ...,
        title="시장구분 (Market segment)",
        description=(
            "Market segment. '1' = KOSPI (코스피), '2' = KOSDAQ (코스닥), "
            "'3' = futures (선물), '4' = call options (콜옵션), '5' = put "
            "options (풋옵션)."
        ),
        examples=["1", "2", "3"],
    )
    vagubun: Literal["1", "2"] = Field(
        ...,
        title="금액수량구분 (Amount / quantity mode)",
        description="Mode for per-investor columns. '1' = quantity (수량), '2' = amount (금액).",
        examples=["1", "2"],
    )
    bdgubun: Literal["1", "2"] = Field(
        ...,
        title="시간일별구분 (Time-bucket / per-day mode)",
        description="Aggregation granularity. '1' = time-bucket (시간별), '2' = per-day (일별).",
        examples=["1", "2"],
    )
    cnt: int = Field(
        default=20,
        title="조회건수 (Requested row count)",
        description="Number of rows to request per page.",
        examples=[20, 100],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division code. 'K' = KRX, 'N' = NXT, 'U' = unified.",
        examples=["K", "N", "U"],
    )


class T1664Request(BaseModel):
    """t1664 request envelope."""

    header: T1664RequestHeader = T1664RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1664",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1664InBlock"], T1664InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1664"
    )


class T1664OutBlock1(BaseModel):
    """t1664OutBlock1 — per-bucket flattened investor net-buy row.

    Sign convention on ``tjjNN`` net-buy columns + ``cha`` / ``bicha`` /
    ``totcha`` program-trade decomposition NOT declared in available
    source — [+, -, 0] examples preserve symmetry.
    """

    dt: str = Field(
        default="",
        title="일자시간 (Date / datetime)",
        description=(
            "Bucket label. Per LS source the field carries either a date "
            "('YYYYMMDD') when ``bdgubun='2'`` (per-day) or a time / "
            "datetime when ``bdgubun='1'``. Treat as opaque per-mode."
        ),
        examples=["20260228", "0900"],
    )
    tjj01: int = Field(default=0, title="증권순매수 (Securities net buy)", description="Securities (증권) net-buy column.", examples=[5000, -4000, 0])
    tjj02: int = Field(default=0, title="보험순매수 (Insurance net buy)", description="Insurance (보험) net-buy column.", examples=[5000, -3000, 0])
    tjj03: int = Field(default=0, title="투신순매수 (Investment-trust net buy)", description="Investment-trust (투신) net-buy column.", examples=[10000, -8000, 0])
    tjj04: int = Field(default=0, title="은행순매수 (Bank net buy)", description="Bank (은행) net-buy column.", examples=[5000, -3000, 0])
    tjj05: int = Field(default=0, title="종금순매수 (Merchant-bank net buy)", description="Merchant-bank (종금) net-buy column.", examples=[1000, -500, 0])
    tjj06: int = Field(default=0, title="기금순매수 (Pension / fund net buy)", description="Pension / fund (기금) net-buy column.", examples=[5000, -4000, 0])
    tjj07: int = Field(default=0, title="기타순매수 (Other net buy)", description="Other (기타) net-buy column.", examples=[3000, -2000, 0])
    tjj08: int = Field(default=0, title="개인순매수 (Individual net buy)", description="Individual (개인) net-buy column.", examples=[50000, -45000, 0])
    tjj17: int = Field(default=0, title="외국인순매수 (Foreign net buy)", description="Foreign (외국인) net-buy column.", examples=[40000, -25000, 0])
    tjj18: int = Field(default=0, title="기관순매수 (Institutional net buy)", description="Institutional (기관) net-buy column.", examples=[30000, -20000, 0])
    cha: int = Field(
        default=0,
        title="차익순매수 (Arbitrage program-trade net buy)",
        description=(
            "Arbitrage (차익) program-trade net-buy column. Source label "
            "verbatim — exact computation of arbitrage vs. non-arbitrage "
            "boundary not declared in available source."
        ),
        examples=[10000, -8000, 0],
    )
    bicha: int = Field(
        default=0,
        title="비차익순매수 (Non-arbitrage program-trade net buy)",
        description="Non-arbitrage (비차익) program-trade net-buy column.",
        examples=[20000, -15000, 0],
    )
    totcha: int = Field(
        default=0,
        title="종합순매수 (Total program-trade net buy)",
        description="Total (종합 = 차익 + 비차익) program-trade net-buy column per LS convention.",
        examples=[30000, -23000, 0],
    )
    basis: float = Field(
        default=0.0,
        title="베이시스 (Basis)",
        description=(
            "Futures basis (futures price − spot price) at the bucket. "
            "Decimal scale and sign convention not further declared in "
            "available source."
        ),
        examples=[0.45, -0.30, 0.0],
    )


class T1664Response(BaseModel):
    """t1664 response envelope.

    OutBlock is absent on this TR — only ``OutBlock1`` (``block``) is
    returned (see source comment "OutBlock 없이 OutBlock1만 존재하는 TR").
    """

    header: Optional[T1664ResponseHeader] = None
    block: List[T1664OutBlock1] = Field(
        default_factory=list,
        title="차트 데이터 (Chart data)",
        description="Per-bucket flattened investor net-buy + program-trade rows.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code returned for the request.",
    )
    rsp_cd: str = ""
    rsp_msg: str = ""
    error_msg: Optional[str] = Field(
        None,
        title="오류메시지 (Error message)",
        description="Error message when the request failed; ``None`` on success.",
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
