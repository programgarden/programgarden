
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t1403
from .t1403 import TrT1403
from .t1403.blocks import T1403InBlock, T1403Request, T1403RequestHeader
from . import t1638
from .t1638 import TrT1638
from .t1638.blocks import T1638InBlock, T1638Request, T1638RequestHeader
from . import t1927
from .t1927 import TrT1927
from .t1927.blocks import T1927InBlock, T1927Request, T1927RequestHeader
from . import t1941
from .t1941 import TrT1941
from .t1941.blocks import T1941InBlock, T1941Request, T1941RequestHeader

from programgarden_core.korea_alias import require_korean_alias


class Etc:
    """
    국내 주식 기타 정보를 조회하는 Etc 클래스입니다.

    신규상장종목, 관리/투자유의종목 등 종목 상태 관련 조회 TR을 제공합니다.
    API 엔드포인트: /stock/etc
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t1403(
        self,
        body: T1403InBlock,
        header: Optional[T1403RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1403:
        """
        [신규상장] 특정 기간에 신규 상장된 종목의 현재가, 공모가, 상장일 대비 등락률을 조회합니다.

        IPO 후 주가 흐름 분석, 신규 상장 모니터링에 활용합니다.
        idx 기반 연속조회를 지원합니다.

        Args:
            body (T1403InBlock): gubun(시장구분 0:전체/1:코스피/2:코스닥), styymm(시작상장월 YYYYMM), enyymm(종료상장월 YYYYMM), idx(연속조회키) 입력
            header (Optional[T1403RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1403: 신규상장종목 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1403Request(
            body={
                "t1403InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1403(request_data)

    신규상장종목조회 = t1403
    신규상장종목조회.__doc__ = "[신규상장] 특정 기간에 신규 상장된 종목의 현재가, 공모가, 상장일 대비 등락률을 조회합니다."

    @require_korean_alias
    def t1638(
        self,
        body: T1638InBlock,
        header: Optional[T1638RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1638:
        """
        LS openAPI의 t1638 종목별잔량/사전공시을(를) 조회합니다.
        """

        request_data = T1638Request(
            body={
                "t1638InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1638(request_data)

    종목별잔량사전공시 = t1638
    종목별잔량사전공시.__doc__ = "종목별 잔량/사전공시를 조회합니다."

    @require_korean_alias
    def t1927(
        self,
        body: T1927InBlock,
        header: Optional[T1927RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1927:
        """
        LS openAPI의 t1927 공매도일별추이을(를) 조회합니다.
        """

        request_data = T1927Request(
            body={
                "t1927InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1927(request_data)

    공매도일별추이 = t1927
    공매도일별추이.__doc__ = "공매도 일별 추이를 조회합니다."

    @require_korean_alias
    def t1941(
        self,
        body: T1941InBlock,
        header: Optional[T1941RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1941:
        """
        LS openAPI의 t1941 종목별대차거래일간추이을(를) 조회합니다.
        """

        request_data = T1941Request(
            body={
                "t1941InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1941(request_data)

    종목별대차거래일간추이 = t1941
    종목별대차거래일간추이.__doc__ = "종목별 대차거래 일간 추이를 조회합니다."


__all__ = [
    Etc,
    t1403,
    t1638,
    t1927,
    t1941,
]
