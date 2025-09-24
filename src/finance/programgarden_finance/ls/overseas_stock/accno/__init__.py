from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from .COSAQ00102 import TrCOSAQ00102
from .COSAQ00102.blocks import (
    COSAQ00102InBlock1,
    COSAQ00102Request,
    COSAQ00102RequestHeader,
)
from .COSAQ01400 import TrCOSAQ01400
from .COSAQ01400.blocks import (
    COSAQ01400InBlock1,
    COSAQ01400Request,
    COSAQ01400RequestHeader,
)
from .COSOQ00201 import TrCOSOQ00201
from .COSOQ00201.blocks import (
    COSOQ00201InBlock1,
    COSOQ00201Request,
    COSOQ00201RequestHeader,
)
from .COSOQ02701 import TrCOSOQ02701
from .COSOQ02701.blocks import (
    COSOQ02701InBlock1,
    COSOQ02701Request,
    COSOQ02701RequestHeader,
)
from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class Accno(metaclass=EnforceKoreanAliasMeta):
    """
    LS증권 OpenAPI 계좌 정보 클래스
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def cosaq00102(
        self,
        body: COSAQ00102InBlock1,
        header: Optional[COSAQ00102RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCOSAQ00102:
        """
        LS openAPI의 COSAQ00102 계좌 주문 내역을 조회합니다.

        Args:
            body (COSAQ00102InBlock1): 계좌 주문 내역 조회를 위한 입력 데이터입니다.
            header (Optional[COSAQ00102RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrCOSAQ00102: 계좌 주문 내역 조회를 위한 TrCOSAQ00102 인스턴스
        """
        request_data = COSAQ00102Request(
            body={
                "COSAQ00102InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCOSAQ00102(request_data)

    계좌주문체결내역조회 = cosaq00102
    계좌주문체결내역조회.__doc__ = "주문체결 내역을 조회합니다."

    @require_korean_alias
    def cosaq01400(
        self,
        body: COSAQ01400InBlock1,
        header: Optional[COSAQ01400RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCOSAQ01400:
        """
        LS openAPI의 COSAQ01400 계좌 예약 주문 처리결과를 조회합니다.

        Args:
            body (COSAQ01400InBlock1): 예약 주문 처리결과 조회를 위한 입력 데이터입니다.
            header (Optional[COSAQ01400RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrCOSAQ01400: 계좌 예약 주문 처리결과 조회를 위한 TR_COSAQ01400 인스턴스
        """
        request_data = COSAQ01400Request(
            body={
                "COSAQ01400InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCOSAQ01400(request_data)

    계좌예약주문처리결과조회 = cosaq01400
    계좌예약주문처리결과조회.__doc__ = "예약주문 처리결과를 조회합니다."

    @require_korean_alias
    def cosoq00201(
        self,
        body: COSOQ00201InBlock1,
        header: Optional[COSOQ00201RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCOSOQ00201:
        """
        LS openAPI의 COSOQ00201 해외주식 종합잔고평가를 조회합니다.

        Args:
            body (COSOQ00201InBlock1): 해외주식 종합잔고평가 조회를 위한 입력 데이터
            header (Optional[COSOQ00201RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrCOSOQ00201: 해외주식 종합잔고평가 조회를 위한 인스턴스
        """

        request_data = COSOQ00201Request(
                body={
                    "COSOQ00201InBlock1": body
                },
            )

        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCOSOQ00201(request_data)

    계좌종합잔고평가조회 = cosoq00201
    계좌종합잔고평가조회.__doc__ = "해외주식 종합잔고평가를 조회합니다."

    @require_korean_alias
    def cosoq02701(
        self,
        body: COSOQ02701InBlock1,
        header: Optional[COSOQ02701RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCOSOQ02701:
        """
        LS openAPI의 COSOQ02701 외화 예수금 및 주문 가능 금액을 조회합니다.

        Args:
            body (COSOQ02701InBlock1): 외화 예수금 및 주문 가능 금액 조회를 위한 입력 데이터입니다.
            header (Optional[COSOQ02701RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrCOSOQ02701: 외화 예수금 및 주문 가능 금액 조회를 위한 TR_COSOQ02701 인스턴스
        """

        request_data = COSOQ02701Request(
            body={
                "COSOQ02701InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCOSOQ02701(request_data)

    계좌외화예수금및주문가능금액조회 = cosoq02701
    계좌외화예수금및주문가능금액조회.__doc__ = "외화 예수금 및 주문 가능 금액을 조회합니다."


__all__ = [
    Accno,

    TrCOSAQ00102,
    COSAQ00102InBlock1,
    COSAQ00102Request,
    TrCOSAQ01400,
    COSAQ01400InBlock1,
    COSAQ01400Request,
    TrCOSOQ00201,
    COSOQ00201InBlock1,
    COSOQ00201Request,
    TrCOSOQ02701,
    COSOQ02701InBlock1,
    COSOQ02701Request,
]
