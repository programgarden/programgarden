"""
커스텀 예외 클래스들
"""


class BasicException(Exception):
    """오픈소스의 기본 에러 클래스"""

    def __init__(
        self,
        message: str = "알 수 없는 오류가 발생했습니다.",
        code: str = "UNKNOWN_ERROR",
    ):
        super().__init__(message, code)


class AppKeyException(BasicException):
    """앱키가 존재하지 않음"""

    def __init__(
        self,
        message: str = "appkey 또는 secretkey가 존재하지 않습니다.",
        code: str = "APPKEY_NOT_FOUND",
    ):
        super().__init__(message, code)


class LoginException(BasicException):
    """로그인 실패"""

    def __init__(
        self,
        message: str = "로그인에 실패했습니다.",
        code: str = "LOGIN_ERROR",
    ):
        super().__init__(message, code)


class TokenException(BasicException):
    """토큰 발급 실패"""

    def __init__(
        self,
        message: str = "토큰 발급 실패했습니다.",
        code: str = "TOKEN_ERROR",
    ):
        super().__init__(message, code)


class TokenNotFoundException(BasicException):
    """토큰이 존재하지 않음"""

    def __init__(
        self,
        message: str = "토큰이 존재하지 않습니다.",
        code: str = "TOKEN_NOT_FOUND",
    ):
        super().__init__(message, code)


class TrRequestDataNotFoundException(BasicException):
    """TR 요청 데이터가 존재하지 않음"""

    def __init__(
        self,
        message: str = "TR 요청 데이터가 존재하지 않습니다.",
        code: str = "TR_REQUEST_DATA_NOT_FOUND",
    ):
        super().__init__(message, code)


class SystemException(BasicException):
    """시스템 오류"""

    def __init__(
        self,
        message: str = "시스템 오류가 발생했습니다.",
        code: str = "SYSTEM_ERROR",
    ):
        super().__init__(message, code)


class NotExistSystemException(SystemException):
    """존재하지 않는 시스템"""

    def __init__(
        self,
        message: str = "존재하지 않는 시스템입니다.",
        code: str = "NOT_EXIST_SYSTEM",
    ):
        super().__init__(message, code)


class NotExistSystemKeyException(SystemException):
    """존재하지 않는 키"""

    def __init__(
        self,
        message: str = "존재하지 않는 키입니다.",
        code: str = "NOT_EXIST_KEY",
    ):
        super().__init__(message, code)


class NotExistConditionException(SystemException):
    """존재하지 않는 조건"""

    def __init__(
        self,
        message: str = "존재하지 않는 조건입니다.",
        code: str = "NOT_EXIST_CONDITION",
    ):
        super().__init__(message, code)


class OrderException(SystemException):
    """주문 관련 오류"""

    def __init__(
        self,
        message: str = "주문 처리 중 오류가 발생했습니다.",
        code: str = "ORDER_ERROR",
    ):
        super().__init__(message, code)


class NotExistCompanyException(SystemException):
    """존재하지 않는 증권사"""

    def __init__(
        self,
        message: str = "증권사가 존재하지 않습니다.",
        code: str = "NOT_EXIST_COMPANY",
    ):
        super().__init__(message, code)
