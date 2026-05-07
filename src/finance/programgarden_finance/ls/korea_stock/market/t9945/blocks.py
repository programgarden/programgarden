"""Pydantic models for LS Securities OpenAPI t9945 (주식마스터 / Korean stock master).

t9945 returns the master list of Korean stock issues for a market division
(KOSPI / KOSDAQ), with per-issue Korean name, short code, expanded code, ETF
flag, and NXT venue eligibility. Used to build symbol universes (e.g., the
WatchlistNode source pool) and resolve short-code → display-name lookups.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``etfchk`` and ``filler`` value semantics are NOT declared in the
      source available to this codebase; consume as returned by LS.
    - ``nxt_chk`` enum '1' / '0' is documented in the source.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T9945RequestHeader(BlockRequestHeader):
    """t9945 request header. Inherits the standard LS request header schema."""
    pass


class T9945ResponseHeader(BlockResponseHeader):
    """t9945 response header. Inherits the standard LS response header schema."""
    pass


class T9945InBlock(BaseModel):
    """t9945InBlock — input block for the Korean stock master query."""

    gubun: Literal["1", "2"] = Field(
        ...,
        title="구분 (Market division)",
        description="Market division code. '1' = KOSPI (KSP), '2' = KOSDAQ (KSD) per LS source.",
        examples=["1", "2"],
    )


class T9945Request(BaseModel):
    """t9945 request envelope."""

    header: T9945RequestHeader = T9945RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t9945",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t9945InBlock"], T9945InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t9945"
    )


class T9945OutBlock(BaseModel):
    """t9945OutBlock — per-issue master row."""

    hname: str = Field(
        ...,
        title="종목명 (Korean name)",
        description="Korean issue name as reported by LS.",
        examples=["삼성전자"],
    )
    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    expcode: str = Field(
        ...,
        title="확장코드 (Expanded code)",
        description="Expanded (full) issue code as reported by LS. Format not declared in available source.",
        examples=["KR7005930003"],
    )
    etfchk: str = Field(
        ...,
        title="ETF구분 (ETF flag)",
        description="ETF / non-ETF classification flag. Code values not declared in available source; consume as returned by LS.",
        examples=["0", "1"],
    )
    nxt_chk: str = Field(
        default="",
        title="NXT상장구분 (NXT listing flag)",
        description="NXT venue listing flag. '1' = listed on NXT (NXT 거래소 제공), '0' = not listed on NXT (NXT 거래소 미제공).",
        examples=["0", "1"],
    )
    filler: str = Field(
        default="",
        title="filler (Reserved filler)",
        description="LS-reserved filler field. Semantics not declared in available source.",
        examples=[""],
    )


class T9945Response(BaseModel):
    """t9945 response envelope."""

    header: Optional[T9945ResponseHeader]
    block: List[T9945OutBlock] = Field(
        default_factory=list,
        title="종목 리스트 (Issue list)",
        description="List of stock master rows for the requested market division.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code returned for the request.",
    )
    rsp_cd: str
    rsp_msg: str
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
