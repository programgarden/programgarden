"""Pydantic models for LS Securities OpenAPI t1601 (investor-by-category aggregate / 투자자별종합).

t1601 returns a per-investor-category buy / sell / delta / net-buy
snapshot across six different market segments (KOSPI stock, KOSDAQ
stock, futures, call options, put options, ELW). The response carries
six ``OutBlock`` entries (``block1`` … ``block6``) sharing the same
``T1601InvestorBlock`` schema with 12 investor categories.

Investor-category code mapping (consistent across this TR family —
t1601 / t1602 / t1603 / t1617 / t1664):
    - _08 = 개인 (individual / retail)
    - _17 = 외국인 (foreign aggregate)
    - _18 = 기관계 (institutional aggregate)
    - _01 = 증권 (securities firms)
    - _03 = 투신 (investment trust)
    - _04 = 은행 (bank)
    - _02 = 보험 (insurance)
    - _05 = 종금 (merchant bank)
    - _06 = 기금 (pension / fund)
    - _11 = 국가 (state)
    - _07 = 기타 (other)
    - _00 = 사모펀드 (private fund)

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - The unit of every per-investor column (currency vs. quantity) is
      determined by the corresponding ``gubun*`` mode in ``InBlock``;
      same field name carries different units across modes.
    - Sign convention on ``rate_*`` (증감) and ``svolume_*`` (순매수)
      columns is NOT declared in the available source — [+, -, 0]
      examples preserve symmetry.
    - The investor-code field name on individual (``tjjcode_08``) and
      on every other category (``jjcode_NN``) differs by one character
      ("tjj" vs. "jj") per the LS source — preserved verbatim, NOT
      normalized to a single name.
    - ``gubun3`` is documented in the LS source as "사용안함" (unused);
      preserved as default-empty plain string.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1601.py``
      (``gubun1='1'``, ``gubun2='1'``, ``gubun4='1'`` → quantity mode
      across stock / option / future).
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1601RequestHeader(BlockRequestHeader):
    """t1601 request header. Inherits the standard LS request header schema."""
    pass


class T1601ResponseHeader(BlockResponseHeader):
    """t1601 response header. Inherits the standard LS response header schema."""
    pass


class T1601InBlock(BaseModel):
    """t1601InBlock — input block for the investor-by-category aggregate query."""

    gubun1: Literal["1", "2"] = Field(
        ...,
        title="주식금액수량구분1 (Stock amount / quantity mode)",
        description=(
            "Stock-segment amount / quantity mode for ``block1`` (KOSPI) and "
            "``block2`` (KOSDAQ). '1' = quantity (수량), '2' = amount (금액)."
        ),
        examples=["1", "2"],
    )
    gubun2: Literal["1", "2"] = Field(
        ...,
        title="옵션금액수량구분2 (Option amount / quantity mode)",
        description=(
            "Option-segment amount / quantity mode for ``block4`` (call) and "
            "``block5`` (put) options. '1' = quantity (수량), '2' = amount."
        ),
        examples=["1", "2"],
    )
    gubun3: str = Field(
        default="",
        title="금액단위 (Amount unit / unused)",
        description=(
            "Amount-unit field. Source label states '사용안함' (not used); "
            "consume default empty string."
        ),
        examples=[""],
    )
    gubun4: Literal["1", "2"] = Field(
        ...,
        title="선물금액수량구분4 (Future amount / quantity mode)",
        description=(
            "Future-segment amount / quantity mode for ``block3`` (futures). "
            "'1' = quantity (수량), '2' = amount (금액)."
        ),
        examples=["1", "2"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division code. 'K' = KRX (한국거래소), 'N' = NXT "
            "(넥스트레이드), 'U' = unified (통합)."
        ),
        examples=["K", "N", "U"],
    )


class T1601Request(BaseModel):
    """t1601 request envelope."""

    header: T1601RequestHeader = T1601RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1601",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1601InBlock"], T1601InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1601"
    )


class T1601InvestorBlock(BaseModel):
    """t1601 investor block — shared schema for ``block1`` … ``block6``.

    Holds 12 investor-category entries, each with: investor code +
    buy (ms) + sell (md) + delta (rate) + net-buy (svolume). The unit
    of every numeric column depends on the corresponding ``gubun*``
    mode (quantity vs. amount).

    Sign convention on ``rate_*`` (증감 vs. previous snapshot) and
    ``svolume_*`` (순매수 = buy − sell) is NOT declared in the
    available source — consume as returned by LS.
    """

    tjjcode_08: str = Field(
        default="",
        title="개인투자자코드 (Individual investor code)",
        description="Individual-investor (개인) code. Source label uses 'tjjcode' for individual only; other categories use 'jjcode'.",
        examples=["8000"],
    )
    ms_08: int = Field(
        default=0,
        title="개인매수 (Individual buy)",
        description="Individual (개인) buy column. Unit per ``gubun*`` mode.",
        examples=[1500000],
    )
    md_08: int = Field(
        default=0,
        title="개인매도 (Individual sell)",
        description="Individual (개인) sell column.",
        examples=[1450000],
    )
    rate_08: int = Field(
        default=0,
        title="개인증감 (Individual delta)",
        description="Individual (개인) delta vs. previous snapshot. Sign convention not declared in available source.",
        examples=[5000, -3000, 0],
    )
    svolume_08: int = Field(
        default=0,
        title="개인순매수 (Individual net buy)",
        description="Individual (개인) net buy = buy − sell. Sign convention not declared in available source.",
        examples=[50000, -45000, 0],
    )
    jjcode_17: str = Field(
        default="",
        title="외국인투자자코드 (Foreign investor code)",
        description="Foreign-aggregate investor (외국인) code.",
        examples=["1700"],
    )
    ms_17: int = Field(
        default=0,
        title="외국인매수 (Foreign buy)",
        description="Foreign-aggregate (외국인) buy column.",
        examples=[1200000],
    )
    md_17: int = Field(
        default=0,
        title="외국인매도 (Foreign sell)",
        description="Foreign-aggregate (외국인) sell column.",
        examples=[1150000],
    )
    rate_17: int = Field(
        default=0,
        title="외국인증감 (Foreign delta)",
        description="Foreign-aggregate (외국인) delta vs. previous snapshot.",
        examples=[4000, -2500, 0],
    )
    svolume_17: int = Field(
        default=0,
        title="외국인순매수 (Foreign net buy)",
        description="Foreign-aggregate (외국인) net buy = buy − sell.",
        examples=[50000, -45000, 0],
    )
    jjcode_18: str = Field(
        default="",
        title="기관계투자자코드 (Institutional investor code)",
        description="Institutional-aggregate (기관계) investor code.",
        examples=["1800"],
    )
    ms_18: int = Field(
        default=0,
        title="기관계매수 (Institutional buy)",
        description="Institutional-aggregate (기관계) buy column.",
        examples=[800000],
    )
    md_18: int = Field(
        default=0,
        title="기관계매도 (Institutional sell)",
        description="Institutional-aggregate (기관계) sell column.",
        examples=[750000],
    )
    rate_18: int = Field(
        default=0,
        title="기관계증감 (Institutional delta)",
        description="Institutional-aggregate (기관계) delta vs. previous snapshot.",
        examples=[3000, -2000, 0],
    )
    svolume_18: int = Field(
        default=0,
        title="기관계순매수 (Institutional net buy)",
        description="Institutional-aggregate (기관계) net buy = buy − sell.",
        examples=[50000, -45000, 0],
    )
    jjcode_01: str = Field(
        default="",
        title="증권투자자코드 (Securities investor code)",
        description="Securities-firm (증권) investor code.",
        examples=["0100"],
    )
    ms_01: int = Field(
        default=0,
        title="증권매수 (Securities buy)",
        description="Securities-firm (증권) buy column.",
        examples=[150000],
    )
    md_01: int = Field(
        default=0,
        title="증권매도 (Securities sell)",
        description="Securities-firm (증권) sell column.",
        examples=[140000],
    )
    rate_01: int = Field(
        default=0,
        title="증권증감 (Securities delta)",
        description="Securities-firm (증권) delta vs. previous snapshot.",
        examples=[1000, -500, 0],
    )
    svolume_01: int = Field(
        default=0,
        title="증권순매수 (Securities net buy)",
        description="Securities-firm (증권) net buy = buy − sell.",
        examples=[10000, -8000, 0],
    )
    jjcode_03: str = Field(
        default="",
        title="투신투자자코드 (Investment-trust investor code)",
        description="Investment-trust (투신) investor code.",
        examples=["0300"],
    )
    ms_03: int = Field(
        default=0,
        title="투신매수 (Investment-trust buy)",
        description="Investment-trust (투신) buy column.",
        examples=[200000],
    )
    md_03: int = Field(
        default=0,
        title="투신매도 (Investment-trust sell)",
        description="Investment-trust (투신) sell column.",
        examples=[190000],
    )
    rate_03: int = Field(
        default=0,
        title="투신증감 (Investment-trust delta)",
        description="Investment-trust (투신) delta vs. previous snapshot.",
        examples=[1500, -800, 0],
    )
    svolume_03: int = Field(
        default=0,
        title="투신순매수 (Investment-trust net buy)",
        description="Investment-trust (투신) net buy = buy − sell.",
        examples=[10000, -8000, 0],
    )
    jjcode_04: str = Field(
        default="",
        title="은행투자자코드 (Bank investor code)",
        description="Bank (은행) investor code.",
        examples=["0400"],
    )
    ms_04: int = Field(
        default=0,
        title="은행매수 (Bank buy)",
        description="Bank (은행) buy column.",
        examples=[80000],
    )
    md_04: int = Field(
        default=0,
        title="은행매도 (Bank sell)",
        description="Bank (은행) sell column.",
        examples=[70000],
    )
    rate_04: int = Field(
        default=0,
        title="은행증감 (Bank delta)",
        description="Bank (은행) delta vs. previous snapshot.",
        examples=[800, -500, 0],
    )
    svolume_04: int = Field(
        default=0,
        title="은행순매수 (Bank net buy)",
        description="Bank (은행) net buy = buy − sell.",
        examples=[10000, -8000, 0],
    )
    jjcode_02: str = Field(
        default="",
        title="보험투자자코드 (Insurance investor code)",
        description="Insurance-company (보험) investor code.",
        examples=["0200"],
    )
    ms_02: int = Field(
        default=0,
        title="보험매수 (Insurance buy)",
        description="Insurance (보험) buy column.",
        examples=[120000],
    )
    md_02: int = Field(
        default=0,
        title="보험매도 (Insurance sell)",
        description="Insurance (보험) sell column.",
        examples=[110000],
    )
    rate_02: int = Field(
        default=0,
        title="보험증감 (Insurance delta)",
        description="Insurance (보험) delta vs. previous snapshot.",
        examples=[1000, -700, 0],
    )
    svolume_02: int = Field(
        default=0,
        title="보험순매수 (Insurance net buy)",
        description="Insurance (보험) net buy = buy − sell.",
        examples=[10000, -8000, 0],
    )
    jjcode_05: str = Field(
        default="",
        title="종금투자자코드 (Merchant-bank investor code)",
        description="Merchant-bank (종금) investor code.",
        examples=["0500"],
    )
    ms_05: int = Field(
        default=0,
        title="종금매수 (Merchant-bank buy)",
        description="Merchant-bank (종금) buy column.",
        examples=[10000],
    )
    md_05: int = Field(
        default=0,
        title="종금매도 (Merchant-bank sell)",
        description="Merchant-bank (종금) sell column.",
        examples=[8000],
    )
    rate_05: int = Field(
        default=0,
        title="종금증감 (Merchant-bank delta)",
        description="Merchant-bank (종금) delta vs. previous snapshot.",
        examples=[200, -100, 0],
    )
    svolume_05: int = Field(
        default=0,
        title="종금순매수 (Merchant-bank net buy)",
        description="Merchant-bank (종금) net buy = buy − sell.",
        examples=[2000, -1500, 0],
    )
    jjcode_06: str = Field(
        default="",
        title="기금투자자코드 (Pension / fund investor code)",
        description="Pension / fund (기금) investor code.",
        examples=["0600"],
    )
    ms_06: int = Field(
        default=0,
        title="기금매수 (Pension / fund buy)",
        description="Pension / fund (기금) buy column.",
        examples=[150000],
    )
    md_06: int = Field(
        default=0,
        title="기금매도 (Pension / fund sell)",
        description="Pension / fund (기금) sell column.",
        examples=[140000],
    )
    rate_06: int = Field(
        default=0,
        title="기금증감 (Pension / fund delta)",
        description="Pension / fund (기금) delta vs. previous snapshot.",
        examples=[1000, -700, 0],
    )
    svolume_06: int = Field(
        default=0,
        title="기금순매수 (Pension / fund net buy)",
        description="Pension / fund (기금) net buy = buy − sell.",
        examples=[10000, -8000, 0],
    )
    jjcode_11: str = Field(
        default="",
        title="국가투자코드 (State investor code)",
        description="State (국가) investor code per the LS source label.",
        examples=["1100"],
    )
    ms_11: int = Field(
        default=0,
        title="국가매수 (State buy)",
        description="State (국가) buy column.",
        examples=[30000],
    )
    md_11: int = Field(
        default=0,
        title="국가매도 (State sell)",
        description="State (국가) sell column.",
        examples=[25000],
    )
    rate_11: int = Field(
        default=0,
        title="국가증감 (State delta)",
        description="State (국가) delta vs. previous snapshot.",
        examples=[300, -200, 0],
    )
    svolume_11: int = Field(
        default=0,
        title="국가순매수 (State net buy)",
        description="State (국가) net buy = buy − sell.",
        examples=[5000, -4000, 0],
    )
    jjcode_07: str = Field(
        default="",
        title="기타투자자코드 (Other investor code)",
        description="Other-investor (기타) code.",
        examples=["0700"],
    )
    ms_07: int = Field(
        default=0,
        title="기타매수 (Other buy)",
        description="Other (기타) buy column.",
        examples=[70000],
    )
    md_07: int = Field(
        default=0,
        title="기타매도 (Other sell)",
        description="Other (기타) sell column.",
        examples=[65000],
    )
    rate_07: int = Field(
        default=0,
        title="기타증감 (Other delta)",
        description="Other (기타) delta vs. previous snapshot.",
        examples=[600, -400, 0],
    )
    svolume_07: int = Field(
        default=0,
        title="기타순매수 (Other net buy)",
        description="Other (기타) net buy = buy − sell.",
        examples=[5000, -4000, 0],
    )
    jjcode_00: str = Field(
        default="",
        title="사모펀드투자자코드 (Private-fund investor code)",
        description="Private-fund (사모펀드) investor code.",
        examples=["0000"],
    )
    ms_00: int = Field(
        default=0,
        title="사모펀드매수 (Private-fund buy)",
        description="Private-fund (사모펀드) buy column.",
        examples=[100000],
    )
    md_00: int = Field(
        default=0,
        title="사모펀드매도 (Private-fund sell)",
        description="Private-fund (사모펀드) sell column.",
        examples=[95000],
    )
    rate_00: int = Field(
        default=0,
        title="사모펀드증감 (Private-fund delta)",
        description="Private-fund (사모펀드) delta vs. previous snapshot.",
        examples=[700, -500, 0],
    )
    svolume_00: int = Field(
        default=0,
        title="사모펀드순매수 (Private-fund net buy)",
        description="Private-fund (사모펀드) net buy = buy − sell.",
        examples=[5000, -4000, 0],
    )


class T1601Response(BaseModel):
    """t1601 response envelope.

    Six per-segment ``T1601InvestorBlock`` entries:
        - ``block1`` = KOSPI stock
        - ``block2`` = KOSDAQ stock
        - ``block3`` = futures
        - ``block4`` = call options
        - ``block5`` = put options
        - ``block6`` = ELW
    """

    header: Optional[T1601ResponseHeader] = None
    block1: Optional[T1601InvestorBlock] = Field(
        None,
        title="코스피(주식) (KOSPI stock)",
        description="KOSPI-stock investor-by-category aggregate.",
    )
    block2: Optional[T1601InvestorBlock] = Field(
        None,
        title="코스닥(주식) (KOSDAQ stock)",
        description="KOSDAQ-stock investor-by-category aggregate.",
    )
    block3: Optional[T1601InvestorBlock] = Field(
        None,
        title="선물 (Futures)",
        description="Futures investor-by-category aggregate.",
    )
    block4: Optional[T1601InvestorBlock] = Field(
        None,
        title="콜옵션 (Call options)",
        description="Call-option investor-by-category aggregate.",
    )
    block5: Optional[T1601InvestorBlock] = Field(
        None,
        title="풋옵션 (Put options)",
        description="Put-option investor-by-category aggregate.",
    )
    block6: Optional[T1601InvestorBlock] = Field(
        None,
        title="ELW",
        description="ELW (Equity-Linked Warrant) investor-by-category aggregate.",
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
