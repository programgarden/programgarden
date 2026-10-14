"""Pydantic models for LS Securities OpenAPI g3112 (해외주식API시세순위 / overseas stock quote ranking).

g3112 returns overseas stock issues ranked by one quote metric (price change,
volume, trading value, turnover, market capitalisation, 52-week high/low, limit
prices) for one country / exchange-segment combination. The response supports
continuation via ``cts_value``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Every field, its Korean label, its type and every enumerated code comes
      from the official LS OpenAPI guide entry for g3112 ("[해외주식] 시세",
      path ``/overseas-stock/market-data``, ``transactionPerSec`` 1).
    - The guide types every OutBlock / OutBlock1 field as ``String``; the
      models keep them as ``str`` and add no float/int typing. Numeric values
      are consumed as returned by LS.
    - Live observation (one read-only call, 2026-10-15 KST, natcode US,
      exgubun 1, rankgubun 0): HTTP 200, rsp_cd 00000, 20 rows, tr_cont Y,
      cts_value '0000000000000021'. ``volume``, ``amount``, ``shareprc`` and
      ``rec_count`` arrived as JSON integers although the guide says String,
      so both OutBlock models set ``coerce_numbers_to_str``. ``keysymbol`` was
      the LS exchange code + symbol ('82AEHL', '81AMTD'); ``exsymbol`` was an
      exchange label + symbol ('나스닥 AEHL', '뉴욕   AMTD').
    - The guide does not declare currency units or scales for ``amount``
      (거래대금) and ``shareprc`` (시가총액); consume as returned by LS.
    - The guide does not enumerate ``sign`` (전일대비구분). Sibling LS quote
      TRs use '1' upper limit, '2' up, '3' unchanged, '4' lower limit,
      '5' down; consume as returned by LS.
    - ``examples`` come from ``src/finance/example/overseas_stock/run_g3112.py``
      (delaygb='R', natcode='US', exgubun='1', rankgubun='0', cts_value='')
      plus neutral placeholder values.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3112RequestHeader(BlockRequestHeader):
    """g3112 request header. Inherits the standard LS request header schema."""
    pass


class G3112ResponseHeader(BlockResponseHeader):
    """g3112 response header. Inherits the standard LS response header schema."""
    pass


class G3112InBlock(BaseModel):
    """g3112InBlock — input block for the overseas stock quote ranking."""

    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분 (Delay flag)",
        description="Delay flag. Always 'R' per the LS guide.",
        examples=["R"],
    )
    natcode: str = Field(
        ...,
        title="국가구분 (Country code)",
        description="Country code. The LS guide documents 'US' (미국, United States).",
        examples=["US"],
    )
    exgubun: Literal["1", "2", "3", "4"] = Field(
        ...,
        title="거래소구분 (Exchange segment)",
        description=(
            "Exchange segment. '1' = all (전체), '2' = New York (뉴욕), "
            "'3' = NASDAQ (나스닥), '4' = ETF."
        ),
        examples=["1", "2", "3", "4"],
    )
    rankgubun: Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"] = Field(
        ...,
        title="순위구분 (Ranking type)",
        description=(
            "Ranking type. '0' = change rate vs. previous day, gainers (전일대비상승률); "
            "'1' = change rate vs. previous day, losers (전일대비하락률); "
            "'2' = today's volume (당일거래량); '3' = trading value (거래대금); "
            "'4' = turnover (회전율); '5' = market capitalisation (시가총액); "
            "'6' = 52-week high (52주신고가); '7' = 52-week low (52주신저가); "
            "'8' = upper limit (상한가); '9' = lower limit (하한가)."
        ),
        examples=["0", "1", "2", "5"],
    )
    cts_value: str = Field(
        default="",
        title="연속구분 (Continuation token)",
        description=(
            "Continuation token (optional in the LS guide). Empty string for the "
            "first page; echo the value returned in OutBlock for the next page."
        ),
        examples=[""],
    )


class G3112Request(BaseModel):
    """g3112 full request envelope (header + body + setup options)."""

    header: G3112RequestHeader = Field(
        G3112RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="g3112",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["g3112InBlock"], G3112InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'g3112InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="g3112"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options. The LS guide allows 1 transaction per second.",
    )


class G3112OutBlock(BaseModel):
    """g3112OutBlock — input echo + continuation control block."""

    model_config = ConfigDict(coerce_numbers_to_str=True)

    delaygb: str = Field(
        default="",
        title="지연구분 (Delay flag)",
        description="Echoed delay flag.",
        examples=["R"],
    )
    natcode: str = Field(
        default="",
        title="국가구분 (Country code)",
        description="Echoed country code.",
        examples=["US"],
    )
    exgubun: str = Field(
        default="",
        title="거래소구분 (Exchange segment)",
        description="Echoed exchange segment code.",
        examples=["1"],
    )
    rankgubun: str = Field(
        default="",
        title="순위구분 (Ranking type)",
        description="Echoed ranking type code.",
        examples=["0"],
    )
    cts_value: str = Field(
        default="",
        title="연속구분 (Continuation token)",
        description=(
            "Continuation token for the next page request. An empty value "
            "means no further page was offered."
        ),
        examples=["", "0000000000000021"],
    )
    rec_count: str = Field(
        default="",
        title="레코드카운트 (Record count)",
        description="Number of OutBlock1 rows on this page (guide type String; observed as a JSON integer, kept as text).",
        examples=["", "20"],
    )


class G3112OutBlock1(BaseModel):
    """g3112OutBlock1 — one ranked overseas stock row.

    Every field is a string in the LS guide. Units of ``amount`` and
    ``shareprc`` are not declared; consume as returned by LS.
    """

    model_config = ConfigDict(coerce_numbers_to_str=True)

    keysymbol: str = Field(
        default="",
        title="KEY종목코드 (Key symbol code)",
        description="LS key symbol: exchange code + symbol as observed ('82AEHL' NASDAQ, '81AMTD' NYSE/AMEX).",
        examples=["82TSLA"],
    )
    exsymbol: str = Field(
        default="",
        title="거래소종목명 (Exchange issue name)",
        description=(
            "Guide label 거래소종목명. Observed as an LS exchange label plus the symbol "
            "('나스닥 AEHL', '뉴욕   AMTD'); consume as returned by LS."
        ),
        examples=["나스닥 TSLA"],
    )
    symbol: str = Field(
        default="",
        title="종목코드 (Symbol)",
        description="Ticker symbol of the issue.",
        examples=["TSLA"],
    )
    korname: str = Field(
        default="",
        title="한글종목명 (Korean issue name)",
        description="Issue name in Korean.",
        examples=["테슬라"],
    )
    price: str = Field(
        default="",
        title="현재가 (Current price)",
        description="Current price as returned by LS (guide length 15.6).",
        examples=["248.500000"],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Direction code versus the previous close. Not enumerated in the g3112 guide; "
            "sibling LS quote TRs use '1' upper limit, '2' up, '3' unchanged, "
            "'4' lower limit, '5' down. Consume as returned by LS."
        ),
        examples=["2", "5"],
    )
    diff: str = Field(
        default="",
        title="전일대비 (Change vs. previous close)",
        description="Price change versus the previous close as returned by LS. Pair with ``sign`` for direction.",
        examples=["3.250000"],
    )
    rate: str = Field(
        default="",
        title="등락률 (Change rate)",
        description="Percent change versus the previous close as returned by LS (guide length 6.2).",
        examples=["1.33"],
    )
    volume: str = Field(
        default="",
        title="거래량 (Volume)",
        description="Traded volume as returned by LS.",
        examples=["85000000"],
    )
    amount: str = Field(
        default="",
        title="거래대금 (Trading value)",
        description="Trading value. Currency unit and scale are not declared in the LS guide; consume as returned by LS.",
        examples=["21000000"],
    )
    trgt: str = Field(
        default="",
        title="회전율 (Turnover)",
        description="Turnover as returned by LS (guide length 15.6). Baseline not declared in the LS guide.",
        examples=["2.710000"],
    )
    shareprc: str = Field(
        default="",
        title="시가총액 (Market capitalisation)",
        description="Market capitalisation. Currency unit and scale are not declared in the LS guide; consume as returned by LS.",
        examples=["800000000"],
    )
    high52p: str = Field(
        default="",
        title="52주최고가 (52-week high)",
        description="52-week high price as returned by LS.",
        examples=["299.290000"],
    )
    low52p: str = Field(
        default="",
        title="52주최저가 (52-week low)",
        description="52-week low price as returned by LS.",
        examples=["138.800000"],
    )


class G3112Response(BaseModel):
    """g3112 full response envelope."""

    header: Optional[G3112ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[G3112OutBlock] = Field(
        None,
        title="기본 응답 블록 (Echo + continuation block)",
        description="Echo + continuation block (cts_value / rec_count).",
    )
    block1: List[G3112OutBlock1] = Field(
        default_factory=list,
        title="순위 리스트 (Ranked rows)",
        description="Ranked issue rows in the order returned by LS.",
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
