"""Pydantic models for LS Securities OpenAPI t1531 (테마별종목 / theme list).

t1531 returns the list of investment themes matching the requested
``tmname`` (theme name) or ``tmcode`` (theme code), each with the average
percent change of its member stocks. Use t8425 to discover available
``tmname`` / ``tmcode`` values.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Either ``tmname`` or ``tmcode`` may be supplied; the matching
      semantics (exact / prefix / partial) when only ``tmname`` is given
      are NOT declared in the available source.
    - ``avgdiff`` is the average percent change across the theme's
      constituent stocks; the baseline (intraday vs prior close vs
      session) and weighting scheme (equal-weight vs cap-weight) are NOT
      declared in the available source — consume as returned by LS.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1531RequestHeader(BlockRequestHeader):
    """t1531 request header. Inherits the standard LS request header schema."""
    pass


class T1531ResponseHeader(BlockResponseHeader):
    """t1531 response header. Inherits the standard LS response header schema."""
    pass


class T1531InBlock(BaseModel):
    """t1531InBlock — input block for the theme-list query."""

    tmname: str = Field(
        default="",
        title="테마명 (Theme name)",
        description="Theme name. Discoverable via t8425. Either ``tmname`` or ``tmcode`` may be supplied; matching semantics when only the name is given are not declared in the available source.",
        examples=["", "2차전지"],
    )
    tmcode: str = Field(
        default="",
        title="테마코드 (Theme code)",
        description="Theme code. Discoverable via t8425. Either ``tmname`` or ``tmcode`` may be supplied.",
        examples=["", "0001"],
    )


class T1531Request(BaseModel):
    """t1531 request envelope."""

    header: T1531RequestHeader = T1531RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1531",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1531InBlock"], T1531InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1531"
    )


class T1531OutBlock(BaseModel):
    """t1531OutBlock — per-theme row."""

    tmname: str = Field(
        default="",
        title="테마명 (Theme name)",
        description="Theme display name in Korean.",
        examples=["2차전지"],
    )
    avgdiff: float = Field(
        default=0.0,
        title="평균등락율 (Average change percent)",
        description="Average percent change across theme constituents. Baseline and weighting scheme not declared in the available source; consume as returned by LS.",
        examples=[1.25, -0.85, 0.0],
    )
    tmcode: str = Field(
        default="",
        title="테마코드 (Theme code)",
        description="Theme code.",
        examples=["0001"],
    )


class T1531Response(BaseModel):
    """t1531 response envelope."""

    header: Optional[T1531ResponseHeader] = None
    block: List[T1531OutBlock] = Field(
        default_factory=list,
        title="테마 리스트 (Theme rows)",
        description="List of investment themes matching the query.",
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
