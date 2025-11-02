"""Custom exception definitions used throughout ProgramGarden.

EN:
    Centralizes domain-specific error types so that the finance, core, and
    application layers can raise rich exceptions with structured payloads.

KO:
    금융, 코어, 애플리케이션 레이어에서 공통으로 사용하는 도메인 전용 예외를
    모아 구조화된 오류 정보를 제공하도록 합니다.
"""

from typing import Any, Dict, Optional


class BasicException(Exception):
    """Base exception carrying a code, message, and optional payload.

    EN:
        Stores additional metadata in ``code`` and ``data`` so that API
        consumers can inspect machine-readable details.

    KO:
        ``code`` 와 ``data`` 속성에 구조화된 메타데이터를 담아 API 소비자가
        기계적으로 오류를 식별할 수 있도록 합니다.
    """

    def __init__(
        self,
        message: str = "알 수 없는 오류가 발생했습니다.",
        code: str = "UNKNOWN_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a basic exception instance with structured fields.

        Parameters:
            message (str): Human-readable error summary.
            code (str): Machine-friendly identifier describing the error type.
            data (Optional[Dict[str, Any]]): Extra context to attach to payloads.
        """
        self.code: str = code
        self.message: str = message
        self.data: Dict[str, Any] = dict(data or {})
        super().__init__(message)

    def to_payload(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Serialize the exception into a dictionary payload.

        EN:
            Merge ``self.data`` with ``extra`` to make transport-friendly error
            objects suitable for logging or API responses.

        KO:
            ``self.data`` 와 ``extra`` 를 병합하여 로그 및 API 응답에 사용하기 좋은
            사전 형태의 오류 객체를 생성합니다.

        Parameters:
            extra (Optional[Dict[str, Any]]): Additional metadata to merge.

        Returns:
            Dict[str, Any]: Structured payload containing code, message, data.
        """
        payload_data = dict(self.data)
        if extra:
            payload_data.update(extra)
        return {
            "code": self.code,
            "message": self.message,
            "data": payload_data,
        }


class SystemShutdownException(BasicException):
    """Raised when ProgramGarden performs a controlled shutdown.

    EN:
        Indicates that execution stopped gracefully and clients can terminate
        background work without retrying.

    KO:
        프로그램이 정상적으로 종료되었다는 신호이며, 클라이언트는 재시도 없이
        백그라운드 작업을 마무리할 수 있습니다.
    """

    def __init__(
        self,
        message: str = "시스템이 정상적으로 종료되었습니다.",
        code: str = "SYSTEM_SHUTDOWN",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class AppKeyException(BasicException):
    """Raised when authentication keys are missing or invalid.

    EN:
        Emitted when ``appkey`` or ``secretkey`` credentials are absent from the
        configuration payload.

    KO:
        설정 값에 ``appkey`` 또는 ``secretkey`` 가 없거나 잘못되었을 때 발생합니다.
    """

    def __init__(
        self,
        message: str = "appkey 또는 secretkey가 존재하지 않습니다.",
        code: str = "APPKEY_NOT_FOUND",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class LoginException(BasicException):
    """Raised when broker login attempts fail.

    EN:
        Signals that the authentication workflow could not complete with the
        provided credentials.

    KO:
        제공된 자격 증명으로 인증 플로우가 완료되지 못했음을 나타냅니다.
    """

    def __init__(
        self,
        message: str = "로그인에 실패했습니다.",
        code: str = "LOGIN_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class TokenException(BasicException):
    """Raised when issuing API tokens fails unexpectedly.

    EN:
        Wraps errors produced during token creation steps.

    KO:
        토큰 발급 과정에서 발생한 예외를 감싸 전달합니다.
    """

    def __init__(
        self,
        message: str = "토큰 발급 실패했습니다.",
        code: str = "TOKEN_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class TokenNotFoundException(BasicException):
    """Raised when a previously issued token cannot be located.

    EN:
        Often triggered when secure storage is empty or expired.

    KO:
        보관된 토큰이 만료되었거나 존재하지 않을 때 발생합니다.
    """

    def __init__(
        self,
        message: str = "토큰이 존재하지 않습니다.",
        code: str = "TOKEN_NOT_FOUND",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class TrRequestDataNotFoundException(BasicException):
    """Raised when mandatory TR request payloads are missing.

    EN:
        Indicates that API calls lack required transaction request parameters.

    KO:
        필수 거래 요청 파라미터가 누락되었음을 나타냅니다.
    """

    def __init__(
        self,
        message: str = "TR 요청 데이터가 존재하지 않습니다.",
        code: str = "TR_REQUEST_DATA_NOT_FOUND",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class SystemException(BasicException):
    """Generic system-level error raised by core components.

    EN:
        Represents unexpected failures originating from internal subsystems.

    KO:
        내부 서브시스템에서 발생하는 일반적인 시스템 오류를 나타냅니다.
    """

    def __init__(
        self,
        message: str = "시스템 오류가 발생했습니다.",
        code: str = "SYSTEM_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class NotExistSystemException(SystemException):
    """Raised when a requested system definition cannot be found.

    EN:
        Occurs if a client references a nonexistent system identifier.

    KO:
        존재하지 않는 시스템 ID를 참조했을 때 발생합니다.
    """

    def __init__(
        self,
        message: str = "존재하지 않는 시스템입니다.",
        code: str = "NOT_EXIST_SYSTEM",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class NotExistSystemKeyException(SystemException):
    """Raised when a requested system key is missing.

    EN:
        Provides clarity when configuration dictionaries lack specific keys.

    KO:
        구성 사전에 특정 키가 없을 때 원인을 명확히 알려줍니다.
    """

    def __init__(
        self,
        message: str = "존재하지 않는 키입니다.",
        code: str = "NOT_EXIST_KEY",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class NotExistConditionException(SystemException):
    """Raised when strategy condition identifiers do not exist.

    EN:
        Notifies callers that the requested condition mapping is undefined.

    KO:
        요청한 조건 매핑이 정의되지 않았음을 호출자에게 알려줍니다.
    """

    def __init__(
        self,
        message: str = "존재하지 않는 조건입니다.",
        code: str = "NOT_EXIST_CONDITION",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class OrderException(SystemException):
    """Base exception for order processing failures.

    EN:
        Serves as the parent for all order-related runtime errors.

    KO:
        주문 처리 중 발생하는 런타임 오류의 상위 예외로 사용됩니다.
    """

    def __init__(
        self,
        message: str = "주문 처리 중 오류가 발생했습니다.",
        code: str = "ORDER_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class NotExistCompanyException(SystemException):
    """Raised when a brokerage company code is unrecognized.

    EN:
        Helps developers detect configuration mismatches with broker metadata.

    KO:
        증권사 메타데이터와 구성이 일치하지 않을 때 문제를 진단합니다.
    """

    def __init__(
        self,
        message: str = "증권사가 존재하지 않습니다.",
        code: str = "NOT_EXIST_COMPANY",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class InvalidCronExpressionException(SystemException):
    """Raised when cron expressions fail validation.

    EN:
        Alerts callers that schedule strings violate cron syntax rules.

    KO:
        스케줄 문자열이 크론 문법을 위반했음을 알립니다.
    """
    def __init__(
        self,
        message: str = "잘못된 Cron 식입니다.",
        code: str = "INVALID_CRON_EXPRESSION",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class ConditionExecutionException(SystemException):
    """Raised when evaluating strategy conditions fails.

    EN:
        Wraps exceptions thrown by reusable condition evaluators.

    KO:
        전략 조건 평가기에서 발생한 예외를 감싸 제공합니다.
    """

    def __init__(
        self,
        message: str = "조건 실행 중 오류가 발생했습니다.",
        code: str = "CONDITION_EXECUTION_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class OrderExecutionException(OrderException):
    """Raised when executing orders encounters runtime errors.

    EN:
        Indicates problems occurring during submission or broker responses.

    KO:
        주문 전송 또는 브로커 응답 처리 중 문제를 나타냅니다.
    """

    def __init__(
        self,
        message: str = "주문 실행 중 오류가 발생했습니다.",
        code: str = "ORDER_EXECUTION_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class StrategyExecutionException(SystemException):
    """Raised when strategy orchestration fails.

    EN:
        Signals that strategy loops or evaluators produced unrecoverable errors.

    KO:
        전략 루프나 평가기에서 복구 불가능한 오류가 발생했음을 나타냅니다.
    """

    def __init__(
        self,
        message: str = "전략 실행 중 오류가 발생했습니다.",
        code: str = "STRATEGY_EXECUTION_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class SystemInitializationException(SystemException):
    """Raised when initializing systems or plugins fails.

    EN:
        Points to errors during setup phases such as dependency wiring.

    KO:
        의존성 연결 등 초기화 단계에서 발생한 문제를 알려줍니다.
    """

    def __init__(
        self,
        message: str = "시스템 초기화 중 오류가 발생했습니다.",
        code: str = "SYSTEM_INITIALIZATION_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)
