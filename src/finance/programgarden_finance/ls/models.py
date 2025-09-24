"""
LS증권 API를 사용하기 위한 데이터 타입입니다.
이 파일은 LS증권 API의 인증 요청 및 응답 헤더, 블록 요청 및 응답 헤더를 정의합니다.
"""

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class SetupOptions(BaseModel):
    """
    코드 실행 전 설정(setup)을 위한 옵션
    """
    rate_limit_count: int = Field(
        1,
        title="Rate Limit 횟수",
        description="기간(rate_limit_seconds) 내 허용되는 최대 요청 수"
    )
    """기간(rate_limit_seconds) 내 허용되는 최대 요청 수"""
    rate_limit_seconds: int = Field(
        1,
        title="Rate Limit 기간(초)",
        description="rate_limit_count가 적용되는 기간(초)"
    )
    """rate_limit_count가 적용되는 기간(초)"""
    on_rate_limit: Literal["stop", "wait"] = Field(
        "stop",
        title="Rate Limit 동작",
        description='제한 초과 시 동작: "stop"은 중단(에러), "wait"은 대기 후 재시도'
    )
    """제한 초과 시 동작: "stop"은 중단(에러), "wait"은 대기 후 재시도"""
    rate_limit_key: str = Field(
        None,
        title="Rate Limit 키",
        description="여러 인스턴스 간에 rate limit 상태를 공유하기 위한 키 (기본값: None)"
    )
    """여러 인스턴스 간에 rate limit 상태를 공유하기 위한 키 (기본값: None)"""


class OAuthRequestHeader(BaseModel):
    """
    인증 요청 헤더 데이터 블록

    """
    content_type: str = Field(
        ...,
        alias="Content-Type",
        title="요청 콘텐츠 타입",
        description='LS증권 제공 API를 호출하기 위한 Request Body 데이터 포맷으로 "application/x-www-form-urlencoded 설정"'
    )

    model_config = ConfigDict(
        populate_by_name=True
    )


class OAuthResponseHeader(BaseModel):
    """
    응답 헤더 데이터 블록

    Attributes:
        content_type (str): LS증권 제공 API를 호출하기 위한 Request Body 데이터 포맷으로 "application/json; charset=utf-8 설정"
    """
    content_type: str = Field(
        ...,
        alias="Content-Type",
        title="응답 콘텐츠 타입",
        description="컨텐츠타입 (실제 HTTP 헤더: Content-Type)"
    )

    model_config = ConfigDict(
        populate_by_name=True
    )


class BlockRequestHeader(BaseModel):
    """
    요청 헤더 데이터 블록

    Attributes:
        content_type (str): LS증권 제공 API를 호출하기 위한 Request Body 데이터 포맷으로 "application/json; charset=utf-8 설정"
        authorization (str): 발급한 AccessToken, 예: "Bearer {access_token}"
        tr_cd        (str): 거래CD, LS증권거래코드, 예: COSAQ00102
        tr_cont      (Literal["Y", "N"]): 연속거래여부, Y: 연속거래, N: 단건거래
        tr_cont_key  (str): 연속거래Key, 연속일경우그전에내려온연속키값올림
        mac_address  (str): MAC 주소 (선택적, 필요시 사용)
    """
    content_type: str = Field(
        ..., alias="Content-Type",
        title="요청 콘텐츠 타입",
        description='LS증권 제공 API를 호출하기 위한 Request Body 데이터 포맷으로 "application/json; charset=utf-8 설정"'
    )
    """컨텐츠타입 (실제 HTTP 헤더 “Content-Type”)"""
    authorization: str = Field(
        ...,
        title="인증 헤더",
        description='발급한 AccessToken, 예: "Bearer {access_token}"'
    )
    """인증 헤더이며 'Bearer {access_token}' 형식으로 설정"""

    tr_cd: str = Field(
        ...,
        title="거래CD",
        description="LS증권거래코드, 예: COSAQ00102"
    )
    """거래CD"""

    tr_cont: Literal["Y", "N"] = Field(
        ...,
        title="연속거래여부",
        description="Y: 연속거래, N: 단건거래"
    )
    """연속거래여부 (Y/N)"""

    tr_cont_key: str = Field(
        ...,
        title="연속거래Key",
        description="연속일 경우 그전에 내려온 연속 키값 올림"
    )
    """연속거래Key"""

    mac_address: str = Field(
        ...,
        title="MAC 주소",
        description="선택적, 필요시 사용"
    )
    """MAC 주소 (선택적, 필요시 사용)"""

    model_config = ConfigDict(
        populate_by_name=True
    )


class BlockResponseHeader(BaseModel):
    """
    응답 헤더 데이터 블록

    Attributes:
        content_type (str): LS증권 제공 API를 호출하기 위한 Request Body 데이터 포맷으로 "application/json; charset=utf-8 설정"
        tr_cd        (str): 거래CD, LS증권거래코드, 예: COSAQ
        tr_cont      (str): 연속거래여부, Y: 연속거래, N: 단건거래
        tr_cont_key  (str): 연속거래Key, 연속일경우그전에내려온연속키값올림
    """
    content_type: str = Field(
        ...,
        alias="Content-Type",
        title="응답 콘텐츠 타입",
        description="컨텐츠타입 (실제 HTTP 헤더: Content-Type)"
    )
    """컨텐츠타입 (실제 HTTP 헤더 "Content-Type")"""
    tr_cd: str = Field(
        ...,
        title="거래CD",
        description="LS증권거래코드"
    )
    """거래CD"""
    tr_cont: str = Field(
        ...,
        title="연속거래여부",
        description="Y: 연속거래, N: 단건거래"
    )
    """연속거래여부 (Y/N)"""
    tr_cont_key: str = Field(
        ...,
        title="연속거래Key",
        description="연속일 경우 그전에 내려온 연속 키값 올림"
    )
    """연속거래Key"""

    model_config = ConfigDict(
        populate_by_name=True
    )


class BlockRealRequestHeader(BaseModel):
    token: str = Field(..., description="Access Token")
    """접근 토큰"""
    tr_type: str = Field(..., description="1:계좌등록,2:계좌해제,3:실시간시세등록,4:실시간시세해제")
    """트랜잭션 타입 (1:계좌등록,2:계좌해제,3:실시간시세등록,4:실시간시세해제)"""


class BlockRealResponseHeader(BaseModel):
    tr_cd: str = Field(..., description="거래 CD")
    """거래 CD"""
    tr_key: Optional[str] = Field(None, description="응답 종목 코드 + padding(공백12자리)")
    """응답 종목 코드 + padding(공백12자리)"""
    tr_type: Optional[str] = Field(None, description="1:계좌등록,2:계좌해제,3:실시간시세등록,4:실시간시세해제")
    """트랜잭션 타입 (1:계좌등록,2:계좌해제,3:실시간시세등록,4:실시간시세해제)"""
    rsp_cd: Optional[str] = Field(None, description="응답 코드")
    """응답 코드"""
    rsp_msg: Optional[str] = Field(None, description="응답 메시지")
    """응답 메시지"""
