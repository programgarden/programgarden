
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from .CSPAQ22200 import TrCSPAQ22200
from .CSPAQ22200.blocks import (
    CSPAQ22200InBlock1,
    CSPAQ22200Request,
    CSPAQ22200RequestHeader,
)

from programgarden_core.korea_alias import require_korean_alias


class Accno:
    """
    국내 주식 계좌 정보를 조회하는 Accno 클래스입니다.

    API 엔드포인트: /stock/accno
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def cspaq22200(
        self,
        body: CSPAQ22200InBlock1 = None,
        header: Optional[CSPAQ22200RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCSPAQ22200:
        """
        현물계좌 예수금, 주문가능금액, 증거금, 담보, 정산금 등 종합 자산현황을 조회합니다.

        Args:
            body (CSPAQ22200InBlock1): BalCreTp(잔고생성구분, 기본 "0":주식잔고) 입력
            header (Optional[CSPAQ22200RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrCSPAQ22200: 예수금/주문가능금액 조회 인스턴스 (.req() 호출로 실행)
        """
        if body is None:
            body = CSPAQ22200InBlock1()

        request_data = CSPAQ22200Request(
            body={
                "CSPAQ22200InBlock1": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCSPAQ22200(request_data)

    현물계좌예수금주문가능금액총평가 = cspaq22200
    현물계좌예수금주문가능금액총평가.__doc__ = "현물계좌 예수금, 주문가능금액, 증거금, 담보, 정산금 등 종합 자산현황을 조회합니다."


__init__ = [
    Accno,
    CSPAQ22200,
]
