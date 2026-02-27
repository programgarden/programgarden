
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t1511
from .t1511 import TrT1511
from .t1511.blocks import T1511InBlock, T1511Request, T1511RequestHeader
from . import t1516
from .t1516 import TrT1516
from .t1516.blocks import T1516InBlock, T1516Request, T1516RequestHeader
from . import t1531
from .t1531 import TrT1531
from .t1531.blocks import T1531InBlock, T1531Request, T1531RequestHeader
from . import t1532
from .t1532 import TrT1532
from .t1532.blocks import T1532InBlock, T1532Request, T1532RequestHeader
from . import t1537
from .t1537 import TrT1537
from .t1537.blocks import T1537InBlock, T1537Request, T1537RequestHeader

from programgarden_core.korea_alias import require_korean_alias


class Sector:
    """
    국내 주식 업종/테마를 조회하는 Sector 클래스입니다.

    API 엔드포인트: /stock/sector
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
    def t1531(
        self,
        body: T1531InBlock,
        header: Optional[T1531RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1531:
        """
        테마별종목을 조회합니다.

        테마명 또는 테마코드로 전체 테마 리스트 및 평균등락률을 조회합니다.

        Args:
            body (T1531InBlock): tmname(테마명), tmcode(테마코드) 입력
            header (Optional[T1531RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1531: 테마별종목 조회 인스턴스
        """

        request_data = T1531Request(
            body={
                "t1531InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1531(request_data)

    테마별종목 = t1531
    테마별종목.__doc__ = "테마별 종목 리스트 및 평균등락률을 조회합니다."

    @require_korean_alias
    def t1532(
        self,
        body: T1532InBlock,
        header: Optional[T1532RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1532:
        """
        종목별테마를 조회합니다.

        종목코드로 해당 종목이 속한 테마 리스트를 조회합니다.

        Args:
            body (T1532InBlock): shcode(종목코드) 입력
            header (Optional[T1532RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1532: 종목별테마 조회 인스턴스
        """

        request_data = T1532Request(
            body={
                "t1532InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1532(request_data)

    종목별테마 = t1532
    종목별테마.__doc__ = "종목코드로 해당 종목이 속한 테마 리스트를 조회합니다."

    @require_korean_alias
    def t1537(
        self,
        body: T1537InBlock,
        header: Optional[T1537RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1537:
        """
        테마종목별시세를 조회합니다.

        테마코드로 해당 테마에 속한 종목들의 시세를 조회합니다.

        Args:
            body (T1537InBlock): tmcode(테마코드) 입력
            header (Optional[T1537RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT1537: 테마종목별시세 조회 인스턴스
        """

        request_data = T1537Request(
            body={
                "t1537InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1537(request_data)

    테마종목별시세 = t1537
    테마종목별시세.__doc__ = "테마코드로 해당 테마 종목들의 시세(현재가, 등락률, 거래량, 시가총액)를 조회합니다."


__all__ = [
    Sector,
    t1511,
    t1516,
    t1531,
    t1532,
    t1537,
]
