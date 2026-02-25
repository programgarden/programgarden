
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t1444
from .t1444 import TrT1444
from .t1444.blocks import T1444InBlock, T1444Request, T1444RequestHeader
from . import t1452
from .t1452 import TrT1452
from .t1452.blocks import T1452InBlock, T1452Request, T1452RequestHeader

from programgarden_core.korea_alias import require_korean_alias


class Ranking:
    """
    국내 주식 순위(상위종목)를 조회하는 Ranking 클래스입니다.

    시가총액상위, 거래량상위 등 종목 순위 조회 TR을 제공합니다.
    API 엔드포인트: /stock/high-item
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t1444(
        self,
        body: T1444InBlock,
        header: Optional[T1444RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1444:
        """
        업종별 시가총액 상위 종목을 조회합니다.

        현재가, 등락률, 거래량, 시가총액, 업종 내 비중, 외국인 보유비중을 반환합니다.
        idx 기반 연속조회를 지원합니다 (한 번에 약 20건).

        Args:
            body (T1444InBlock): upcode(업종코드 3자리), idx(연속조회키) 입력
            header (Optional[T1444RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1444: 시가총액상위 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1444Request(
            body={
                "t1444InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1444(request_data)

    시가총액상위 = t1444
    시가총액상위.__doc__ = "업종별 시가총액 상위 종목(현재가, 등락률, 거래량, 시가총액, 외인비중)을 조회합니다."

    @require_korean_alias
    def t1452(
        self,
        body: T1452InBlock,
        header: Optional[T1452RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1452:
        """
        거래량 상위 종목을 조회합니다.

        시장구분, 등락률/가격/거래량 필터를 설정하여
        현재가, 등락률, 누적거래량, 회전율, 전일비를 반환합니다.
        idx 기반 연속조회를 지원합니다 (한 번에 약 40건).

        Args:
            body (T1452InBlock): gubun(시장구분), jnilgubun(전일구분), 필터 조건, idx(연속조회키) 입력
            header (Optional[T1452RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1452: 거래량상위 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1452Request(
            body={
                "t1452InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1452(request_data)

    거래량상위 = t1452
    거래량상위.__doc__ = "거래량 상위 종목(현재가, 등락률, 누적거래량, 회전율, 전일비)을 조회합니다."


__all__ = [
    Ranking,
    t1444,
    t1452,
]
