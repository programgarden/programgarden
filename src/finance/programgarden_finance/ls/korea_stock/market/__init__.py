
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


__init__ = [
    Market,
    t9945,
    t8450,
    t1101,
    t1102,
]
