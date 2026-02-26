
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from .CSPAT00601 import TrCSPAT00601
from .CSPAT00601.blocks import (
    CSPAT00601InBlock1,
    CSPAT00601Request,
    CSPAT00601RequestHeader,
)
from .CSPAT00701 import TrCSPAT00701
from .CSPAT00701.blocks import (
    CSPAT00701InBlock1,
    CSPAT00701Request,
    CSPAT00701RequestHeader,
)

from programgarden_core.korea_alias import require_korean_alias


class Order:
    """
    국내 주식 주문을 처리하는 Order 클래스입니다.

    API 엔드포인트: /stock/order
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def cspat00601(
        self,
        body: CSPAT00601InBlock1,
        header: Optional[CSPAT00601RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCSPAT00601:
        """
        국내주식 현물 매수/매도 주문을 요청합니다.

        Args:
            body (CSPAT00601InBlock1): 종목번호, 수량, 가격, 매매구분 등 입력
            header (Optional[CSPAT00601RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrCSPAT00601: 현물주문 인스턴스 (.req() 호출로 실행)
        """
        request_data = CSPAT00601Request(
            body={
                "CSPAT00601InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCSPAT00601(request_data)

    현물주문 = cspat00601
    현물주문.__doc__ = "국내주식 현물 매수/매도 주문을 요청합니다."

    @require_korean_alias
    def cspat00701(
        self,
        body: CSPAT00701InBlock1,
        header: Optional[CSPAT00701RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCSPAT00701:
        """
        국내주식 현물 정정주문을 요청합니다.

        원주문번호(OrgOrdNo)는 cspat00601(현물주문) 시 받은 OrdNo를 사용합니다.

        Args:
            body (CSPAT00701InBlock1): 원주문번호, 종목번호, 수량, 호가유형, 가격 입력
            header (Optional[CSPAT00701RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrCSPAT00701: 현물정정주문 인스턴스 (.req() 호출로 실행)
        """
        request_data = CSPAT00701Request(
            body={
                "CSPAT00701InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCSPAT00701(request_data)

    현물정정주문 = cspat00701
    현물정정주문.__doc__ = "국내주식 현물 정정주문을 요청합니다."


__init__ = [
    Order,
    CSPAT00601,
    CSPAT00701,
]
