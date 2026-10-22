
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
from . import t1463
from .t1463 import TrT1463
from .t1463.blocks import T1463InBlock, T1463Request, T1463RequestHeader
from . import t1441
from .t1441 import TrT1441
from .t1441.blocks import T1441InBlock, T1441Request, T1441RequestHeader
from . import t1466
from .t1466 import TrT1466
from .t1466.blocks import T1466InBlock, T1466Request, T1466RequestHeader
from . import t1481
from .t1481 import TrT1481
from .t1481.blocks import T1481InBlock, T1481Request, T1481RequestHeader

from . import t1482
from .t1482 import TrT1482
from .t1482.blocks import T1482InBlock, T1482Request, T1482RequestHeader

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

    @require_korean_alias
    def t1463(
        self,
        body: T1463InBlock,
        header: Optional[T1463RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1463:
        """
        거래대금 상위 종목을 조회합니다.

        시장구분, 가격/거래량 필터를 설정하여
        현재가, 등락률, 거래대금, 전일거래대금, 전일비, 시가총액을 반환합니다.
        idx 기반 연속조회를 지원합니다 (한 번에 약 20건).

        Args:
            body (T1463InBlock): gubun(시장구분), jnilgubun(전일구분), 필터 조건, idx(연속조회키) 입력
            header (Optional[T1463RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1463: 거래대금상위 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1463Request(
            body={
                "t1463InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1463(request_data)

    거래대금상위 = t1463
    거래대금상위.__doc__ = "거래대금 상위 종목(현재가, 등락률, 거래대금, 전일거래대금, 전일비, 시가총액)을 조회합니다."

    @require_korean_alias
    def t1441(
        self,
        body: T1441InBlock,
        header: Optional[T1441RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1441:
        """
        등락률 상위 종목을 조회합니다.

        시장구분, 상승/하락, 가격/거래량 필터를 설정하여
        현재가, 등락률, 거래량, 시가총액을 반환합니다.
        idx 기반 연속조회를 지원합니다.

        Args:
            body (T1441InBlock): gubun1(시장구분), gubun2(상승하락), 필터 조건, idx(연속조회키) 입력
            header (Optional[T1441RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1441: 등락율상위 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1441Request(
            body={
                "t1441InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1441(request_data)

    등락율상위 = t1441
    등락율상위.__doc__ = "등락률 상위 종목(현재가, 등락률, 거래량, 시가총액)을 조회합니다."

    @require_korean_alias
    def t1466(
        self,
        body: T1466InBlock,
        header: Optional[T1466RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1466:
        """
        전일 동시간 대비 거래량이 급증한 종목을 조회합니다.

        시장구분, 가격/거래량 필터를 설정하여
        현재가, 등락률, 전일동시간거래량, 금일거래량, 거래급증률을 반환합니다.
        idx 기반 연속조회를 지원합니다.

        Args:
            body (T1466InBlock): gubun(시장구분), 필터 조건, idx(연속조회키) 입력
            header (Optional[T1466RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1466: 전일동시간대비거래급증 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1466Request(
            body={
                "t1466InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1466(request_data)

    전일동시간대비거래급증 = t1466
    전일동시간대비거래급증.__doc__ = "전일 동시간 대비 거래량 급증 종목(현재가, 등락률, 전일동시간거래량, 거래급증률)을 조회합니다."

    @require_korean_alias
    def t1481(
        self,
        body: T1481InBlock,
        header: Optional[T1481RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1481:
        """
        시간외 거래에서 등락률 상위 종목을 조회합니다.

        시장구분, 상승/하락, 가격/거래량 필터를 설정하여
        시간외 현재가, 등락률, 거래량을 반환합니다.
        idx 기반 연속조회를 지원합니다.

        Args:
            body (T1481InBlock): gubun(시장구분), 필터 조건, idx(연속조회키) 입력
            header (Optional[T1481RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1481: 시간외등락율상위 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1481Request(
            body={
                "t1481InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1481(request_data)

    시간외등락율상위 = t1481
    시간외등락율상위.__doc__ = "시간외 거래 등락률 상위 종목(시간외 현재가, 등락률, 거래량)을 조회합니다."

    @require_korean_alias
    def t1482(
        self,
        body: T1482InBlock,
        header: Optional[T1482RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1482:
        """
        LS openAPI의 t1482 시간외거래량상위을(를) 조회합니다.
        """

        request_data = T1482Request(
            body={
                "t1482InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1482(request_data)

    시간외거래량상위 = t1482
    시간외거래량상위.__doc__ = "시간외 거래량 상위 종목을 조회합니다."


__all__ = [
    Ranking,
    t1444,
    t1452,
    t1463,
    t1441,
    t1466,
    t1481,
    t1482,
]
