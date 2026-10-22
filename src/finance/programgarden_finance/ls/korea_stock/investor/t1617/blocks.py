"""Pydantic models for LS Securities OpenAPI t1617 (investor trading aggregate v2 / 투자자매매종합2).

t1617 returns either an intraday or per-day investor net-buy time series
across a single market segment, narrowed to four primary investor
categories (개인 / 외국인 / 기관계 / 증권). The response carries:

    - ``OutBlock`` (``cont_block``) — continuation cursors plus running
      buy / sell / net-buy totals for each of the four categories.
    - ``OutBlock1`` (``block``) — list of per-bucket rows: date + time +
      one ``sv_NN`` net-buy column per category.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - The unit of every numeric column is determined by ``InBlock.gubun2``
      (1 = quantity / 2 = amount).
    - Sign convention on ``sv_*`` net-buy columns is NOT declared in the
      available source — [+, -, 0] examples preserve symmetry.
    - ``gubun1`` enum is preserved verbatim including its non-monotonic
      ordering ('0' = M풋옵션 at the end). Source labels:
      '1' = 코스피, '2' = 코스닥, '3' = 선물, '4' = 콜옵션, '5' = 풋옵션,
      '6' = 주식선물, '7' = 변동성, '8' = M선물, '9' = M콜옵션,
      '0' = M풋옵션.
    - ``cts_date`` / ``cts_time`` are LS continuation cursors; pass back
      verbatim on follow-up requests.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1617.py``
      (``gubun1='1'``, ``gubun2='1'``, ``gubun3='1'`` → KOSPI quantity
      time-bucket).
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1617RequestHeader(BlockRequestHeader):
    """t1617 request header. Inherits the standard LS request header schema."""
    pass


class T1617ResponseHeader(BlockResponseHeader):
    """t1617 response header. Inherits the standard LS response header schema."""
    pass


class T1617InBlock(BaseModel):
    """t1617InBlock — input block for the investor trading-aggregate v2 query."""

    gubun1: Literal["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"] = Field(
        ...,
        title="시장구분 (Market segment)",
        description=(
            "Market segment. '1' = KOSPI (코스피), '2' = KOSDAQ (코스닥), "
            "'3' = futures (선물), '4' = call options (콜옵션), '5' = put "
            "options (풋옵션), '6' = stock futures (주식선물), '7' = "
            "volatility (변동성), '8' = mini futures (M선물), '9' = mini "
            "call options (M콜옵션), '0' = mini put options (M풋옵션). "
            "Source enum verbatim including non-monotonic '0' at the end."
        ),
        examples=["1", "2", "3"],
    )
    gubun2: Literal["1", "2"] = Field(
        ...,
        title="수량금액구분 (Quantity / amount mode)",
        description="Mode for per-investor columns. '1' = quantity (수량), '2' = amount (금액).",
        examples=["1", "2"],
    )
    gubun3: Literal["1", "2"] = Field(
        ...,
        title="일자구분 (Time-bucket / per-day mode)",
        description="Aggregation granularity. '1' = time-bucket (시간대별), '2' = per-day (일별).",
        examples=["1", "2"],
    )
    cts_date: str = Field(
        default="",
        title="연속키 일자 (Continuation date cursor)",
        description="Continuation date cursor. Empty (or single space) on the first request.",
        examples=[""],
    )
    cts_time: str = Field(
        default="",
        title="연속키 시간 (Continuation time cursor)",
        description="Continuation time cursor. Empty (or single space) on the first request.",
        examples=[""],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division code. 'K' = KRX, 'N' = NXT, 'U' = unified.",
        examples=["K", "N", "U"],
    )


class T1617Request(BaseModel):
    """t1617 request envelope."""

    header: T1617RequestHeader = T1617RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1617",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1617InBlock"], T1617InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1617"
    )


class T1617OutBlock(BaseModel):
    """t1617OutBlock — continuation + running-total block for the four primary investor categories.

    Categories: 08 = 개인, 17 = 외국인, 18 = 기관계, 01 = 증권.
    """

    cts_date: str = Field(
        default="",
        title="연속키 일자 (Continuation date cursor)",
        description="Continuation date cursor for the next paged request.",
        examples=[""],
    )
    cts_time: str = Field(
        default="",
        title="연속키 시간 (Continuation time cursor)",
        description="Continuation time cursor for the next paged request.",
        examples=[""],
    )
    ms_08: int = Field(default=0, title="개인매수 (Individual buy)", description="Individual (개인) running buy total.", examples=[1500000])
    md_08: int = Field(default=0, title="개인매도 (Individual sell)", description="Individual (개인) running sell total.", examples=[1450000])
    sv_08: int = Field(default=0, title="개인순매수 (Individual net buy)", description="Individual (개인) net buy = buy − sell.", examples=[50000, -45000, 0])
    ms_17: int = Field(default=0, title="외국인매수 (Foreign buy)", description="Foreign (외국인) running buy total.", examples=[1200000])
    md_17: int = Field(default=0, title="외국인매도 (Foreign sell)", description="Foreign (외국인) running sell total.", examples=[1150000])
    sv_17: int = Field(default=0, title="외국인순매수 (Foreign net buy)", description="Foreign (외국인) net buy.", examples=[50000, -45000, 0])
    ms_18: int = Field(default=0, title="기관계매수 (Institutional buy)", description="Institutional (기관계) running buy total.", examples=[800000])
    md_18: int = Field(default=0, title="기관계매도 (Institutional sell)", description="Institutional (기관계) running sell total.", examples=[750000])
    sv_18: int = Field(default=0, title="기관계순매수 (Institutional net buy)", description="Institutional (기관계) net buy.", examples=[50000, -45000, 0])
    ms_01: int = Field(default=0, title="증권매수 (Securities buy)", description="Securities (증권) running buy total.", examples=[150000])
    md_01: int = Field(default=0, title="증권매도 (Securities sell)", description="Securities (증권) running sell total.", examples=[140000])
    sv_01: int = Field(default=0, title="증권순매수 (Securities net buy)", description="Securities (증권) net buy.", examples=[10000, -8000, 0])


class T1617OutBlock1(BaseModel):
    """t1617OutBlock1 — per-bucket investor net-buy row.

    For ``gubun3='1'`` (time-bucket), ``date`` may be empty and ``time``
    carries the bucket. For ``gubun3='2'`` (per-day), ``date`` carries
    the bucket and ``time`` may be empty. Sign convention on ``sv_*``
    NOT declared.
    """

    date: str = Field(
        default="",
        title="날짜 (Date)",
        description="Date bucket in 'YYYYMMDD' format, when ``gubun3='2'`` (per-day).",
        examples=["", "20260228"],
    )
    time: str = Field(
        default="",
        title="시간 (Time)",
        description="Time bucket in 'HHMM' format, when ``gubun3='1'`` (time-bucket).",
        examples=["", "0900"],
    )
    sv_08: int = Field(default=0, title="개인 (Individual net buy)", description="Individual (개인) net-buy column for the bucket.", examples=[50000, -45000, 0])
    sv_17: int = Field(default=0, title="외국인 (Foreign net buy)", description="Foreign (외국인) net-buy column.", examples=[40000, -25000, 0])
    sv_18: int = Field(default=0, title="기관계 (Institutional net buy)", description="Institutional (기관계) net-buy column.", examples=[30000, -20000, 0])
    sv_01: int = Field(default=0, title="증권 (Securities net buy)", description="Securities (증권) net-buy column.", examples=[5000, -4000, 0])


class T1617Response(BaseModel):
    """t1617 response envelope."""

    header: Optional[T1617ResponseHeader] = None
    cont_block: Optional[T1617OutBlock] = Field(
        None,
        title="합계/연속 데이터 (Summary / continuation block)",
        description="Per-investor running totals + continuation cursors (cts_date, cts_time).",
    )
    block: List[T1617OutBlock1] = Field(
        default_factory=list,
        title="시간/일별 리스트 (Time / day bucket list)",
        description="Per-bucket investor net-buy rows (time-bucket or per-day per ``gubun3``).",
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
