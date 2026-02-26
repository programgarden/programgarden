
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t9945
from .t9945 import TrT9945
from .t9945.blocks import T9945InBlock, T9945Request, T9945RequestHeader
from . import t8450
from .t8450 import TrT8450
from .t8450.blocks import T8450InBlock, T8450Request, T8450RequestHeader
from . import t1101
from .t1101 import TrT1101
from .t1101.blocks import T1101InBlock, T1101Request, T1101RequestHeader
from . import t1102
from .t1102 import TrT1102
from .t1102.blocks import T1102InBlock, T1102Request, T1102RequestHeader
from . import t1301
from .t1301 import TrT1301
from .t1301.blocks import T1301InBlock, T1301Request, T1301RequestHeader
from . import t1471
from .t1471 import TrT1471
from .t1471.blocks import T1471InBlock, T1471Request, T1471RequestHeader
from . import t1475
from .t1475 import TrT1475
from .t1475.blocks import T1475InBlock, T1475Request, T1475RequestHeader
from . import t1404
from .t1404 import TrT1404
from .t1404.blocks import T1404InBlock, T1404Request, T1404RequestHeader
from . import t1405
from .t1405 import TrT1405
from .t1405.blocks import T1405InBlock, T1405Request, T1405RequestHeader
from . import t1422
from .t1422 import TrT1422
from .t1422.blocks import T1422InBlock, T1422Request, T1422RequestHeader
from . import t1442
from .t1442 import TrT1442
from .t1442.blocks import T1442InBlock, T1442Request, T1442RequestHeader

from programgarden_core.korea_alias import require_korean_alias


class Market:
    """
    국내 주식 시세를 조회하는 Market 클래스입니다.

    API 엔드포인트: /stock/market-data
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t9945(
        self,
        body: T9945InBlock,
        header: Optional[T9945RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT9945:
        """
        LS openAPI의 t9945 주식마스터조회API용을 조회합니다.

        Args:
            body (T9945InBlock): 조회를 위한 입력 데이터입니다.
            header (Optional[T9945RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT9945: 조회를 위한 TrT9945 인스턴스
        """

        request_data = T9945Request(
            body={
                "t9945InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT9945(request_data)

    주식마스터조회 = t9945
    주식마스터조회.__doc__ = "주식마스터를 조회합니다."

    @require_korean_alias
    def t8450(
        self,
        body: T8450InBlock,
        header: Optional[T8450RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT8450:
        """
        LS openAPI의 t8450 주식현재가호가조회2 API용을 조회합니다.

        Args:
            body (T8450InBlock): 조회를 위한 입력 데이터입니다.
            header (Optional[T8450RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT8450: 조회를 위한 TrT8450 인스턴스
        """

        request_data = T8450Request(
            body={
                "t8450InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT8450(request_data)

    주식현재가호가조회 = t8450
    주식현재가호가조회.__doc__ = "주식현재가호가를 조회합니다."

    @require_korean_alias
    def t1101(
        self,
        body: T1101InBlock,
        header: Optional[T1101RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1101:
        """
        [호가 전용] 매도/매수 10단계 호가, 호가잔량, 직전대비, 예상체결가를 조회합니다.

        시세/펀더멘탈/증권사동향이 필요하면 t1102를 사용하세요.

        Args:
            body (T1101InBlock): shcode(종목코드 6자리) 입력
            header (Optional[T1101RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1101: 호가 조회 인스턴스 (.req() 호출로 실행)
        """

        request_data = T1101Request(
            body={
                "t1101InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1101(request_data)

    주식현재가호가 = t1101
    주식현재가호가.__doc__ = "[호가 전용] 매도/매수 10단계 호가, 호가잔량, 직전대비, 예상체결가를 조회합니다."

    @require_korean_alias
    def t1102(
        self,
        body: T1102InBlock,
        header: Optional[T1102RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1102:
        """
        [시세/종합정보] 현재가, 등락률, 거래량, 시고저가, PER/PBR, 시가총액,
        증권사별 매매동향(Top5), 외국계 매매동향, 재무실적을 조회합니다.

        호가(매도/매수 10단계)가 필요하면 t1101을 사용하세요.

        Args:
            body (T1102InBlock): shcode(종목코드 6자리), exchgubun(거래소구분) 입력
            header (Optional[T1102RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1102: 시세 조회 인스턴스 (.req() 호출로 실행)
        """

        request_data = T1102Request(
            body={
                "t1102InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1102(request_data)

    주식현재가시세 = t1102
    주식현재가시세.__doc__ = "[시세/종합정보] 현재가, 등락률, PER/PBR, 시가총액, 증권사/외국계 매매동향, 재무실적을 조회합니다."

    @require_korean_alias
    def t1301(
        self,
        body: T1301InBlock,
        header: Optional[T1301RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1301:
        """
        주식 시간대별 체결 내역을 조회합니다.

        종목코드, 시작/종료시간 조건으로
        체결시간, 현재가, 체결량, 매도/매수 체결수량을 반환합니다.
        cts_time 기반 연속조회를 지원합니다.

        Args:
            body (T1301InBlock): shcode(종목코드), starttime, endtime, cts_time(연속조회키) 입력
            header (Optional[T1301RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1301: 시간대별체결 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1301Request(
            body={
                "t1301InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1301(request_data)

    주식시간대별체결조회 = t1301
    주식시간대별체결조회.__doc__ = "주식 시간대별 체결 내역(체결시간, 현재가, 체결량, 매도/매수 체결수량)을 조회합니다."

    @require_korean_alias
    def t1471(
        self,
        body: T1471InBlock,
        header: Optional[T1471RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1471:
        """
        시간대별 호가 잔량 추이를 조회합니다.

        종목코드, 시간 조건으로
        매도잔량, 매수잔량, 호가, 순매수잔량, 매수비율을 반환합니다.
        time 기반 연속조회를 지원합니다.

        Args:
            body (T1471InBlock): shcode(종목코드), gubun(분단위), time(연속조회키) 입력
            header (Optional[T1471RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1471: 시간대별호가잔량추이 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1471Request(
            body={
                "t1471InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1471(request_data)

    시간대별호가잔량추이 = t1471
    시간대별호가잔량추이.__doc__ = "시간대별 호가 잔량 추이(매도잔량, 매수잔량, 호가, 순매수잔량, 매수비율)를 조회합니다."

    @require_korean_alias
    def t1475(
        self,
        body: T1475InBlock,
        header: Optional[T1475RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1475:
        """
        체결강도 추이를 조회합니다.

        종목코드, 분/일 구분 조건으로
        체결강도, 이동평균(5/20/60) 체결강도를 반환합니다.
        date+time 기반 연속조회를 지원합니다.

        Args:
            body (T1475InBlock): shcode(종목코드), vptype(체결강도구분), gubun(분/일구분) 입력
            header (Optional[T1475RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1475: 체결강도추이 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1475Request(
            body={
                "t1475InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1475(request_data)

    체결강도추이 = t1475
    체결강도추이.__doc__ = "체결강도 추이(체결강도, 이동평균 5/20/60 체결강도)를 조회합니다."

    @require_korean_alias
    def t1404(
        self,
        body: T1404InBlock,
        header: Optional[T1404RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1404:
        """
        관리종목, 불성실공시, 투자유의, 투자환기 종목을 조회합니다.

        시장구분, 종목체크 구분 조건으로
        현재가, 등락률, 거래량, 지정일, 사유를 반환합니다.
        cts_shcode 기반 연속조회를 지원합니다.

        Args:
            body (T1404InBlock): gubun(시장구분), jongchk(종목체크 1:관리/2:불성실공시/3:투자유의/4:투자환기), cts_shcode(연속조회키) 입력
            header (Optional[T1404RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1404: 관리/불성실/투자유의 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1404Request(
            body={
                "t1404InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1404(request_data)

    관리불성실투자유의조회 = t1404
    관리불성실투자유의조회.__doc__ = "관리종목, 불성실공시, 투자유의, 투자환기 종목을 조회합니다."

    @require_korean_alias
    def t1405(
        self,
        body: T1405InBlock,
        header: Optional[T1405RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1405:
        """
        투자경고, 매매정지, 정리매매, 투자주의/위험/위험예고 종목을 조회합니다.

        시장구분, 종목체크 구분 조건으로
        현재가, 등락률, 거래량, 지정일, 해제일을 반환합니다.
        cts_shcode 기반 연속조회를 지원합니다.

        Args:
            body (T1405InBlock): gubun(시장구분), jongchk(종목체크 1:투자경고/2:매매정지/3:정리매매 등), cts_shcode(연속조회키) 입력
            header (Optional[T1405RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1405: 투자경고/매매정지/정리매매 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1405Request(
            body={
                "t1405InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1405(request_data)

    투자경고매매정지정리매매조회 = t1405
    투자경고매매정지정리매매조회.__doc__ = "투자경고, 매매정지, 정리매매, 투자주의/위험/위험예고 종목을 조회합니다."

    @require_korean_alias
    def t1422(
        self,
        body: T1422InBlock,
        header: Optional[T1422RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1422:
        """
        상한가/하한가 종목을 조회합니다.

        시장구분, 당일/전일, 상한/하한 조건으로
        현재가, 등락률, 거래량, 매도잔량, 매수잔량을 반환합니다.
        idx 기반 연속조회를 지원합니다.

        Args:
            body (T1422InBlock): gubun(시장구분), sign(상한/하한), 필터 조건, idx(연속조회키) 입력
            header (Optional[T1422RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1422: 상하한가 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1422Request(
            body={
                "t1422InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1422(request_data)

    상하한가 = t1422
    상하한가.__doc__ = "상한가/하한가 종목(현재가, 등락률, 거래량, 매도잔량, 매수잔량)을 조회합니다."

    @require_korean_alias
    def t1442(
        self,
        body: T1442InBlock,
        header: Optional[T1442RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1442:
        """
        신고가/신저가 종목을 조회합니다.

        기간별(52주, 연중, 월중 등) 신고가/신저가 종목을 반환합니다.
        idx 기반 연속조회를 지원합니다.

        Args:
            body (T1442InBlock): gubun(시장구분), type1(기간구분), type2(고저구분), 필터 조건, idx(연속조회키) 입력
            header (Optional[T1442RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1442: 신고/신저가 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1442Request(
            body={
                "t1442InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1442(request_data)

    신고신저가 = t1442
    신고신저가.__doc__ = "신고가/신저가 종목(52주, 연중, 월중 등 기간별)을 조회합니다."


__all__ = [
    Market,
    t9945,
    t8450,
    t1101,
    t1102,
    t1301,
    t1471,
    t1475,
    t1404,
    t1405,
    t1422,
    t1442,
]
