"""
ProgramGarden Core - 예외 클래스 정의
"""

from typing import Optional, Any


class ProgramGardenError(Exception):
    """ProgramGarden 기본 예외"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(ProgramGardenError):
    """워크플로우 검증 오류"""

    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        field: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.node_id = node_id
        self.field = field


class ExecutionError(ProgramGardenError):
    """워크플로우 실행 오류"""

    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        node_id: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.job_id = job_id
        self.node_id = node_id


class CredentialError(ProgramGardenError):
    """인증 정보 오류"""

    def __init__(
        self,
        message: str,
        credential_id: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.credential_id = credential_id


class PluginError(ProgramGardenError):
    """플러그인 오류"""

    def __init__(
        self,
        message: str,
        plugin_id: Optional[str] = None,
        version: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.plugin_id = plugin_id
        self.version = version


class ConnectionError(ProgramGardenError):
    """연결 오류 (WebSocket, REST API)"""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.provider = provider


class OrderError(ProgramGardenError):
    """주문 실행 오류"""

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.order_id = order_id
        self.symbol = symbol


class DuplicateJobIdError(ProgramGardenError):
    """중복된 Job ID 오류

    동일한 job_id로 워크플로우 실행 시도 시 발생합니다.
    """

    def __init__(
        self,
        message: str = "이미 사용 중인 job_id입니다.",
        job_id: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.job_id = job_id


# =============================================================================
# Finance 패키지 전용 예외 (LS증권 OpenAPI)
# =============================================================================


class FinanceError(Exception):
    """Finance 패키지 기본 예외

    EN:
        Base exception for finance package carrying code, message, and payload.

    KO:
        Finance 패키지의 기본 예외로, 코드, 메시지, 데이터를 담습니다.
    """

    def __init__(
        self,
        message: str = "알 수 없는 금융 오류가 발생했습니다.",
        code: str = "FINANCE_ERROR",
        data: Optional[dict] = None,
    ):
        self.code: str = code
        self.message: str = message
        self.data: dict = dict(data or {})
        super().__init__(message)

    def to_payload(self, extra: Optional[dict] = None) -> dict:
        """예외를 딕셔너리로 직렬화"""
        payload_data = dict(self.data)
        if extra:
            payload_data.update(extra)
        return {
            "code": self.code,
            "message": self.message,
            "data": payload_data,
        }


class AppKeyException(FinanceError):
    """인증 키 누락 또는 유효하지 않음

    EN:
        Raised when appkey or secretkey credentials are missing or invalid.

    KO:
        appkey 또는 secretkey가 누락되었거나 유효하지 않을 때 발생합니다.
    """

    def __init__(
        self,
        message: str = "appkey 또는 secretkey가 존재하지 않습니다.",
        code: str = "APPKEY_NOT_FOUND",
        data: Optional[dict] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class LoginException(FinanceError):
    """로그인 실패

    EN:
        Raised when broker login attempts fail.

    KO:
        증권사 로그인에 실패했을 때 발생합니다.
    """

    def __init__(
        self,
        message: str = "로그인에 실패했습니다.",
        code: str = "LOGIN_ERROR",
        data: Optional[dict] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class TokenException(FinanceError):
    """토큰 발급 실패

    EN:
        Raised when issuing API tokens fails.

    KO:
        API 토큰 발급에 실패했을 때 발생합니다.
    """

    def __init__(
        self,
        message: str = "토큰 발급에 실패했습니다.",
        code: str = "TOKEN_ERROR",
        data: Optional[dict] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class TokenNotFoundException(FinanceError):
    """토큰을 찾을 수 없음

    EN:
        Raised when a previously issued token cannot be located.

    KO:
        발급된 토큰이 만료되었거나 존재하지 않을 때 발생합니다.
    """

    def __init__(
        self,
        message: str = "토큰이 존재하지 않습니다.",
        code: str = "TOKEN_NOT_FOUND",
        data: Optional[dict] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class TrRequestDataNotFoundException(FinanceError):
    """TR 요청 데이터 누락

    EN:
        Raised when mandatory TR request payloads are missing.

    KO:
        필수 TR(거래) 요청 파라미터가 누락되었을 때 발생합니다.
    """

    def __init__(
        self,
        message: str = "TR 요청 데이터가 존재하지 않습니다.",
        code: str = "TR_REQUEST_DATA_NOT_FOUND",
        data: Optional[dict] = None,
    ):
        super().__init__(message=message, code=code, data=data)
