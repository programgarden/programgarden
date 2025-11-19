"""LS Securities API data models for authentication and block messaging.

영문/한글로 인증 및 블록 메시지 헤더 스키마를 정의합니다."""

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from programgarden_finance.ls.token_manager import TokenManager


class SetupOptions(BaseModel):
    """Execution pre-setup options controlling rate limiting behaviour.

    코드 실행 전 rate limit 제어를 위한 사전 설정 옵션입니다."""
    rate_limit_count: int = Field(
        1,
        title="Rate Limit 횟수",
        description="기간(rate_limit_seconds) 내 허용되는 최대 요청 수"
    )
    """Maximum number of requests within ``rate_limit_seconds``.

    ``rate_limit_seconds`` 안에서 허용되는 기간내 최대 요청 수입니다."""
    rate_limit_seconds: int = Field(
        1,
        title="Rate Limit 기간(초)",
        description="rate_limit_count가 적용되는 기간(초)"
    )
    """Sliding window length in seconds for rate limiting.

    rate limit이 적용되는 기간(초)입니다."""
    on_rate_limit: Literal["stop", "wait"] = Field(
        "stop",
        title="Rate Limit 동작",
        description='제한 초과 시 동작: "stop"은 중단(에러), "wait"은 대기 후 재시도'
    )
    """Behaviour when the limit is exceeded (``stop`` or ``wait``).

    제한 초과 시 동작을 ``stop`` 중단(에러 발생) 또는 ``wait``(대기 후 재시도) 중에서 선택합니다."""
    rate_limit_key: str = Field(
        None,
        title="Rate Limit 키",
        description="여러 인스턴스 간에 rate limit 상태를 공유하기 위한 키 (기본값: None)"
    )
    """Shared key for coordinating rate limit state across instances.

    여러 인스턴스 간 rate limit 상태를 공유하기 위한 키입니다. (기본값: None)"""

    # 내부 실행 컨텍스트에서만 참조하는 객체이므로 검증/직렬화와 분리
    token_manager: Optional[TokenManager] = Field(
        default=None,
        title="Token Manager",
        description="현재 요청에 사용되는 토큰 관리자",
        exclude=True,
        repr=False,
    )

    model_config = ConfigDict(
        # token_manager는 직렬화에서 제외되지만, 임의 객체라 검증에서 차단되지 않도록 허용
        arbitrary_types_allowed=True
    )


class OAuthRequestHeader(BaseModel):
    """OAuth authentication request header structure.

    OAuth 인증 요청 헤더를 표현하는 데이터 블록입니다."""
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
    """OAuth authentication response header schema.

    OAuth 인증 응답 헤더를 표현합니다."""
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
    """Securities block call request header envelope.

    LS증권 블록 호출 요청 헤더 정보를 담는 모델입니다."""
    content_type: str = Field(
        ..., alias="Content-Type",
        title="요청 콘텐츠 타입",
        description='LS증권 제공 API를 호출하기 위한 Request Body 데이터 포맷으로 "application/json; charset=utf-8 설정"'
    )
    """MIME type of the request payload (HTTP header ``Content-Type``).

    요청 본문의 MIME 타입(HTTP 헤더 ``Content-Type``)입니다."""
    authorization: str = Field(
        ...,
        title="인증 헤더",
        description='발급한 AccessToken, 예: "Bearer {access_token}"'
    )
    """Authorization header using the issued ``Bearer`` token.

    발급된 ``Bearer`` 토큰을 담는 인증 헤더 값입니다."""

    tr_cd: str = Field(
        ...,
        title="거래CD",
        description="LS증권거래코드, 예: COSAQ00102"
    )
    """Transaction code supplied by LS Securities.

    LS증권이 제공하는 거래 코드입니다."""

    tr_cont: Literal["Y", "N"] = Field(
        ...,
        title="연속거래여부",
        description="Y: 연속거래, N: 단건거래"
    )
    """Continuous transaction flag (``Y`` or ``N``).

    연속거래 여부를 나타내는 값입니다 (``Y``/``N``)."""

    tr_cont_key: str = Field(
        ...,
        title="연속거래Key",
        description="연속일 경우 그전에 내려온 연속 키값 올림"
    )
    """Continuation key echoed from previous paged responses.

    직전 응답에서 내려온 연속 거래 키입니다."""

    mac_address: str = Field(
        ...,
        title="MAC 주소",
        description="선택적, 필요시 사용"
    )
    """Optional MAC address supplied when required.

    필요 시 사용하는 선택적 MAC 주소입니다."""

    model_config = ConfigDict(
        populate_by_name=True
    )


class BlockResponseHeader(BaseModel):
    """Metadata returned alongside block call responses.

    블록 호출 응답과 함께 제공되는 메타데이터입니다."""
    content_type: str = Field(
        ...,
        alias="Content-Type",
        title="응답 콘텐츠 타입",
        description="컨텐츠타입 (실제 HTTP 헤더: Content-Type)"
    )
    """Response MIME type (HTTP header ``Content-Type``).

    응답 본문의 MIME 타입(HTTP 헤더 ``Content-Type``)입니다."""
    tr_cd: str = Field(
        ...,
        title="거래CD",
        description="LS증권거래코드"
    )
    """Transaction code returned by LS Securities.

    LS증권이 응답으로 반환하는 거래 코드입니다."""
    tr_cont: str = Field(
        ...,
        title="연속거래여부",
        description="Y: 연속거래, N: 단건거래"
    )
    """Continuous transaction indicator (``Y`` or ``N``).

    연속 거래 여부를 나타내는 값입니다 (``Y``/``N``)."""
    tr_cont_key: str = Field(
        ...,
        title="연속거래Key",
        description="연속일 경우 그전에 내려온 연속 키값 올림"
    )
    """Continuation key for fetching subsequent pages.

    후속 페이지 요청에 사용하는 연속 거래 키입니다."""

    model_config = ConfigDict(
        populate_by_name=True
    )


class BlockRealRequestHeader(BaseModel):
    """Request header used when registering for real-time streaming.

    실시간 스트리밍 등록/해제 시 사용하는 요청 헤더 모델입니다."""

    token: str = Field(..., description="Access Token")
    """Access token supplied to LS APIs.

    LS API로 전달하는 접근 토큰입니다."""
    tr_type: str = Field(..., description="1:계좌등록,2:계좌해제,3:실시간시세등록,4:실시간시세해제")
    """Transaction type discriminator for the real-time call.

    실시간 호출의 트랜잭션 타입 식별자입니다. (1:계좌등록,2:계좌해제,3:실시간시세등록,4:실시간시세해제)"""


class BlockRealResponseHeader(BaseModel):
    """Response header for real-time streaming registration results.

    실시간 스트리밍 등록 요청에 대한 응답 헤더 모델입니다."""

    tr_cd: str = Field(..., description="거래 CD")
    """Transaction code associated with the real-time stream.

    실시간 스트리밍과 매핑되는 거래 코드입니다."""
    tr_key: Optional[str] = Field(None, description="응답 종목 코드 + padding(공백12자리)")
    """Responded instrument code padded with blanks.

    공백 패딩이 포함된 응답 종목 코드입니다. 응답 종목 코드 + padding(공백12자리)"""
    tr_type: Optional[str] = Field(None, description="1:계좌등록,2:계좌해제,3:실시간시세등록,4:실시간시세해제")
    """Indicator describing registration/deregistration type.

    등록/해제 유형을 나타내는 식별자입니다. (1:계좌등록,2:계좌해제,3:실시간시세등록,4:실시간시세해제)"""
    rsp_cd: Optional[str] = Field(None, description="응답 코드")
    """Response code returned by LS Securities.

    LS증권이 반환하는 응답 코드입니다."""
    rsp_msg: Optional[str] = Field(None, description="응답 메시지")
    """Human-readable response message.

    사람이 읽을 수 있는 응답 메시지입니다."""
