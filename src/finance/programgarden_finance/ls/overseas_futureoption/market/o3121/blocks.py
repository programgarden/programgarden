"""Pydantic models for LS Securities OpenAPI o3121 (Overseas futures/options master list query).

o3121 returns a list of overseas futures and options instrument master records.
The query supports filtering by market type (futures 'F' or options 'O') and
optional underlying product code.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale, currency unit, multiplier semantics: NOT declared in
      source; documented accordingly.
    - Options-specific fields (XrcPrc, OptTpCode, Moneyness, etc.): enum
      values and semantics documented as declared in source; undeclared
      values noted accordingly.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3121.py``
      (MktGb='O', BscGdsCd='') plus neutral placeholder values.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3121RequestHeader(BlockRequestHeader):
    """o3121 request header. Inherits the standard LS request header schema."""
    pass


class O3121ResponseHeader(BlockResponseHeader):
    """o3121 response header. Inherits the standard LS response header schema."""
    pass


class O3121InBlock(BaseModel):
    """o3121InBlock — input block for the overseas futures/options master list query."""

    MktGb: Optional[Literal["F", "O"]] = Field(
        default=None,
        title="Market type (시장구분)",
        description=(
            "Market type filter. 'F' = futures (선물), 'O' = options (옵션). "
            "None or empty to query all."
        ),
        examples=["O", "F"],
    )
    BscGdsCd: Optional[str] = Field(
        default=None,
        title="Underlying product code (옵션기초상품코드)",
        description=(
            "Underlying product code for options filtering. "
            "When MktGb='O': empty string returns all option product lists; "
            "'O_ES' returns ES product option lists. "
            "Consume as returned by LS."
        ),
        examples=["", "O_ES"],
    )


class O3121Request(BaseModel):
    """o3121 full request envelope (header + body + setup options)."""

    header: O3121RequestHeader = Field(
        O3121RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3121",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3121InBlock"], O3121InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3121InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3121"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3121OutBlock(BaseModel):
    """o3121OutBlock — one overseas futures/options instrument master record.

    Decimal scale, currency unit, multiplier, and tick-value semantics are
    not declared in the source available to this codebase.
    """

    Symbol: str = Field(
        default="",
        title="Symbol code (종목코드)",
        description="LS instrument symbol code for the listed contract.",
        examples=["ESM26", "ESZ25C5800"],
    )
    SymbolNm: str = Field(
        default="",
        title="Symbol name (종목명)",
        description="Human-readable instrument name.",
        examples=["E-MINI S&P500 JUN26"],
    )
    ApplDate: str = Field(
        default="",
        title="Batch receive date YYYYMMDD (종목배치수신일(한국일자))",
        description=(
            "Date on which LS received this instrument's master data in batch, "
            "in Korean time (YYYYMMDD)."
        ),
        examples=["20260101"],
    )
    BscGdsCd: str = Field(
        default="",
        title="Underlying product code (기초상품코드)",
        description=(
            "LS code for the underlying product. "
            "Other LS-defined codes may appear; consume as returned by LS."
        ),
        examples=["ES", "O_ES"],
    )
    BscGdsNm: str = Field(
        default="",
        title="Underlying product name (기초상품명)",
        description="Name of the underlying product.",
        examples=["E-MINI S&P500"],
    )
    ExchCd: str = Field(
        default="",
        title="Exchange code (거래소코드)",
        description=(
            "LS exchange code. "
            "Other LS-defined codes may appear; consume as returned by LS."
        ),
        examples=["CME"],
    )
    ExchNm: str = Field(
        default="",
        title="Exchange name (거래소명)",
        description="Name of the listing exchange.",
        examples=["Chicago Mercantile Exchange"],
    )
    CrncyCd: str = Field(
        default="",
        title="Base currency code (기준통화코드)",
        description="ISO-style currency code for the contract's settlement currency.",
        examples=["USD"],
    )
    NotaCd: str = Field(
        default="",
        title="Numeral system code (진법구분코드)",
        description=(
            "Numeral system classification code for price quotation. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["10"],
    )
    UntPrc: float = Field(
        default=0.0,
        title="Tick price (호가단위가격)",
        description=(
            "Minimum price tick size. Decimal scale not declared in available source."
        ),
        examples=[0.25, 0.5],
    )
    MnChgAmt: float = Field(
        default=0.0,
        title="Minimum price change amount (최소가격변동금액)",
        description=(
            "Monetary value of one minimum price movement. "
            "Multiplier semantics not declared in available source."
        ),
        examples=[12.5, 5.0],
    )
    RgltFctr: float = Field(
        default=0.0,
        title="Price adjustment factor (가격조정계수)",
        description=(
            "Price adjustment factor used by LS. Semantics not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[1.0],
    )
    CtrtPrAmt: float = Field(
        default=0.0,
        title="Per-contract amount (계약당금액)",
        description=(
            "Notional value per contract. Multiplier semantics not declared in "
            "available source."
        ),
        examples=[50.0, 20.0],
    )
    GdsCd: str = Field(
        default="",
        title="Product type code (상품구분코드)",
        description=(
            "LS product-type classification code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["F", "O"],
    )
    LstngYr: str = Field(
        default="",
        title="Contract year (월물(년))",
        description="Year component of the contract month.",
        examples=["2026", "2025"],
    )
    LstngM: str = Field(
        default="",
        title="Contract month (월물(월))",
        description="Month component of the contract month as returned by LS.",
        examples=["06", "12"],
    )
    EcPrc: float = Field(
        default=0.0,
        title="Settlement price (정산가격)",
        description=(
            "Previous settlement price. Decimal scale not declared in available source."
        ),
        examples=[5800.25, 100.0],
    )
    DlStrtTm: str = Field(
        default="",
        title="Trading start time HHMMSS (거래시작시간)",
        description=(
            "Daily trading session start time in HHMMSS format. "
            "Time zone not declared in available source; consume as returned by LS."
        ),
        examples=["170000", "090000"],
    )
    DlEndTm: str = Field(
        default="",
        title="Trading end time HHMMSS (거래종료시간)",
        description=(
            "Daily trading session end time in HHMMSS format. "
            "Time zone not declared in available source; consume as returned by LS."
        ),
        examples=["160000"],
    )
    DlPsblCd: str = Field(
        default="",
        title="Tradeable classification code (거래가능구분코드)",
        description=(
            "Code indicating whether the contract is currently tradeable. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["1", "0"],
    )
    MgnCltCd: str = Field(
        default="",
        title="Margin collection code (증거금징수구분코드)",
        description=(
            "Margin collection type code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["1"],
    )
    OpngMgn: float = Field(
        default=0.0,
        title="Initial margin (개시증거금)",
        description=(
            "Initial margin requirement. "
            "Currency unit not declared in available source."
        ),
        examples=[12000.0, 500.0],
    )
    MntncMgn: float = Field(
        default=0.0,
        title="Maintenance margin (유지증거금)",
        description=(
            "Maintenance margin requirement. "
            "Currency unit not declared in available source."
        ),
        examples=[11000.0, 450.0],
    )
    OpngMgnR: float = Field(
        default=0.0,
        title="Initial margin rate (개시증거금율)",
        description="Initial margin rate. Scale not declared in available source.",
        examples=[0.05, 0.1],
    )
    MntncMgnR: float = Field(
        default=0.0,
        title="Maintenance margin rate (유지증거금율)",
        description="Maintenance margin rate. Scale not declared in available source.",
        examples=[0.04, 0.09],
    )
    DotGb: int = Field(
        default=0,
        title="Effective decimal places (유효소수점자리수)",
        description="Number of effective decimal places LS uses for price display.",
        examples=[2, 4],
    )
    XrcPrc: str = Field(
        default="",
        title="Option strike price (옵션행사가)",
        description=(
            "Strike price for options contracts as a string. "
            "Decimal scale not declared in available source. "
            "Empty for futures contracts."
        ),
        examples=["5800", "5850", ""],
    )
    FdasBasePrc: str = Field(
        default="",
        title="Underlying asset base price (기초자산기준가격)",
        description=(
            "Base price of the underlying asset as a string. "
            "Decimal scale not declared in available source."
        ),
        examples=["5800.25", ""],
    )
    OptTpCode: str = Field(
        default="",
        title="Option call/put type (옵션콜풋구분)",
        description=(
            "Option type classification. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["C", "P", ""],
    )
    RgtXrcPtnCode: str = Field(
        default="",
        title="Exercise style code (권리행사구분코드)",
        description=(
            "Option exercise style code (e.g., American, European). "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["A", "E", ""],
    )
    Moneyness: str = Field(
        default="",
        title="ATM classification (ATM구분)",
        description=(
            "Moneyness classification (ATM/ITM/OTM). "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["A", "I", "O", ""],
    )
    LastSettPtnCode: str = Field(
        default="",
        title="Underlying derivative instrument code (해외파생기초자산종목코드)",
        description=(
            "LS code for the underlying derivative instrument. "
            "Consume as returned by LS."
        ),
        examples=["ES", ""],
    )
    OptMinOrcPrc: str = Field(
        default="",
        title="Minimum option tick price (해외옵션최소호가)",
        description=(
            "Minimum order tick price for options contracts as a string. "
            "Decimal scale not declared in available source."
        ),
        examples=["0.05", ""],
    )
    OptMinBaseOrcPrc: str = Field(
        default="",
        title="Minimum option base tick price (해외옵션최소기준호가)",
        description=(
            "Minimum base order tick price for options contracts as a string. "
            "Decimal scale not declared in available source."
        ),
        examples=["0.1", ""],
    )


class O3121Response(BaseModel):
    """o3121 full response envelope."""

    header: Optional[O3121ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: List[O3121OutBlock] = Field(
        ...,
        title="Instrument master list (출력 블록 리스트)",
        description=(
            "List of overseas futures/options instrument master records. "
            "Time ordering: consume as returned by LS."
        ),
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP status code (HTTP 상태 코드)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="LS response code (응답 코드)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="LS response message (응답 메시지)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="Error message (오류 메시지)",
        description="Error message when an exception or HTTP error occurred. None on success.",
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        """Raw underlying response object (for debugging)."""
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
