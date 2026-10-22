"""Pydantic models for LS Securities OpenAPI CIDBQ01400 (Overseas Futures/Options Order Quantity Query).

CIDBQ01400 returns the orderable quantity for an overseas futures/options instrument
given a symbol, buy/sell direction, order price, and order type.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into English.
      Korean source label is appended in parentheses for AI chatbot Korean↔English mapping.
    - Field length, decimal scale, and complete enum mappings are NOT declared in the
      source available to this codebase. Where ambiguous, descriptions state
      "consume as returned by LS."
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_CIDBQ01400.py``
      where present, plus safe placeholder values ("12345678901" for account numbers).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ01400RequestHeader(BlockRequestHeader):
    """CIDBQ01400 request header. Inherits the standard LS request header schema."""
    pass


class CIDBQ01400ResponseHeader(BlockResponseHeader):
    """CIDBQ01400 response header. Inherits the standard LS response header schema."""
    pass


class CIDBQ01400InBlock1(BaseModel):
    """CIDBQ01400InBlock1 — input block for overseas futures/options orderable quantity query."""

    RecCnt: int = Field(
        default=1,
        title="Record count (레코드갯수)",
        description="Number of records in this request. LS examples use 1.",
        examples=[1],
    )

    QryTpCode: Literal["1", "2", "3"] = Field(
        default="1",
        title="Query type code (조회구분코드)",
        description=(
            "Query type. '1' = new order (신규), '2' = liquidation (청산), "
            "'3' = total available (총가능)."
        ),
        examples=["1", "2", "3"],
    )

    IsuCodeVal: str = Field(
        ...,
        title="Issue code value (종목코드값)",
        description=(
            "Instrument code for the overseas futures/options symbol to query. "
            "From the example script: 'ADM23'. Length not declared in available source."
        ),
        examples=["ADM23", "ESM26", "NQU26"],
    )

    BnsTpCode: Literal["1", "2"] = Field(
        ...,
        title="Buy/sell type code (매매구분코드)",
        description="Trade direction. '1' = sell (매도), '2' = buy (매수).",
        examples=["1", "2"],
    )

    OvrsDrvtOrdPrc: float = Field(
        ...,
        title="Overseas derivative order price (해외파생주문가격)",
        description=(
            "Limit order price. Pass 0 when the order type is market (시장가). "
            "From the example script: 1.0."
        ),
        examples=[1.0, 0.0, 4500.25],
    )

    AbrdFutsOrdPtnCode: Literal["1", "2"] = Field(
        ...,
        title="Overseas futures order type code (해외선물주문유형코드)",
        description="Order type. '1' = market order (시장가), '2' = limit order (지정가).",
        examples=["1", "2"],
    )


class CIDBQ01400Request(BaseModel):
    """CIDBQ01400 full request envelope (header + body + setup options)."""

    header: CIDBQ01400RequestHeader = Field(
        CIDBQ01400RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ01400",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더 데이터 블록)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["CIDBQ01400InBlock1"], CIDBQ01400InBlock1] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'CIDBQ01400InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ01400"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CIDBQ01400OutBlock1(BaseModel):
    """CIDBQ01400OutBlock1 — input echo block.

    LS echoes the request inputs back in OutBlock1. The actual result
    (orderable quantity) is in OutBlock2.
    """

    RecCnt: int = Field(
        default=0,
        title="Record count (레코드갯수)",
        description="Echoed record count from the request.",
        examples=[0, 1],
    )

    QryTpCode: str = Field(
        default="",
        title="Query type code (조회구분코드)",
        description="Echoed query type. '1' = new, '2' = liquidation, '3' = total available.",
        examples=["1", "2", "3"],
    )

    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number associated with the query. Length not declared in available source.",
        examples=["12345678901"],
    )

    IsuCodeVal: str = Field(
        default="",
        title="Issue code value (종목코드값)",
        description="Echoed instrument code.",
        examples=["ADM23", "ESM26"],
    )

    BnsTpCode: str = Field(
        default="",
        title="Buy/sell type code (매매구분코드)",
        description="Echoed trade direction. '1' = sell, '2' = buy.",
        examples=["1", "2"],
    )

    OvrsDrvtOrdPrc: str = Field(
        default="",
        title="Overseas derivative order price (해외파생주문가격)",
        description=(
            "Echoed order price, returned as a string by LS. "
            "Decimal scale not declared in available source."
        ),
        examples=["0", "1.0", "4500.25"],
    )

    AbrdFutsOrdPtnCode: str = Field(
        default="",
        title="Overseas futures order type code (해외선물주문유형코드)",
        description="Echoed order type. '1' = market, '2' = limit.",
        examples=["1", "2"],
    )


class CIDBQ01400OutBlock2(BaseModel):
    """CIDBQ01400OutBlock2 — orderable quantity result block."""

    RecCnt: int = Field(
        default=0,
        title="Record count (레코드갯수)",
        description="Record count for this result block.",
        examples=[0, 1],
    )

    OrdAbleQty: int = Field(
        default=0,
        title="Orderable quantity (주문가능수량)",
        description="Number of contracts that can be ordered given the request parameters.",
        examples=[0, 1, 10],
    )


class CIDBQ01400Response(BaseModel):
    """CIDBQ01400 full response envelope."""

    header: Optional[CIDBQ01400ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CIDBQ01400OutBlock1] = Field(
        None,
        title="First output block — input echo (기본 응답 블록)",
        description="Input echo block (mirrors the InBlock1 inputs).",
    )
    block2: Optional[CIDBQ01400OutBlock2] = Field(
        None,
        title="Second output block — orderable quantity (주문가능수량 블록)",
        description="Orderable quantity result block.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP status code (HTTP 상태 코드)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="LS response code (응답코드)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="LS response message (응답메시지)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="Error message (오류메시지)",
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
