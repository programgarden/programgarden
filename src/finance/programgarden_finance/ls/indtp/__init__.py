
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t1511
from .t1511 import TrT1511
from .t1511.blocks import T1511InBlock, T1511Request, T1511RequestHeader
from . import t1514
from .t1514 import TrT1514
from .t1514.blocks import T1514InBlock, T1514Request, T1514RequestHeader
from . import t1516
from .t1516 import TrT1516
from .t1516.blocks import T1516InBlock, T1516Request, T1516RequestHeader

from programgarden_core.korea_alias import require_korean_alias


class Indtp:
    """
    국내 업종(indtp) 지수를 조회하는 Indtp 클래스입니다.

    API 엔드포인트: /indtp/market-data (KOREA_STOCK_INDTP_URL)
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t1511(
        self,
        body: T1511InBlock,
        header: Optional[T1511RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1511:
        """
        업종현재가를 조회합니다.

        업종코드로 업종 지수, 등락률, 거래량, 52주 고저가, 하위 지수 등을 조회합니다.

        Args:
            body (T1511InBlock): upcode(업종코드) 입력
            header (Optional[T1511RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1511: 업종현재가 조회 인스턴스
        """

        request_data = T1511Request(
            body={
                "t1511InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1511(request_data)

    업종현재가 = t1511
    업종현재가.__doc__ = "업종코드로 업종 지수, 등락률, 거래량, 52주 고저가를 조회합니다."

    @require_korean_alias
    def t1514(
        self,
        body: T1514InBlock,
        header: Optional[T1514RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1514:
        """
        업종기간별추이를 조회합니다.

        업종코드로 해당 업종 지수의 기간별(일/주/월) 추이 시계열을 조회합니다.
        각 기간 행은 지수 OHLC(jisu/openjisu/highjisu/lowjisu), 전일대비/등락률,
        거래량/거래대금, 시장폭(상승/보합/하락/상한/하한 **종목수**), 외인·기관
        순매수, 거래비중, 업종배당수익률을 포함합니다.

        cts_date 기반 연속조회를 지원합니다(.req() 단건, .occurs_req() 전체).

        Args:
            body (T1514InBlock): upcode(업종코드), gubun2(주기 1일/2주/3월),
                cnt(조회건수), rate_gbn(비중구분) 입력
            header (Optional[T1514RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1514: 업종기간별추이 조회 인스턴스
        """

        request_data = T1514Request(
            body={
                "t1514InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1514(request_data)

    업종기간별추이 = t1514
    업종기간별추이.__doc__ = "업종코드로 업종 지수의 기간별(일/주/월) 추이(OHLC·등락률·거래량·시장폭·외인기관순매수)를 조회합니다."

    @require_korean_alias
    def t1516(
        self,
        body: T1516InBlock,
        header: Optional[T1516RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1516:
        """
        업종별종목시세를 조회합니다.

        업종코드로 해당 업종의 종목별 시세를 조회합니다.
        shcode 기반 연속조회를 지원합니다.

        Args:
            body (T1516InBlock): upcode(업종코드), gubun(구분), shcode(연속조회키) 입력
            header (Optional[T1516RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1516: 업종별종목시세 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1516Request(
            body={
                "t1516InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1516(request_data)

    업종별종목시세 = t1516
    업종별종목시세.__doc__ = "업종코드로 해당 업종의 종목별 시세(현재가, 등락률, PER 등)를 조회합니다."


__all__ = [
    Indtp,
    t1511,
    t1514,
    t1516,
]
