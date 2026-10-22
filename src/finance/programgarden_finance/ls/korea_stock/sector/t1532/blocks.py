"""Pydantic models for LS Securities OpenAPI t1532 (종목별테마 / per-stock theme list).

t1532 returns the list of investment themes that include a given stock
``shcode``, each with the average percent change of its member stocks.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``avgdiff`` baseline (intraday vs prior close vs session) and
      weighting scheme (equal-weight vs cap-weight) are NOT declared in
      the available source — consume as returned by LS.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1532RequestHeader(BlockRequestHeader):
    """t1532 request header. Inherits the standard LS request header schema."""
    pass


class T1532ResponseHeader(BlockResponseHeader):
    """t1532 response header. Inherits the standard LS response header schema."""
    pass


class T1532InBlock(BaseModel):
    """t1532InBlock — input block for the per-stock theme-list query."""

    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )


class T1532Request(BaseModel):
    """t1532 request envelope."""

    header: T1532RequestHeader = T1532RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1532",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1532InBlock"], T1532InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1532"
    )


class T1532OutBlock(BaseModel):
    """t1532OutBlock — per-theme row that contains the queried stock."""

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


class T1532Response(BaseModel):
    """t1532 response envelope."""

    header: Optional[T1532ResponseHeader] = None
    block: List[T1532OutBlock] = Field(
        default_factory=list,
        title="테마 리스트 (Theme rows)",
        description="List of themes that include the queried stock.",
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
