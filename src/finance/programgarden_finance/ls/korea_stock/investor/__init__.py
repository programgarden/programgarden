
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t1601
from .t1601 import TrT1601
from .t1601.blocks import T1601InBlock, T1601Request, T1601RequestHeader
from . import t1602
from .t1602 import TrT1602
from .t1602.blocks import T1602InBlock, T1602Request, T1602RequestHeader
from . import t1603
from .t1603 import TrT1603
from .t1603.blocks import T1603InBlock, T1603Request, T1603RequestHeader
from . import t1617
from .t1617 import TrT1617
from .t1617.blocks import T1617InBlock, T1617Request, T1617RequestHeader
from . import t1621
from .t1621 import TrT1621
from .t1621.blocks import T1621InBlock, T1621Request, T1621RequestHeader
from . import t1664
from .t1664 import TrT1664
from .t1664.blocks import T1664InBlock, T1664Request, T1664RequestHeader

from programgarden_core.korea_alias import require_korean_alias


class Investor:
    """
    국내 주식 투자자별 매매 동향을 조회하는 Investor 클래스입니다.

    API 엔드포인트: /stock/investortrading
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t1601(
        self,
        body: T1601InBlock,
        header: Optional[T1601RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1601:
        """
        투자자별종합을 조회합니다.

        코스피/코스닥/선물/옵션/ELW 시장별 12개 투자자 유형의 매수/매도/순매수를 조회합니다.

        Args:
            body (T1601InBlock): gubun1~4(수량/금액 구분), exchgubun(거래소구분) 입력
            header (Optional[T1601RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1601: 투자자별종합 조회 인스턴스
        """

        request_data = T1601Request(
            body={
                "t1601InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1601(request_data)

    투자자별종합 = t1601
    투자자별종합.__doc__ = "시장별 12개 투자자 유형의 매수/매도/순매수 종합 데이터를 조회합니다."

    @require_korean_alias
    def t1602(
        self,
        body: T1602InBlock,
        header: Optional[T1602RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1602:
        """
        시간대별투자자매매추이를 조회합니다.

        시장/업종별 시간대별 투자자 순매수 추이를 조회합니다.
        cts_time 기반 연속조회를 지원합니다.

        Args:
            body (T1602InBlock): market(시장구분), upcode(업종코드), gubun1~3, cts_time(연속조회키) 입력
            header (Optional[T1602RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1602: 시간대별투자자매매추이 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1602Request(
            body={
                "t1602InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1602(request_data)

    시간대별투자자매매추이 = t1602
    시간대별투자자매매추이.__doc__ = "시장/업종별 시간대별 투자자 순매수 추이를 조회합니다."

    @require_korean_alias
    def t1603(
        self,
        body: T1603InBlock,
        header: Optional[T1603RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1603:
        """
        시간대별투자자매매추이상세를 조회합니다.

        특정 투자자의 시간대별 매수/매도/순매수 수량 및 금액을 상세 조회합니다.
        cts_time/cts_idx 기반 연속조회를 지원합니다.

        Args:
            body (T1603InBlock): market(시장), gubun1(투자자구분), cts_time/cts_idx(연속조회키) 입력
            header (Optional[T1603RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1603: 시간대별투자자매매추이상세 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1603Request(
            body={
                "t1603InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1603(request_data)

    시간대별투자자매매추이상세 = t1603
    시간대별투자자매매추이상세.__doc__ = "특정 투자자의 시간대별 매수/매도/순매수 수량 및 금액을 상세 조회합니다."

    @require_korean_alias
    def t1617(
        self,
        body: T1617InBlock,
        header: Optional[T1617RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1617:
        """
        투자자매매종합2를 조회합니다.

        주요 투자자(개인, 외국인, 기관계, 증권)의 매매 동향을 시간대별/일별로 조회합니다.
        cts_date/cts_time 기반 연속조회를 지원합니다.

        Args:
            body (T1617InBlock): gubun1(시장), gubun2(수량/금액), gubun3(시간/일별), cts_date/cts_time(연속조회키) 입력
            header (Optional[T1617RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1617: 투자자매매종합2 조회 인스턴스 (.req() 단건, .occurs_req() 전체)
        """

        request_data = T1617Request(
            body={
                "t1617InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1617(request_data)

    투자자매매종합 = t1617
    투자자매매종합.__doc__ = "주요 투자자의 매매 동향을 시간대별/일별로 조회합니다."

    @require_korean_alias
    def t1621(
        self,
        body: T1621InBlock,
        header: Optional[T1621RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1621:
        """
        업종별분별투자자매매동향을 조회합니다.

        업종코드 기준으로 12개 투자자 유형의 분별 순매수 거래량/대금과 기준지수를 조회합니다.

        Args:
            body (T1621InBlock): upcode(업종코드), nmin(N분), cnt(조회건수), bgubun(전일분) 입력
            header (Optional[T1621RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1621: 업종별분별투자자매매동향 조회 인스턴스
        """

        request_data = T1621Request(
            body={
                "t1621InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1621(request_data)

    업종별분별투자자매매동향 = t1621
    업종별분별투자자매매동향.__doc__ = "업종별 분별 12개 투자자 유형의 순매수 거래량/대금을 조회합니다."

    @require_korean_alias
    def t1664(
        self,
        body: T1664InBlock,
        header: Optional[T1664RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1664:
        """
        투자자매매종합(차트)을 조회합니다.

        투자자 유형별 순매수와 차익/비차익 순매수, 베이시스를 차트 데이터로 조회합니다.

        Args:
            body (T1664InBlock): mgubun(시장), vagubun(금액/수량), bdgubun(시간/일별), cnt(조회건수) 입력
            header (Optional[T1664RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1664: 투자자매매종합(차트) 조회 인스턴스
        """

        request_data = T1664Request(
            body={
                "t1664InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1664(request_data)

    투자자매매종합차트 = t1664
    투자자매매종합차트.__doc__ = "투자자별 순매수와 차익/비차익, 베이시스를 차트 데이터로 조회합니다."


__all__ = [
    Investor,
    t1601,
    t1602,
    t1603,
    t1617,
    t1621,
    t1664,
]
