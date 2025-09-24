from typing import Dict, Literal, Optional
from programgarden_finance.ls.oauth.generate_token import (
    TokenRequestHeader,
    TokenResponseHeader,
)
from pydantic import BaseModel, PrivateAttr
from requests import Response


class RevokeRequestHeader(TokenRequestHeader):
    """접근토큰 폐기 요청용 Header"""
    pass


class RevokeResponseHeader(TokenResponseHeader):
    """접근토큰 폐기 응답용 Header"""
    pass


class RevokeInBlock(BaseModel):
    """
    revokeInBlock 입력 블록

    Attributes:
        appkey (str): 고객 앱Key
        appsecretkey (str): 고객 앱 비밀Key
        token (str): 접근토큰
        token_type_hint (Literal["access_token", "refresh_token"]): 토큰 유형 hint
    """
    appkey: str
    appsecretkey: str
    token: str
    token_type_hint: Literal["access_token", "refresh_token"]


class RevokeRequest(BaseModel):
    """
    Revoke API 요청

    Attributes:
        header (RevokeRequestHeader)
        body (Dict[Literal["revokeInBlock"], RevokeInBlock]]
    """
    header: RevokeRequestHeader
    body: Dict[Literal["revokeInBlock"], RevokeInBlock]


class RevokeOutBlock(BaseModel):
    """
    revokeOutBlock 응답 블록

    Attributes:
        code (int): 응답코드
        message (str): 응답메시지
    """
    code: int
    message: str


class RevokeResponse(BaseModel):
    """
    Revoke API 전체 응답

    Attributes:
        header (Optional[RevokeResponseHeader])
        block (Optional[RevokeOutBlock])
    """
    header: Optional[RevokeResponseHeader]
    block: Optional[RevokeOutBlock]

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
