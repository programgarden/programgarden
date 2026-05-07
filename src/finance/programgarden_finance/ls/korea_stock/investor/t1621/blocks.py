"""Pydantic models for LS Securities OpenAPI t1621 (sector N-minute investor flow / 업종별분별투자자매매동향).

t1621 returns a per-N-minute investor net-buy time series for a single
sector / index, expanded to all 12 investor categories with both
quantity and value columns. The response carries:

    - ``OutBlock`` (``cont_block``) — investor-code echoes for all 12
      categories + benchmark index code / name + exchange-specific
      sector code echo.
    - ``OutBlock1`` (``block``) — list of per-N-minute rows: date +
      time + datetime + 12 × (msvol, msamt) per investor + benchmark
      index close / volume / cumulative volume / value.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - Sign convention on per-investor ``msvol`` (순매수거래량) and
      ``msamt`` (순매수거래대금) columns is NOT declared in the
      available source — [+, -, 0] examples preserve symmetry.
    - Decimal scale and currency unit of value / index columns are NOT
      declared in the available source; consume as returned by LS.
    - Time ordering of ``OutBlock1`` rows is NOT declared.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1621.py``
      (``upcode='001'`` = KOSPI all sectors, ``bgubun='0'`` = 당일).
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1621RequestHeader(BlockRequestHeader):
    """t1621 request header. Inherits the standard LS request header schema."""
    pass


class T1621ResponseHeader(BlockResponseHeader):
    """t1621 response header. Inherits the standard LS response header schema."""
    pass


class T1621InBlock(BaseModel):
    """t1621InBlock — input block for the sector N-minute investor-flow query."""

    upcode: str = Field(
        ...,
        title="업종코드 (Sector code)",
        description="Sector / index code (e.g., '001' for KOSPI all-sectors).",
        examples=["001"],
    )
    nmin: int = Field(
        default=0,
        title="N분 (N-minute interval)",
        description="N-minute aggregation interval. 0 uses the LS default per source.",
        examples=[0, 1, 5, 30],
    )
    cnt: int = Field(
        default=20,
        title="조회건수 (Requested row count)",
        description="Number of rows to request per page.",
        examples=[20, 100],
    )
    bgubun: Literal["0", "1"] = Field(
        ...,
        title="전일분 (Today / previous-day mode)",
        description="Time scope. '0' = today (당일), '1' = previous day (전일).",
        examples=["0", "1"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division code. 'K' = KRX, 'N' = NXT, 'U' = unified.",
        examples=["K", "N", "U"],
    )


class T1621Request(BaseModel):
    """t1621 request envelope."""

    header: T1621RequestHeader = T1621RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1621",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1621InBlock"], T1621InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1621"
    )


class T1621OutBlock(BaseModel):
    """t1621OutBlock — investor-code echo + benchmark index identifier block.

    Note: per the LS source, the investor-code field per category uses
    a 3-letter abbreviation prefix (ind / for / sys / sto / inv / ban /
    ins / fin / mon / etc / nat / pef) — not the t1601 / t1602
    ``jjcode_NN`` style. Preserved verbatim.
    """

    indcode: str = Field(default="", title="개인투자자코드 (Individual investor code)", description="Individual-investor (개인) code.", examples=["8000"])
    forcode: str = Field(default="", title="외국인투자자코드 (Foreign investor code)", description="Foreign-aggregate (외국인) investor code.", examples=["1700"])
    syscode: str = Field(default="", title="기관계투자자코드 (Institutional investor code)", description="Institutional-aggregate (기관계) investor code.", examples=["1800"])
    stocode: str = Field(default="", title="증권투자자코드 (Securities investor code)", description="Securities-firm (증권) investor code.", examples=["0100"])
    invcode: str = Field(default="", title="투신투자자코드 (Investment-trust investor code)", description="Investment-trust (투신) investor code.", examples=["0300"])
    bancode: str = Field(default="", title="은행투자자코드 (Bank investor code)", description="Bank (은행) investor code.", examples=["0400"])
    inscode: str = Field(default="", title="보험투자자코드 (Insurance investor code)", description="Insurance (보험) investor code.", examples=["0200"])
    fincode: str = Field(default="", title="종금투자자코드 (Merchant-bank investor code)", description="Merchant-bank (종금) investor code.", examples=["0500"])
    moncode: str = Field(default="", title="기금투자자코드 (Pension / fund investor code)", description="Pension / fund (기금) investor code.", examples=["0600"])
    etccode: str = Field(default="", title="기타투자자코드 (Other investor code)", description="Other (기타) investor code.", examples=["0700"])
    natcode: str = Field(default="", title="국가투자자코드 (State investor code)", description="State (국가) investor code.", examples=["1100"])
    pefcode: str = Field(default="", title="사모펀드투자자코드 (Private-fund investor code)", description="Private-fund (사모펀드) investor code.", examples=["0000"])
    jisucd: str = Field(
        default="",
        title="기준지수코드 (Benchmark index code)",
        description="Benchmark index code referenced by the per-N-minute rows.",
        examples=["001"],
    )
    jisunm: str = Field(
        default="",
        title="기준지수명 (Benchmark index name)",
        description="Benchmark index name referenced by the per-N-minute rows.",
        examples=["KOSPI"],
    )
    ex_upcode: str = Field(
        default="",
        title="거래소별업종코드 (Exchange-specific sector code)",
        description="Exchange-specific sector code echoed for the queried request.",
        examples=["001"],
    )


class T1621OutBlock1(BaseModel):
    """t1621OutBlock1 — per-N-minute investor-flow row + benchmark index snapshot.

    Sign convention on per-investor ``msvol`` / ``msamt`` (순매수) NOT
    declared in available source — [+, -, 0] examples preserve symmetry.
    """

    date: str = Field(default="", title="일자 (Date)", description="Bucket date in 'YYYYMMDD' format.", examples=["20260228"])
    time: str = Field(default="", title="시간 (Time)", description="Bucket time in 'HHMM' format.", examples=["0900"])
    datetime: str = Field(default="", title="일자시간 (Datetime)", description="Concatenated date + time string per LS convention.", examples=["202602280900"])
    indmsvol: int = Field(default=0, title="개인순매수거래량 (Individual net-buy quantity)", description="Individual (개인) net-buy quantity for the bucket.", examples=[50000, -45000, 0])
    indmsamt: int = Field(default=0, title="개인순매수거래대금 (Individual net-buy value)", description="Individual (개인) net-buy value. Currency unit not declared.", examples=[3925000000, -3531000000, 0])
    formsvol: int = Field(default=0, title="외국인순매수거래량 (Foreign net-buy quantity)", description="Foreign (외국인) net-buy quantity.", examples=[40000, -25000, 0])
    formsamt: int = Field(default=0, title="외국인순매수거래대금 (Foreign net-buy value)", description="Foreign (외국인) net-buy value.", examples=[3140000000, -1962500000, 0])
    sysmsvol: int = Field(default=0, title="기관계순매수거래량 (Institutional net-buy quantity)", description="Institutional (기관계) net-buy quantity.", examples=[30000, -20000, 0])
    sysmsamt: int = Field(default=0, title="기관계순매수거래대금 (Institutional net-buy value)", description="Institutional (기관계) net-buy value.", examples=[2355000000, -1570000000, 0])
    stomsvol: int = Field(default=0, title="증권순매수거래량 (Securities net-buy quantity)", description="Securities (증권) net-buy quantity.", examples=[5000, -4000, 0])
    stomsamt: int = Field(default=0, title="증권순매수거래대금 (Securities net-buy value)", description="Securities (증권) net-buy value.", examples=[392500000, -314000000, 0])
    invmsvol: int = Field(default=0, title="투신순매수거래량 (Investment-trust net-buy quantity)", description="Investment-trust (투신) net-buy quantity.", examples=[10000, -8000, 0])
    invmsamt: int = Field(default=0, title="투신순매수거래대금 (Investment-trust net-buy value)", description="Investment-trust (투신) net-buy value.", examples=[785000000, -628000000, 0])
    banmsvol: int = Field(default=0, title="은행순매수거래량 (Bank net-buy quantity)", description="Bank (은행) net-buy quantity.", examples=[5000, -3000, 0])
    banmsamt: int = Field(default=0, title="은행순매수거래대금 (Bank net-buy value)", description="Bank (은행) net-buy value.", examples=[392500000, -235500000, 0])
    insmsvol: int = Field(default=0, title="보험순매수거래량 (Insurance net-buy quantity)", description="Insurance (보험) net-buy quantity.", examples=[5000, -3000, 0])
    insmsamt: int = Field(default=0, title="보험순매수거래대금 (Insurance net-buy value)", description="Insurance (보험) net-buy value.", examples=[392500000, -235500000, 0])
    finmsvol: int = Field(default=0, title="종금순매수거래량 (Merchant-bank net-buy quantity)", description="Merchant-bank (종금) net-buy quantity.", examples=[1000, -500, 0])
    finmsamt: int = Field(default=0, title="종금순매수거래대금 (Merchant-bank net-buy value)", description="Merchant-bank (종금) net-buy value.", examples=[78500000, -39250000, 0])
    monmsvol: int = Field(default=0, title="기금순매수거래량 (Pension / fund net-buy quantity)", description="Pension / fund (기금) net-buy quantity.", examples=[5000, -4000, 0])
    monmsamt: int = Field(default=0, title="기금순매수거래대금 (Pension / fund net-buy value)", description="Pension / fund (기금) net-buy value.", examples=[392500000, -314000000, 0])
    etcmsvol: int = Field(default=0, title="기타순매수거래량 (Other net-buy quantity)", description="Other (기타) net-buy quantity.", examples=[3000, -2000, 0])
    etcmsamt: int = Field(default=0, title="기타순매수거래대금 (Other net-buy value)", description="Other (기타) net-buy value.", examples=[235500000, -157000000, 0])
    natmsvol: int = Field(default=0, title="국가순매수거래량 (State net-buy quantity)", description="State (국가) net-buy quantity.", examples=[1000, -800, 0])
    natmsamt: int = Field(default=0, title="국가순매수거래대금 (State net-buy value)", description="State (국가) net-buy value.", examples=[78500000, -62800000, 0])
    pefmsvol: int = Field(default=0, title="사모펀드순매수거래량 (Private-fund net-buy quantity)", description="Private-fund (사모펀드) net-buy quantity.", examples=[2000, -1500, 0])
    pefmsamt: int = Field(default=0, title="사모펀드순매수거래대금 (Private-fund net-buy value)", description="Private-fund (사모펀드) net-buy value.", examples=[157000000, -117750000, 0])
    upclose: float = Field(default=0.0, title="기준지수 (Benchmark index close)", description="Benchmark index closing value at the bucket. Decimal scale not declared in available source.", examples=[2750.45])
    upcvolume: int = Field(default=0, title="기준체결거래량 (Benchmark execution volume)", description="Benchmark execution volume at the bucket.", examples=[15000000])
    upvolume: int = Field(default=0, title="기준누적거래량 (Benchmark cumulative volume)", description="Benchmark cumulative volume up to the bucket.", examples=[150000000])
    upvalue: int = Field(default=0, title="기준거래대금 (Benchmark trade value)", description="Benchmark cumulative trade value up to the bucket. Currency unit not declared.", examples=[12000000000000])


class T1621Response(BaseModel):
    """t1621 response envelope."""

    header: Optional[T1621ResponseHeader] = None
    cont_block: Optional[T1621OutBlock] = Field(
        None,
        title="요약 데이터 (Summary block)",
        description="Investor-code echoes + benchmark index identifier.",
    )
    block: List[T1621OutBlock1] = Field(
        default_factory=list,
        title="시간별 리스트 (Per-N-minute list)",
        description="Per-N-minute investor-flow rows + benchmark index snapshot.",
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
