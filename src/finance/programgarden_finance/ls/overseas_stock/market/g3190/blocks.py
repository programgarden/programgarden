"""Pydantic models for LS Securities OpenAPI g3190 (Overseas Stock listed-symbol master).

g3190 returns the listed-symbol master for one country / exchange code
combination. Each ``OutBlock1`` row is a single listed issue carrying
the exchange-side identifiers (LS key symbol, ticker, ISIN), Korean /
English issue names, currency, decimal-place convention, industry,
share / capital metadata, lot sizes, base / previous-close, listing /
expiry dates, suspend flag, business date, sell-only flag, stamp-tax
flag, tick-size type, and various market-segment flags
(VCM / CAS / POS / fractional). The response supports continuation via
``cts_value``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, lot-size unit, ``natcode`` country
      codes, ``exgubun`` exchange codes, and the enum codes for
      ``suspend`` / ``sellonly`` / ``stamp`` / ``ticktype`` /
      ``vcmf`` / ``casf`` / ``posf`` / ``point`` are NOT enumerated in
      the source available to this codebase. Where the Korean label is
      generic, the description states "consume as returned by LS".
    - ``examples`` come from ``src/finance/example/overseas_stock/run_g3190.py``
      (delaygb='R', natcode='US', exgubun='2', readcnt=500,
      cts_value='') plus neutral placeholder values.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3190RequestHeader(BlockRequestHeader):
    """g3190 request header. Inherits the standard LS request header schema."""
    pass


class G3190ResponseHeader(BlockResponseHeader):
    """g3190 response header. Inherits the standard LS response header schema."""
    pass


class G3190InBlock(BaseModel):
    """g3190InBlock — input block for the listed-symbol master batch query."""

    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분 (Delay flag)",
        description="Delay flag. Always 'R' (real-time / 실시간) per LS source.",
        examples=["R"],
    )
    natcode: str = Field(
        ...,
        title="국가구분 (Country / nation code)",
        description=(
            "Country / nation code. 'US' = United States. Other LS-defined "
            "codes may apply to non-US markets; consume as returned by LS."
        ),
        examples=["US"],
    )
    exgubun: str = Field(
        ...,
        title="거래소구분 (Exchange-segment code)",
        description=(
            "Exchange-segment code within the country. Code-set not "
            "enumerated in available source; the example script uses '2'."
        ),
        examples=["2"],
    )
    readcnt: int = Field(
        ...,
        title="조회갯수 (Read count)",
        description=(
            "Number of master rows to read per page. Length / max not "
            "declared in available source."
        ),
        examples=[500, 100],
    )
    cts_value: str = Field(
        ...,
        title="연속구분 (Continuation token)",
        description=(
            "Continuation token. Pass empty string for the first page; "
            "echo the value returned in OutBlock for subsequent pages."
        ),
        examples=["", "0"],
    )


class G3190Request(BaseModel):
    """g3190 full request envelope (header + body + setup options)."""

    header: G3190RequestHeader = Field(
        G3190RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="g3190",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["g3190InBlock"], G3190InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'g3190InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=3,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="g3190"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class G3190OutBlock(BaseModel):
    """g3190OutBlock — input echo + continuation control block.

    ``cts_value`` and ``rec_count`` together drive paged retrieval of
    the underlying ``OutBlock1`` rows.
    """

    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분 (Delay flag)",
        description="Echoed delay flag. Always 'R'.",
        examples=["R"],
    )
    natcode: str = Field(
        default="",
        title="국가구분 (Country / nation code)",
        description="Echoed country code (e.g., 'US').",
        examples=["US"],
    )
    exgubun: str = Field(
        default="",
        title="거래소구분 (Exchange-segment code)",
        description="Echoed exchange-segment code.",
        examples=["2"],
    )
    cts_value: str = Field(
        default="",
        title="연속구분 (Continuation token)",
        description=(
            "Continuation token to use on the next page request. An empty "
            "value typically signals no further pages."
        ),
        examples=["", "0"],
    )
    rec_count: int = Field(
        default=0,
        title="조회된 종목 수 (Record count)",
        description="Number of master rows returned in OutBlock1 for this page.",
        examples=[0, 500],
    )


class G3190OutBlock1(BaseModel):
    """g3190OutBlock1 — single listed-issue master row.

    Decimal scale, currency unit, lot-size unit, and the enum codes for
    suspend / sellonly / stamp / ticktype / market-segment flags are
    not declared in the source available to this codebase. The
    ``floatpoint`` field describes the decimal-place convention LS uses
    for the price strings on this row.
    """

    keysymbol: str = Field(
        default="",
        title="KEY종목코드 (Key symbol code)",
        description="LS-internal key symbol code for the issue (e.g., '82TSLA').",
        examples=["82TSLA"],
    )
    natcode: str = Field(
        default="",
        title="국가코드 (Country code)",
        description="Country code for the listing (e.g., 'US').",
        examples=["US"],
    )
    exchcd: str = Field(
        default="",
        title="거래소코드 (Exchange code)",
        description=(
            "Exchange code. '82' = NASDAQ. Other LS-defined codes may "
            "appear; consume as returned by LS."
        ),
        examples=["82"],
    )
    symbol: str = Field(
        default="",
        title="종목코드 (Symbol / ticker)",
        description="Ticker symbol of the issue (e.g., 'TSLA').",
        examples=["TSLA"],
    )
    seccode: str = Field(
        default="",
        title="거래소종목코드 (Exchange-side security code)",
        description="Exchange-side security code as returned by LS.",
        examples=["TSLA"],
    )
    korname: str = Field(
        default="",
        title="한글종목명 (Korean issue name)",
        description="Issue name in Korean.",
        examples=["테슬라"],
    )
    engname: str = Field(
        default="",
        title="영문종목명 (English issue name)",
        description="Issue name in English.",
        examples=["TESLA INC"],
    )
    currency: str = Field(
        default="",
        title="외환코드 (Currency code)",
        description="ISO-style currency code for the price quotation.",
        examples=["USD"],
    )
    isin: str = Field(
        default="",
        title="ISIN (International Securities Identification Number)",
        description="ISIN code for the issue.",
        examples=["US88160R1014"],
    )
    floatpoint: str = Field(
        default="",
        title="FLOATPOINT (Decimal places)",
        description="Number of decimal places LS applies to the price strings.",
        examples=["4", "2"],
    )
    indusury: str = Field(
        default="",
        title="업종코드 (Industry code)",
        description=(
            "Industry classification code as returned by LS. Code-set not "
            "enumerated in available source."
        ),
        examples=["", "AUTO"],
    )
    share: int = Field(
        default=0,
        title="상장주식수 (Listed shares)",
        description="Total listed share count.",
        examples=[0, 3170000000],
    )
    marketcap: int = Field(
        default=0,
        title="자본금 (Capital / market cap)",
        description=(
            "Capital amount as returned by LS. Korean source labels this "
            "field 자본금; currency unit not declared in available source."
        ),
        examples=[0, 800000000000],
    )
    par: float = Field(
        default=0.0,
        title="액면가 (Par value)",
        description="Par value per share. Decimal scale not declared in available source.",
        examples=[0.0, 0.01],
    )
    parcurr: str = Field(
        default="",
        title="액면가외환코드 (Par-value currency code)",
        description="Currency code that the par value is denominated in.",
        examples=["USD"],
    )
    bidlotsize2: int = Field(
        default=0,
        title="매수주문단위2 (Alternate buy lot size)",
        description="Alternate buy-side lot size (shares).",
        examples=[0, 1],
    )
    asklotsize2: int = Field(
        default=0,
        title="매도주문단위2 (Alternate sell lot size)",
        description="Alternate sell-side lot size (shares).",
        examples=[0, 1],
    )
    clos: float = Field(
        default=0.0,
        title="기준가 (Base / reference price)",
        description="Base reference price for the issue.",
        examples=[0.0, 248.00],
    )
    listed_date: str = Field(
        default="",
        title="상장일자 (Listing date)",
        description="Listing date in YYYYMMDD format.",
        examples=["20100629"],
    )
    expire_date: str = Field(
        default="",
        title="만기일자 (Expiry / delisting date)",
        description=(
            "Expiry / delisting date in YYYYMMDD format. Empty for issues "
            "without a defined expiry."
        ),
        examples=["", "99991231"],
    )
    suspend: str = Field(
        default="",
        title="거래정지여부 (Trading-suspend flag)",
        description=(
            "Trading-suspend flag. Code-set not enumerated in available "
            "source; consume as returned by LS."
        ),
        examples=["", "Y", "N"],
    )
    bymd: str = Field(
        default="",
        title="영업일자 (Business date)",
        description="Business date for the master snapshot in YYYYMMDD format.",
        examples=["20250505"],
    )
    sellonly: str = Field(
        default="",
        title="SELLONLY구분 (Sell-only restriction flag)",
        description=(
            "Sell-only restriction flag. Code-set not enumerated in "
            "available source; consume as returned by LS."
        ),
        examples=["", "Y", "N"],
    )
    stamp: str = Field(
        default="",
        title="인지세여부 (Stamp-tax flag)",
        description=(
            "Stamp-tax flag. Code-set not enumerated in available source; "
            "consume as returned by LS."
        ),
        examples=["", "Y", "N"],
    )
    ticktype: str = Field(
        default="",
        title="TICKSIZETYPE (Tick-size classification)",
        description=(
            "Tick-size classification code as returned by LS. Code-set not "
            "enumerated in available source."
        ),
        examples=[""],
    )
    pcls: str = Field(
        default="",
        title="전일종가 (Previous close)",
        description="Previous trading day close price as a string.",
        examples=["248.00"],
    )
    vcmf: str = Field(
        default="",
        title="VCM대상종목 (VCM-eligible flag)",
        description=(
            "VCM (Volatility Control Mechanism) eligibility flag. Code-set "
            "not enumerated in available source; consume as returned by LS."
        ),
        examples=["", "Y", "N"],
    )
    casf: str = Field(
        default="",
        title="CAS대상종목 (CAS-eligible flag)",
        description=(
            "CAS (Closing Auction Session) eligibility flag. Code-set not "
            "enumerated in available source."
        ),
        examples=["", "Y", "N"],
    )
    posf: str = Field(
        default="",
        title="POS대상종목 (POS-eligible flag)",
        description=(
            "POS-eligible flag as returned by LS. Code-set not enumerated "
            "in available source."
        ),
        examples=["", "Y", "N"],
    )
    point: str = Field(
        default="",
        title="소수점매매가능종목 (Fractional-share-trading flag)",
        description=(
            "Flag indicating whether fractional-share trading is "
            "available for the issue. Code-set not enumerated in available "
            "source."
        ),
        examples=["", "Y", "N"],
    )


class G3190Response(BaseModel):
    """g3190 full response envelope."""

    header: Optional[G3190ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[G3190OutBlock] = Field(
        None,
        title="기본 응답 블록 (Echo + continuation block)",
        description="Echo + continuation block (cts_value / rec_count).",
    )
    block1: List[G3190OutBlock1] = Field(
        default_factory=list,
        title="상세 리스트 (Listed-issue rows)",
        description="List of listed-issue master rows. Ordering: consume as returned by LS.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="응답 코드 (LS response code)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="응답 메시지 (LS response message)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지 (Error message)",
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
