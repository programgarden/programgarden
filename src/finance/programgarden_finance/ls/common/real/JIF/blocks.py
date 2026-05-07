"""Pydantic models for LS Securities OpenAPI JIF (장운영정보 / market-status real-time TR).

JIF is a WebSocket real-time TR that pushes market session-state changes
(open / close / circuit-breaker / sidecar / volatility-interruption etc.)
across all venues that LS exposes through one stream. ``tr_key`` is fixed
to '0' for this TR; all session events for all markets are multiplexed by
``jangubun`` (market division).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``jangubun`` market-division codes ('1'=KOSPI / '2'=KOSDAQ /
      '5'=KRX 파생 / '6'=NXT / '8'=KRX 야간 / '9'=US / 'A'=CN_AM /
      'B'=CN_PM / 'C'=HK_AM / 'D'=HK_PM / 'E'=JP_AM / 'F'=JP_PM) are
      preserved verbatim per the LS Korean source comment in the prior
      blocks.py.
    - ``jstatus`` session-state codes are LS-defined; the available
      source enumerates only a subset ('21' market open, '41' market
      closed, '61'~'68' CB / sidecar / VI) and explicitly notes "등"
      (etc.) — full enum is NOT declared, treat as open-ended.
    - ``tr_key`` is fixed to '0' for JIF per LS source.
"""

from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class JIFRealRequestHeader(BlockRealRequestHeader):
    """JIF real-time request header. Inherits the standard LS real-time header schema."""
    pass


class JIFRealResponseHeader(BlockRealResponseHeader):
    """JIF real-time response header. Inherits the standard LS real-time header schema."""
    pass


class JIFRealRequestBody(BaseModel):
    """JIF real-time request body — TR code + venue key."""

    tr_cd: str = Field(
        default="JIF",
        title="거래코드 (Transaction code)",
        description="Transaction code. Always 'JIF' for this TR.",
        examples=["JIF"],
    )
    tr_key: str = Field(
        default="0",
        max_length=8,
        title="거래키 (Transaction key)",
        description="Transaction key. LS source fixes this to '0' for JIF (single multiplexed stream across all markets).",
        examples=["0"],
    )


class JIFRealRequest(BaseModel):
    """JIF real-time subscription request envelope."""

    header: JIFRealRequestHeader = Field(
        JIFRealRequestHeader(
            token="",
            tr_type="3",
        ),
        title="요청 헤더 (Request header)",
        description="JIF real-time subscription header. tr_type='3' = subscribe, '4' = unsubscribe.",
    )
    body: JIFRealRequestBody = Field(
        JIFRealRequestBody(tr_cd="JIF", tr_key="0"),
        title="입력 블록 (Request body)",
        description="JIF input block. tr_key is fixed to '0' for JIF.",
    )


class JIFRealResponseBody(BaseModel):
    """JIF real-time response body — venue division + session-state event."""

    jangubun: str = Field(
        ...,
        title="장구분 (Market division code)",
        description=(
            "Market division code per LS source: '1'=KOSPI, '2'=KOSDAQ, "
            "'5'=KRX 파생 (KRX derivatives), '6'=NXT, '8'=KRX 야간 (KRX "
            "night session), '9'=US, 'A'=CN_AM, 'B'=CN_PM, 'C'=HK_AM, "
            "'D'=HK_PM, 'E'=JP_AM, 'F'=JP_PM."
        ),
        examples=["1", "2", "9", "6"],
    )
    jstatus: str = Field(
        ...,
        title="장운영상태 (Session-state code)",
        description=(
            "Session-state code per LS source. Available source enumerates "
            "only a subset: '21' = market open, '41' = market closed, "
            "'61'~'68' = circuit-breaker / sidecar / volatility-interruption "
            "events. Source explicitly notes '등' (etc.) — full enum not "
            "declared; treat as open-ended LS-defined codes."
        ),
        examples=["21", "41", "61"],
    )


class JIFRealResponse(BaseModel):
    """JIF real-time response envelope."""

    header: Optional[JIFRealResponseHeader]
    body: Optional[JIFRealResponseBody]

    rsp_cd: str = Field(
        ...,
        title="응답 코드 (Response code)",
        description="LS-defined response code.",
    )
    rsp_msg: str = Field(
        ...,
        title="응답 메시지 (Response message)",
        description="LS-defined response message.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지 (Error message)",
        description="Error message when the request failed; ``None`` on success.",
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
