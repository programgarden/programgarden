
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t1403
from .t1403 import TrT1403
from .t1403.blocks import T1403InBlock, T1403Request, T1403RequestHeader
from . import t1404
from .t1404 import TrT1404
from .t1404.blocks import T1404InBlock, T1404Request, T1404RequestHeader
from . import t1405
from .t1405 import TrT1405
from .t1405.blocks import T1405InBlock, T1405Request, T1405RequestHeader

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


__all__ = [
    Etc,
    t1403,
    t1404,
    t1405,
]
