"""Pydantic models for LS Securities OpenAPI t1602 (intraday investor trading trend / 시간대별투자자매매추이).

t1602 returns a per-time-bucket investor-by-category net-buy time series
for a single market segment + sector. The response carries:

    - ``OutBlock`` (``cont_block``) — header / continuation block:
      continuation cursor (``cts_time``) + per-investor running totals
      (buy / sell / delta / net buy) + sector code echo.
    - ``OutBlock1`` (``block``) — list of per-time-bucket rows: time +
      one ``sv_NN`` net-buy column per investor category.

Investor-category code mapping (consistent across the t1601 family):
    08 = 개인 / 17 = 외국인 / 18 = 기관계 / 01 = 증권 / 03 = 투신 /
    04 = 은행 / 02 = 보험 / 05 = 종금 / 06 = 기금 / 07 = 기타 /
    11 = 국가 / 00 = 사모펀드.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - The unit of every per-investor numeric column is determined by
      ``InBlock.gubun1`` (1 = quantity / 2 = amount).
    - Sign convention on ``rate_*`` (증감) and ``sv_*`` / ``svolume_*``
      (순매수) columns is NOT declared in the available source —
      [+, -, 0] examples preserve symmetry.
    - The investor-code field name on individual (``tjjcode_08``) and
      on every other category (``jjcode_NN``) differs by one character
      ("tjj" vs. "jj") per the LS source — preserved verbatim.
    - ``cts_time`` / ``cts_idx`` are LS continuation cursors; pass back
      verbatim on follow-up requests.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1602.py``
      (``market='1'``, ``upcode='001'`` → KOSPI all sectors, ``gubun1='1'``
      quantity, ``gubun2='0'`` today).
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1602RequestHeader(BlockRequestHeader):
    """t1602 request header. Inherits the standard LS request header schema."""
    pass


class T1602ResponseHeader(BlockResponseHeader):
    """t1602 response header. Inherits the standard LS response header schema."""
    pass


class T1602InBlock(BaseModel):
    """t1602InBlock — input block for the intraday investor-trading-trend query."""

    market: Literal["1", "2", "3", "4", "5", "6", "7", "8"] = Field(
        ...,
        title="시장구분 (Market segment)",
        description=(
            "Market segment. '1' = KOSPI (코스피), '2' = KOSPI 200 (KP200), "
            "'3' = KOSDAQ (코스닥), '4' = futures (선물), '5' = call options "
            "(콜옵션), '6' = put options (풋옵션), '7' = ELW, '8' = ETF."
        ),
        examples=["1", "2", "3"],
    )
    upcode: str = Field(
        ...,
        title="업종코드 (Sector code)",
        description="Sector / index code (e.g., '001' for KOSPI all-sectors).",
        examples=["001"],
    )
    gubun1: Literal["1", "2"] = Field(
        ...,
        title="수량구분 (Quantity / amount mode)",
        description="Mode for per-investor columns. '1' = quantity (수량), '2' = amount (금액).",
        examples=["1", "2"],
    )
    gubun2: Literal["0", "1"] = Field(
        ...,
        title="전일분구분 (Today / previous-day mode)",
        description="Time scope. '0' = today (당일 / 금일), '1' = previous day (전일).",
        examples=["0", "1"],
    )
    cts_time: str = Field(
        default="",
        title="연속키 시간 (Continuation time cursor)",
        description=(
            "Continuation cursor for paged queries. Empty (or single space) "
            "on the first request; on follow-ups, pass back the ``cts_time`` "
            "returned in the previous response. Treat as opaque LS-defined token."
        ),
        examples=[""],
    )
    cts_idx: int = Field(
        default=0,
        title="연속키 인덱스 (Continuation index — unused)",
        description="Continuation index. Source label states '사용안함' (not used) on this TR; default 0.",
        examples=[0],
    )
    cnt: int = Field(
        default=20,
        title="조회건수 (Requested row count)",
        description="Number of rows to request per page.",
        examples=[20, 100],
    )
    gubun3: str = Field(
        default="",
        title="직전대비구분 (Most-recent-snapshot delta flag)",
        description=(
            "Most-recent-snapshot delta flag. Source documents 'C' = "
            "직전대비 (vs. immediately preceding snapshot). Empty disables "
            "the delta computation."
        ),
        examples=["", "C"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division code. 'K' = KRX, 'N' = NXT, 'U' = unified.",
        examples=["K", "N", "U"],
    )


class T1602Request(BaseModel):
    """t1602 request envelope."""

    header: T1602RequestHeader = T1602RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1602",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1602InBlock"], T1602InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1602"
    )


class T1602OutBlock(BaseModel):
    """t1602OutBlock — header / continuation block carrying running totals across investor categories.

    Sign convention on ``rate_*`` (증감) and ``svolume_*`` (순매수)
    columns is NOT declared in the available source. The investor-code
    field name on individual is ``tjjcode_08`` while every other
    category uses ``jjcode_NN`` per the source — preserved verbatim.
    """

    cts_time: str = Field(
        default="",
        title="연속키 시간 (Continuation time cursor)",
        description="Continuation cursor for the next paged request. Empty when no further data.",
        examples=[""],
    )
    tjjcode_08: str = Field(default="", title="개인투자자코드 (Individual investor code)", description="Individual-investor (개인) code.", examples=["8000"])
    ms_08: int = Field(default=0, title="개인매수 (Individual buy)", description="Individual (개인) running buy total.", examples=[1500000])
    md_08: int = Field(default=0, title="개인매도 (Individual sell)", description="Individual (개인) running sell total.", examples=[1450000])
    rate_08: int = Field(default=0, title="개인증감 (Individual delta)", description="Individual (개인) delta vs. previous snapshot.", examples=[5000, -3000, 0])
    svolume_08: int = Field(default=0, title="개인순매수 (Individual net buy)", description="Individual (개인) net buy = buy − sell.", examples=[50000, -45000, 0])
    jjcode_17: str = Field(default="", title="외국인투자자코드 (Foreign investor code)", description="Foreign-aggregate (외국인) investor code.", examples=["1700"])
    ms_17: int = Field(default=0, title="외국인매수 (Foreign buy)", description="Foreign (외국인) running buy total.", examples=[1200000])
    md_17: int = Field(default=0, title="외국인매도 (Foreign sell)", description="Foreign (외국인) running sell total.", examples=[1150000])
    rate_17: int = Field(default=0, title="외국인증감 (Foreign delta)", description="Foreign (외국인) delta vs. previous snapshot.", examples=[4000, -2500, 0])
    svolume_17: int = Field(default=0, title="외국인순매수 (Foreign net buy)", description="Foreign (외국인) net buy.", examples=[50000, -45000, 0])
    jjcode_18: str = Field(default="", title="기관계투자자코드 (Institutional investor code)", description="Institutional-aggregate (기관계) investor code.", examples=["1800"])
    ms_18: int = Field(default=0, title="기관계매수 (Institutional buy)", description="Institutional (기관계) running buy total.", examples=[800000])
    md_18: int = Field(default=0, title="기관계매도 (Institutional sell)", description="Institutional (기관계) running sell total.", examples=[750000])
    rate_18: int = Field(default=0, title="기관계증감 (Institutional delta)", description="Institutional (기관계) delta vs. previous snapshot.", examples=[3000, -2000, 0])
    svolume_18: int = Field(default=0, title="기관계순매수 (Institutional net buy)", description="Institutional (기관계) net buy.", examples=[50000, -45000, 0])
    jjcode_01: str = Field(default="", title="증권투자자코드 (Securities investor code)", description="Securities-firm (증권) code.", examples=["0100"])
    ms_01: int = Field(default=0, title="증권매수 (Securities buy)", description="Securities (증권) running buy total.", examples=[150000])
    md_01: int = Field(default=0, title="증권매도 (Securities sell)", description="Securities (증권) running sell total.", examples=[140000])
    rate_01: int = Field(default=0, title="증권증감 (Securities delta)", description="Securities (증권) delta.", examples=[1000, -500, 0])
    svolume_01: int = Field(default=0, title="증권순매수 (Securities net buy)", description="Securities (증권) net buy.", examples=[10000, -8000, 0])
    jjcode_03: str = Field(default="", title="투신투자자코드 (Investment-trust investor code)", description="Investment-trust (투신) code.", examples=["0300"])
    ms_03: int = Field(default=0, title="투신매수 (Investment-trust buy)", description="Investment-trust (투신) buy total.", examples=[200000])
    md_03: int = Field(default=0, title="투신매도 (Investment-trust sell)", description="Investment-trust (투신) sell total.", examples=[190000])
    rate_03: int = Field(default=0, title="투신증감 (Investment-trust delta)", description="Investment-trust (투신) delta.", examples=[1500, -800, 0])
    svolume_03: int = Field(default=0, title="투신순매수 (Investment-trust net buy)", description="Investment-trust (투신) net buy.", examples=[10000, -8000, 0])
    jjcode_04: str = Field(default="", title="은행투자자코드 (Bank investor code)", description="Bank (은행) code.", examples=["0400"])
    ms_04: int = Field(default=0, title="은행매수 (Bank buy)", description="Bank (은행) buy total.", examples=[80000])
    md_04: int = Field(default=0, title="은행매도 (Bank sell)", description="Bank (은행) sell total.", examples=[70000])
    rate_04: int = Field(default=0, title="은행증감 (Bank delta)", description="Bank (은행) delta.", examples=[800, -500, 0])
    svolume_04: int = Field(default=0, title="은행순매수 (Bank net buy)", description="Bank (은행) net buy.", examples=[10000, -8000, 0])
    jjcode_02: str = Field(default="", title="보험투자자코드 (Insurance investor code)", description="Insurance (보험) code.", examples=["0200"])
    ms_02: int = Field(default=0, title="보험매수 (Insurance buy)", description="Insurance (보험) buy total.", examples=[120000])
    md_02: int = Field(default=0, title="보험매도 (Insurance sell)", description="Insurance (보험) sell total.", examples=[110000])
    rate_02: int = Field(default=0, title="보험증감 (Insurance delta)", description="Insurance (보험) delta.", examples=[1000, -700, 0])
    svolume_02: int = Field(default=0, title="보험순매수 (Insurance net buy)", description="Insurance (보험) net buy.", examples=[10000, -8000, 0])
    jjcode_05: str = Field(default="", title="종금투자자코드 (Merchant-bank investor code)", description="Merchant-bank (종금) code.", examples=["0500"])
    ms_05: int = Field(default=0, title="종금매수 (Merchant-bank buy)", description="Merchant-bank (종금) buy total.", examples=[10000])
    md_05: int = Field(default=0, title="종금매도 (Merchant-bank sell)", description="Merchant-bank (종금) sell total.", examples=[8000])
    rate_05: int = Field(default=0, title="종금증감 (Merchant-bank delta)", description="Merchant-bank (종금) delta.", examples=[200, -100, 0])
    svolume_05: int = Field(default=0, title="종금순매수 (Merchant-bank net buy)", description="Merchant-bank (종금) net buy.", examples=[2000, -1500, 0])
    jjcode_06: str = Field(default="", title="기금투자자코드 (Pension / fund investor code)", description="Pension / fund (기금) code.", examples=["0600"])
    ms_06: int = Field(default=0, title="기금매수 (Pension / fund buy)", description="Pension / fund (기금) buy total.", examples=[150000])
    md_06: int = Field(default=0, title="기금매도 (Pension / fund sell)", description="Pension / fund (기금) sell total.", examples=[140000])
    rate_06: int = Field(default=0, title="기금증감 (Pension / fund delta)", description="Pension / fund (기금) delta.", examples=[1000, -700, 0])
    svolume_06: int = Field(default=0, title="기금순매수 (Pension / fund net buy)", description="Pension / fund (기금) net buy.", examples=[10000, -8000, 0])
    jjcode_07: str = Field(default="", title="기타투자자코드 (Other investor code)", description="Other (기타) code.", examples=["0700"])
    ms_07: int = Field(default=0, title="기타매수 (Other buy)", description="Other (기타) buy total.", examples=[70000])
    md_07: int = Field(default=0, title="기타매도 (Other sell)", description="Other (기타) sell total.", examples=[65000])
    rate_07: int = Field(default=0, title="기타증감 (Other delta)", description="Other (기타) delta.", examples=[600, -400, 0])
    svolume_07: int = Field(default=0, title="기타순매수 (Other net buy)", description="Other (기타) net buy.", examples=[5000, -4000, 0])
    jjcode_11: str = Field(default="", title="국가투자자코드 (State investor code)", description="State (국가) code.", examples=["1100"])
    ms_11: int = Field(default=0, title="국가매수 (State buy)", description="State (국가) buy total.", examples=[30000])
    md_11: int = Field(default=0, title="국가매도 (State sell)", description="State (국가) sell total.", examples=[25000])
    rate_11: int = Field(default=0, title="국가증감 (State delta)", description="State (국가) delta.", examples=[300, -200, 0])
    svolume_11: int = Field(default=0, title="국가순매수 (State net buy)", description="State (국가) net buy.", examples=[5000, -4000, 0])
    jjcode_00: str = Field(default="", title="사모펀드코드 (Private-fund code)", description="Private-fund (사모펀드) investor code.", examples=["0000"])
    ms_00: int = Field(default=0, title="사모펀드매수 (Private-fund buy)", description="Private-fund (사모펀드) buy total.", examples=[100000])
    md_00: int = Field(default=0, title="사모펀드매도 (Private-fund sell)", description="Private-fund (사모펀드) sell total.", examples=[95000])
    rate_00: int = Field(default=0, title="사모펀드증감 (Private-fund delta)", description="Private-fund (사모펀드) delta.", examples=[700, -500, 0])
    svolume_00: int = Field(default=0, title="사모펀드순매수 (Private-fund net buy)", description="Private-fund (사모펀드) net buy.", examples=[5000, -4000, 0])
    ex_upcode: str = Field(
        default="",
        title="거래소별업종코드 (Exchange-specific sector code)",
        description="Exchange-specific sector code echoed for the queried request.",
        examples=["001"],
    )


class T1602OutBlock1(BaseModel):
    """t1602OutBlock1 — per-time-bucket investor net-buy row.

    Sign convention on ``sv_*`` net-buy columns is NOT declared in the
    available source — [+, -, 0] examples preserve symmetry. Time
    ordering of rows is NOT declared either.
    """

    time: str = Field(
        default="",
        title="시간 (Time bucket)",
        description="Time bucket label, in 'HHMM' or 'HHMMSS' format per LS convention.",
        examples=["0900", "1000"],
    )
    sv_08: int = Field(default=0, title="개인순매수 (Individual net buy)", description="Individual (개인) net-buy column for the bucket.", examples=[50000, -45000, 0])
    sv_17: int = Field(default=0, title="외국인순매수 (Foreign net buy)", description="Foreign (외국인) net-buy column.", examples=[40000, -25000, 0])
    sv_18: int = Field(default=0, title="기관계순매수 (Institutional net buy)", description="Institutional (기관계) net-buy column.", examples=[30000, -20000, 0])
    sv_01: int = Field(default=0, title="증권순매수 (Securities net buy)", description="Securities (증권) net-buy column.", examples=[5000, -4000, 0])
    sv_03: int = Field(default=0, title="투신순매수 (Investment-trust net buy)", description="Investment-trust (투신) net-buy column.", examples=[10000, -8000, 0])
    sv_04: int = Field(default=0, title="은행순매수 (Bank net buy)", description="Bank (은행) net-buy column.", examples=[5000, -3000, 0])
    sv_02: int = Field(default=0, title="보험순매수 (Insurance net buy)", description="Insurance (보험) net-buy column.", examples=[5000, -3000, 0])
    sv_05: int = Field(default=0, title="종금순매수 (Merchant-bank net buy)", description="Merchant-bank (종금) net-buy column.", examples=[1000, -500, 0])
    sv_06: int = Field(default=0, title="기금순매수 (Pension / fund net buy)", description="Pension / fund (기금) net-buy column.", examples=[5000, -4000, 0])
    sv_07: int = Field(default=0, title="기타순매수 (Other net buy)", description="Other (기타) net-buy column.", examples=[3000, -2000, 0])
    sv_11: int = Field(default=0, title="국가순매수 (State net buy)", description="State (국가) net-buy column.", examples=[1000, -800, 0])
    sv_00: int = Field(default=0, title="사모펀드순매수 (Private-fund net buy)", description="Private-fund (사모펀드) net-buy column.", examples=[2000, -1500, 0])


class T1602Response(BaseModel):
    """t1602 response envelope."""

    header: Optional[T1602ResponseHeader] = None
    cont_block: Optional[T1602OutBlock] = Field(
        None,
        title="합계/연속 데이터 (Summary / continuation block)",
        description="Per-investor running totals + continuation cursor.",
    )
    block: List[T1602OutBlock1] = Field(
        default_factory=list,
        title="시간대별 리스트 (Time-bucket list)",
        description="Per-time-bucket investor net-buy rows.",
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
