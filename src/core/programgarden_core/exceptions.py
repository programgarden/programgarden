"""커스텀 예외 클래스 정의 모듈."""

from typing import Any, Dict, Optional


class BasicException(Exception):
    """오픈소스의 기본 에러 클래스"""

    def __init__(
        self,
        message: str = "알 수 없는 오류가 발생했습니다.",
        code: str = "UNKNOWN_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        self.code: str = code
        self.message: str = message
        self.data: Dict[str, Any] = dict(data or {})
        super().__init__(message)

    def to_payload(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload_data = dict(self.data)
        if extra:
            payload_data.update(extra)
        return {
            "code": self.code,
            "message": self.message,
            "data": payload_data,
        }


class SystemShutdownException(BasicException):
    """시스템이 종료되었습니다."""

    def __init__(
        self,
        message: str = "시스템이 정상적으로 종료되었습니다.",
        code: str = "SYSTEM_SHUTDOWN",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class AppKeyException(BasicException):
    """앱키가 존재하지 않음"""

    def __init__(
        self,
        message: str = "appkey 또는 secretkey가 존재하지 않습니다.",
        code: str = "APPKEY_NOT_FOUND",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class LoginException(BasicException):
    """로그인 실패"""

    def __init__(
        self,
        message: str = "로그인에 실패했습니다.",
        code: str = "LOGIN_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class TokenException(BasicException):
    """토큰 발급 실패"""

    def __init__(
        self,
        message: str = "토큰 발급 실패했습니다.",
        code: str = "TOKEN_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class TokenNotFoundException(BasicException):
    """토큰이 존재하지 않음"""

    def __init__(
        self,
        message: str = "토큰이 존재하지 않습니다.",
        code: str = "TOKEN_NOT_FOUND",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class TrRequestDataNotFoundException(BasicException):
    """TR 요청 데이터가 존재하지 않음"""

    def __init__(
        self,
        message: str = "TR 요청 데이터가 존재하지 않습니다.",
        code: str = "TR_REQUEST_DATA_NOT_FOUND",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class SystemException(BasicException):
    """시스템 오류"""

    def __init__(
        self,
        message: str = "시스템 오류가 발생했습니다.",
        code: str = "SYSTEM_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class NotExistSystemException(SystemException):
    """존재하지 않는 시스템"""

    def __init__(
        self,
        message: str = "존재하지 않는 시스템입니다.",
        code: str = "NOT_EXIST_SYSTEM",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class NotExistSystemKeyException(SystemException):
    """존재하지 않는 키"""

    def __init__(
        self,
        message: str = "존재하지 않는 키입니다.",
        code: str = "NOT_EXIST_KEY",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class NotExistConditionException(SystemException):
    """존재하지 않는 조건"""

    def __init__(
        self,
        message: str = "존재하지 않는 조건입니다.",
        code: str = "NOT_EXIST_CONDITION",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class OrderException(SystemException):
    """주문 관련 오류"""

    def __init__(
        self,
        message: str = "주문 처리 중 오류가 발생했습니다.",
        code: str = "ORDER_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class NotExistCompanyException(SystemException):
    """존재하지 않는 증권사"""

    def __init__(
        self,
        message: str = "증권사가 존재하지 않습니다.",
        code: str = "NOT_EXIST_COMPANY",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class InvalidCronExpressionException(SystemException):

    def __init__(
        self,
        message: str = "잘못된 Cron 식입니다.",
        code: str = "INVALID_CRON_EXPRESSION",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class ConditionExecutionException(SystemException):
    """조건 실행 중 발생하는 예외"""

    def __init__(
        self,
        message: str = "조건 실행 중 오류가 발생했습니다.",
        code: str = "CONDITION_EXECUTION_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class OrderExecutionException(OrderException):
    """주문 실행 중 발생하는 예외"""

    def __init__(
        self,
        message: str = "주문 실행 중 오류가 발생했습니다.",
        code: str = "ORDER_EXECUTION_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class StrategyExecutionException(SystemException):
    """전략 실행 중 발생하는 예외"""

    def __init__(
        self,
        message: str = "전략 실행 중 오류가 발생했습니다.",
        code: str = "STRATEGY_EXECUTION_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)


class SystemInitializationException(SystemException):
    """시스템 초기화 과정에서 발생하는 예외"""

    def __init__(
        self,
        message: str = "시스템 초기화 중 오류가 발생했습니다.",
        code: str = "SYSTEM_INITIALIZATION_ERROR",
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, data=data)
