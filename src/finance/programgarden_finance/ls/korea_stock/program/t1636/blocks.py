"""Pydantic models for LS Securities OpenAPI t1636 (Korean Stock Program Trading by Symbol).

t1636 returns per-symbol program trading flow on KOSPI / KOSDAQ:
    - Buy and sell amount / quantity.
    - Net-buy amount and quantity.
    - Sort weight (e.g., market-cap weight) for ranking.
    - Net-buy ratio versus market cap (``mkcap_cmpr_val``) — added by LS on 2026-01-08.

The TR supports IDXCTS-based continuation paging via ``cts_idx``.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1636RequestHeader(BlockRequestHeader):
    """t1636 request header. Inherits the standard LS request header schema."""
    pass


class T1636ResponseHeader(BlockResponseHeader):
    """t1636 response header. Carries continuation flags (``tr_cont`` / ``tr_cont_key``)."""
    pass


class T1636InBlock(BaseModel):
    """t1636InBlock — input block for Korean stock program trading by symbol.

    Use ``cts_idx=0`` on the first call. To page through additional results,
    feed back the ``cts_idx`` returned in ``T1636OutBlock``.
    """

    gubun: Literal["0", "1"] = Field(
        ...,
        title="구분 (Market division)",
        description=(
            "Market division. '0' = KOSPI (코스피), '1' = KOSDAQ (코스닥). Required."
        ),
        examples=["0", "1"],
    )
    gubun1: Literal["0", "1"] = Field(
        ...,
        title="금액수량구분 (Amount/quantity selector)",
        description=(
            "Amount-vs-quantity selector for the result set. "
            "'0' = quantity / 수량, '1' = amount / 금액. Required."
        ),
        examples=["0", "1"],
    )
    gubun2: Literal["0", "1", "2", "3", "4"] = Field(
        ...,
        title="정렬기준 (Sort key)",
        description=(
            "Sort key for the result list. "
            "'0' = 시가총액비중 (market-cap weight), '1' = 순매수상위 (top net-buy), "
            "'2' = 순매도상위 (top net-sell), '3' = 매도상위 (top sell), "
            "'4' = 매수상위 (top buy). Required."
        ),
        examples=["0", "1", "2"],
    )
    shcode: str = Field(
        ...,
        title="종목코드 (Stock code)",
        description=(
            "Six-digit Korean stock code (e.g., '005930' for Samsung Electronics, "
            "'000660' for SK Hynix, '035720' for Kakao). Required. Length 6."
        ),
        examples=["005930", "000660", "035720"],
    )
    cts_idx: int = Field(
        default=0,
        title="IDXCTS / cts_idx (Continuation index)",
        description=(
            "IDXCTS continuation index (Number, length 4). Pass 0 (or Space) on the "
            "first request. On subsequent calls reuse the ``cts_idx`` returned in "
            "T1636OutBlock to fetch the next page."
        ),
        examples=[0, 312],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange filter. 'K' = KRX (default), 'N' = NXT, 'U' = unified KRX+NXT. "
            "Other values are treated as KRX per LS spec."
        ),
        examples=["K", "N", "U"],
    )


class T1636Request(BaseModel):
    """t1636 full request envelope (header + body + setup options)."""

    header: T1636RequestHeader = T1636RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1636",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[Literal["t1636InBlock"], T1636InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1636",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class T1636OutBlock(BaseModel):
    """t1636OutBlock — continuation block.

    Returns the IDXCTS index used for paging. ``cts_idx == 0`` indicates no
    further pages.
    """

    cts_idx: int = Field(
        default=0,
        title="IDXCTS / cts_idx (Continuation index)",
        description=(
            "IDXCTS continuation index (Number, length 4). Feed this value back "
            "into the next request's ``T1636InBlock.cts_idx`` to retrieve the "
            "following page. A value of 0 means no further pages are available."
        ),
        examples=[0, 312],
    )


class T1636OutBlock1(BaseModel):
    """t1636OutBlock1 — per-symbol program trading flow row.

    The list ordering follows the requested sort key (``T1636InBlock.gubun2``).

    Note on LS field naming (counter-intuitive):
        - ``svalue`` / ``svolume`` are the **net-buy** amount/quantity.
        - ``stksvalue`` / ``stksvolume`` are the **buy** amount/quantity.
        - ``offervalue`` / ``offervolume`` are the **sell** amount/quantity.
        - Identity: ``svalue == stksvalue - offervalue`` (and same for volume).
    """

    rank: int = Field(
        default=0,
        title="순위 (Rank)",
        description="1-based rank within the result list per the requested sort key. Length 8.",
        examples=[1, 293, 312],
    )
    hname: str = Field(
        default="",
        title="종목명 (Stock display name)",
        description="Korean stock display name. Length 20.",
        examples=["삼성전자", "유진투자증권", "방림"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description="Current price in KRW. Length 8.",
        examples=[3685, 7360, 70000],
    )
    sign: str = Field(
        default="",
        title="대비구분 (Price change sign)",
        description=(
            "Price change sign code (LS standard). '1' = upper limit, '2' = up, "
            "'3' = unchanged, '4' = lower limit, '5' = down."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="대비 (Price change)",
        description="Price change versus previous close in KRW. Length 8.",
        examples=[25, -20, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent price change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '0.68' or '-0.27'); "
            "Pydantic auto-coerces to float."
        ),
        examples=[0.68, -0.27, 0.0],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Trading volume)",
        description="Total trading volume in shares. Length 12.",
        examples=[76162, 322192],
    )
    svalue: int = Field(
        default=0,
        title="순매수금액 (Program net-buy amount)",
        description=(
            "Program net-buy amount in KRW. Identity: ``svalue = stksvalue - offervalue`` "
            "(net-buy = buy - sell). A positive value indicates net buy. Length 12."
        ),
        examples=[200_000_000, -50_000_000, 0],
    )
    offervalue: int = Field(
        default=0,
        title="매도금액 (Program sell amount)",
        description="Program sell amount in KRW. Length 12.",
        examples=[800_000_000, 0],
    )
    stksvalue: int = Field(
        default=0,
        title="매수금액 (Program buy amount)",
        description="Program buy amount in KRW. Length 12.",
        examples=[1_000_000_000, 0],
    )
    svolume: int = Field(
        default=0,
        title="순매수수량 (Program net-buy quantity)",
        description=(
            "Program net-buy quantity in shares. Identity: "
            "``svolume = stksvolume - offervolume`` (net-buy = buy - sell). Length 12."
        ),
        examples=[49935, 2_000, -500],
    )
    offervolume: int = Field(
        default=0,
        title="매도수량 (Program sell quantity)",
        description="Program sell quantity in shares. Length 12.",
        examples=[74893, 8_000],
    )
    stksvolume: int = Field(
        default=0,
        title="매수수량 (Program buy quantity)",
        description="Program buy quantity in shares. Length 12.",
        examples=[124828, 10_000],
    )
    sgta: int = Field(
        default=0,
        title="시가총액 (Market capitalization)",
        description="Market capitalization in KRW. Length 15.",
        examples=[356_952_750_330, 311_431_702_400],
    )
    rate: float = Field(
        default=0.0,
        title="비중 (Sort-key weight)",
        description=(
            "Sort-key weight in % (LS scale 6.2). When ``gubun2 == '0'`` this is "
            "the market-cap weight; for other sort keys it carries the corresponding "
            "ranking metric. LS may serialize this value as a string (e.g., '000.02'); "
            "Pydantic auto-coerces to float."
        ),
        examples=[12.34, 0.02, 5.67],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Stock code)",
        description="Six-digit Korean stock code. Length 6.",
        examples=["001200", "003610", "005930"],
    )
    ex_shcode: str = Field(
        default="",
        title="거래소별단축코드 (Exchange-prefixed short code)",
        description="Exchange-prefixed short code (KRX/NXT-specific identifier). Length 10.",
        examples=["001200", "A001200"],
    )
    mkcap_cmpr_val: float = Field(
        default=0.0,
        title="시총대비순매수비중 (Net-buy ratio vs market cap)",
        description=(
            "Net-buy ratio versus market cap, in % (LS scale 6.2). "
            "Computed as ``svalue / sgta * 100`` (net-buy amount over market cap). "
            "A positive value indicates program net buy exceeds net sell relative to "
            "the symbol's market cap. Added by LS Securities on 2026-01-08."
        ),
        examples=[4.56, -1.20, 0.0],
    )


class T1636Response(BaseModel):
    """t1636 full API response envelope."""

    header: Optional[T1636ResponseHeader] = None
    cont_block: Optional[T1636OutBlock] = Field(
        default=None,
        title="t1636OutBlock (Continuation block)",
        description="IDXCTS continuation key. Present when more pages are available.",
    )
    block: List[T1636OutBlock1] = Field(
        default_factory=list,
        title="t1636OutBlock1 (Per-symbol program trading flow list)",
        description="Result rows ordered by the requested sort key (gubun2).",
    )
    status_code: Optional[int] = Field(default=None, title="HTTP status code")
    rsp_cd: str = ""
    rsp_msg: str = ""
    error_msg: Optional[str] = Field(default=None, title="Error message")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
