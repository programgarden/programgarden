
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
from . import t8408
from .t8408 import TrT8408
from .t8408.blocks import T8408InBlock, T8408Request, T8408RequestHeader
from . import t8409
from .t8409 import TrT8409
from .t8409.blocks import T8409InBlock, T8409Request, T8409RequestHeader

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

    @require_korean_alias
    def t8408(
        self,
        body: T8408InBlock,
        header: Optional[T8408RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT8408:
        """
        업종차트(틱/n틱)를 조회합니다.

        업종코드로 해당 업종 지수의 틱/N틱 차트를 조회합니다. 응답은 메타/커서
        블록(cont_block = 전일·당일 지수 OHLC, 거래량, 연속커서, 장 시작/종료
        시간, 레코드카운트)과 틱 행 리스트(block = 각 봉의 날짜/시간/지수
        OHLC/거래량)로 구성됩니다.

        주의: 모든 OHLC 값은 업종 지수(index points)이며 KRW 가격이 아닙니다.

        cts_date/cts_time 기반 연속조회를 지원합니다(.req() 단건, .occurs_req() 전체).

        Args:
            body (T8408InBlock): shcode(업종코드), ncnt(N틱 단위), qrycnt(요청건수),
                nday(조회영업일수), sdate/edate(조회기간), comp_yn(압축여부) 입력
            header (Optional[T8408RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT8408: 업종차트(틱/n틱) 조회 인스턴스
        """

        request_data = T8408Request(
            body={
                "t8408InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT8408(request_data)

    업종차트틱 = t8408
    업종차트틱.__doc__ = "업종코드로 업종 지수의 틱/N틱 차트(지수 OHLC·거래량)를 조회합니다."

    @require_korean_alias
    def t8409(
        self,
        body: T8409InBlock,
        header: Optional[T8409RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT8409:
        """
        업종차트(N분)를 조회합니다.

        업종코드로 해당 업종 지수의 N분(0=30초) 차트를 조회합니다. 응답은
        메타/커서 블록(cont_block = 전일·당일 지수 OHLC, 전일거래량,
        당일거래대금, 연속커서, 업종 시작/종료 시간, 레코드카운트)과 분봉 행
        리스트(block = 각 봉의 날짜/시간/지수 OHLC/거래량/거래대금)로
        구성됩니다.

        주의: 모든 OHLC 값은 업종 지수(index points)이며 KRW 가격이 아닙니다.
        거래대금(disvalue/value)은 백만원, 거래량(jivolume/jdiff_vol)은 천주
        단위로, LS 명세 미선언 → 샘플 응답 교차검증 확정값입니다.

        cts_date/cts_time 기반 연속조회를 지원합니다(.req() 단건, .occurs_req() 전체).

        Args:
            body (T8409InBlock): shcode(업종코드), ncnt(단위 0=30초/1=1분/n분),
                qrycnt(요청건수), nday(조회영업일수), sdate/edate(조회기간),
                comp_yn(압축여부) 입력
            header (Optional[T8409RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT8409: 업종차트(N분) 조회 인스턴스
        """

        request_data = T8409Request(
            body={
                "t8409InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT8409(request_data)

    업종차트분 = t8409
    업종차트분.__doc__ = "업종코드로 업종 지수의 N분(0=30초) 차트(지수 OHLC·거래량·거래대금)를 조회합니다."


__all__ = [
    Indtp,
    t1511,
    t1514,
    t1516,
    t8408,
    t8409,
]
