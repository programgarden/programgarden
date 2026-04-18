"""Pydantic request/response blocks for JIF (Market Status) real-time TR."""

from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class JIFRealRequestHeader(BlockRealRequestHeader):
    pass


class JIFRealResponseHeader(BlockRealResponseHeader):
    pass


class JIFRealRequestBody(BaseModel):
    tr_cd: str = Field("JIF", description="거래 CD")
    tr_key: str = Field("0", max_length=8, description="JIF는 tr_key='0' 고정")


class JIFRealRequest(BaseModel):
    """JIF 장운영정보 실시간 구독 요청."""

    header: JIFRealRequestHeader = Field(
        JIFRealRequestHeader(
            token="",
            tr_type="3",
        ),
        title="요청 헤더 데이터 블록",
        description="JIF 실시간 구독 요청 헤더 (tr_type=3 구독, 4 해제)",
    )
    body: JIFRealRequestBody = Field(
        JIFRealRequestBody(tr_cd="JIF", tr_key="0"),
        title="입력 데이터 블록",
        description="JIF 입력 블록 (tr_key는 '0' 고정)",
    )


class JIFRealResponseBody(BaseModel):
    """JIF 응답 바디 — jangubun(시장) + jstatus(장운영상태)."""

    jangubun: str = Field(
        ...,
        title="장구분",
        description="시장 구분 코드 (1=KOSPI, 2=KOSDAQ, 9=US, A/B=CN_AM/PM, C/D=HK_AM/PM, E/F=JP_AM/PM, 5=KRX 파생, 6=NXT, 8=KRX 야간)",
    )
    jstatus: str = Field(
        ...,
        title="장운영상태",
        description="장운영상태 코드 (21=Market open, 41=Market closed, 61~68=CB/Sidecar/VI, 등)",
    )


class JIFRealResponse(BaseModel):
    header: Optional[JIFRealResponseHeader]
    body: Optional[JIFRealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드")
    """응답 코드"""
    rsp_msg: str = Field(..., title="응답 메시지")
    """응답 메시지"""
    error_msg: Optional[str] = Field(None, title="오류 메시지")
    """오류 메시지 (있으면)"""
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
