from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from .COSAT00301 import TrCOSAT00301
from .COSAT00301.blocks import (
    COSAT00301InBlock1,
    COSAT00301Request,
    COSAT00301RequestHeader,
)
from .COSAT00311 import TrCOSAT00311
from .COSAT00311.blocks import (
    COSAT00311InBlock1,
    COSAT00311Request,
    COSAT00311RequestHeader,
)
from .COSMT00300 import TrCOSMT00300
from .COSMT00300.blocks import (
    COSMT00300InBlock1,
    COSMT00300Request,
    COSMT00300RequestHeader,
)
from .COSAT00400 import TrCOSAT00400
from .COSAT00400.blocks import (
    COSAT00400InBlock1,
    COSAT00400Request,
    COSAT00400RequestHeader,
)

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class Order(metaclass=EnforceKoreanAliasMeta):
    """
    LS증권 OpenAPI 주문 정보 클래스
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def cosat00301(
        self,
        body: COSAT00301InBlock1,
        header: Optional[COSAT00301RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCOSAT00301:
        """
        LS openAPI의 COSAT00301 미국 시장 주문을 요청합니다.

        Args:
            body (COSAT00301InBlock1): 미국 시장 주문 요청을 위한 입력 데이터입니다.
            header (Optional[COSAT00301RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrCOSAT00301: 미국 시장 주문을 요청하기 위한 TrCOSAT00301 인스턴스
        """
        request_data = COSAT00301Request(
            body={
                "COSAT00301InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCOSAT00301(
            request_data=request_data
        )

    미국시장주문 = cosat00301
    미국시장주문.__doc__ = "미국 시장 주문을 요청합니다."

    @require_korean_alias
    def cosat00311(
        self,
        body: COSAT00311InBlock1,
        header: Optional[COSAT00311RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCOSAT00311:
        """
        LS openAPI의 COSAT00311 미국 시장 정정 주문을 요청합니다.

        Args:
            body (COSAT00311InBlock1): 미국 시장 정정 주문 요청을 위한 입력 데이터입니다.
            header (Optional[COSAT00311RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrCOSAT00311: 미국 시장 정정 주문을 요청하기 위한 TrCOSAT00311 인스턴스
        """
        request_data = COSAT00311Request(
            body={
                "COSAT00311InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCOSAT00311(request_data)

    미국시장정정주문 = cosat00311
    미국시장정정주문.__doc__ = "미국 시장 정정 주문을 요청합니다."

    @require_korean_alias
    def cosmt00300(
        self,
        body: COSMT00300InBlock1,
        header: Optional[COSMT00300RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCOSMT00300:
        """
        LS openAPI의 COSMT00300 미국 시장 주문을 요청합니다.

        Args:
            body (COSMT00300InBlock1): 미국 시장 주문 요청을 위한 입력 데이터입니다.
            header (Optional[COSMT00300RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrCOSMT00300: 미국 시장 주문을 요청하기 위한 TrCOSMT00300 인스턴스
        """
        request_data = COSMT00300Request(
            body={
                "COSMT00300InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )
        return TrCOSMT00300(request_data)

    해외증권매도상환주문 = cosmt00300
    해외증권매도상환주문.__doc__ = "해외 증권 매도 상환 주문을 요청합니다."

    @require_korean_alias
    def cosat00400(
        self,
        body: COSAT00400InBlock1,
        header: Optional[COSAT00400RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCOSAT00400:
        """
        LS openAPI의 COSAT00400 해외주식 예약주문 등록 및 취소를 요청합니다.

        Args:
            body (COSAT00400InBlock1): 해외주식 예약주문 등록 및 취소 요청을 위한 입력 데이터입니다.
            header (Optional[COSAT00400RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrCOSAT00400: 해외주식 예약주문 등록 및 취소를 요청하기 위한 TrCOSAT00400 인스턴스
        """
        request_data = COSAT00400Request(
            body={
                "COSAT00400InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )
        return TrCOSAT00400(request_data)

    해외주식예약주문_등록및취소 = cosat00400
    해외주식예약주문_등록및취소.__doc__ = "해외주식 예약주문 등록 및 취소를 요청합니다."


__all__ = [
    Order,

    COSAT00301Request,
    COSAT00301InBlock1,
    COSAT00301RequestHeader,

    COSAT00311Request,
    COSAT00311InBlock1,
    COSAT00311RequestHeader,

    COSMT00300Request,
    COSMT00300InBlock1,
    COSMT00300RequestHeader,

    COSAT00400Request,
    COSAT00400InBlock1,
    COSAT00400RequestHeader,

    TrCOSAT00301,
    TrCOSAT00311,
    TrCOSMT00300,
    TrCOSAT00400
]
