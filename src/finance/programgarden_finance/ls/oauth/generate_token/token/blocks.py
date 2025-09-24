from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr
from requests import Response

from ....models import OAuthRequestHeader, OAuthResponseHeader, SetupOptions


class TokenRequestHeader(OAuthRequestHeader):
    """접근토큰 발급 요청용 Header"""
    pass


class TokenResponseHeader(OAuthResponseHeader):
    """접근토큰 발급 응답용 Header"""
    pass


class TokenInBlock(BaseModel):
    """
    tokenInBlock 입력 블록

    Attributes:
        grant_type (Literal["client_credentials"]): 권한부여 Type, 항상 "client_credentials"로 고정
        appkey (str): 고객 앱Key
        appsecretkey (str): 고객 앱 비밀Key
        scope (Literal["oob"]): scope
    """
    grant_type: Literal["client_credentials"] = "client_credentials"
    """ 권한부여 Type, 항상 "client_credentials"로 고정 """
    appkey: str
    """ 고객 앱Key """
    appsecretkey: str
    """ 고객 앱 비밀Key """
    scope: Literal["oob"] = "oob"
    """ 항상 "oob"로 고정 """


class TokenRequest(BaseModel):
    """
    Token API 요청

    Attributes:
        header (TokenRequestHeader)
        body (TokenInBlock]
    """
    header: TokenRequestHeader = TokenRequestHeader(content_type="application/x-www-form-urlencoded")
    body: TokenInBlock
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="token"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class TokenOutBlock(BaseModel):
    """
    tokenOutBlock 응답 블록

    Attributes:
        access_token (str): 접근토큰
        expires_in (int): 접근토큰 유효기간(초)
        scope (Literal["oob"]): scope
        token_type (Literal["Bearer"]): 토큰 유형
    """
    access_token: str
    expires_in: int
    scope: Literal["oob"]
    token_type: Literal["Bearer"]


class TokenResponse(BaseModel):
    """
    Token API 전체 응답

    Attributes:
        header (Optional[TokenResponseHeader])
        block (Optional[TokenOutBlock])
    """
    header: Optional[TokenResponseHeader]
    block: Optional[TokenOutBlock]

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
