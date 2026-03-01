from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t8451
from .t8451 import TrT8451
from .t8451.blocks import T8451InBlock, T8451Request, T8451RequestHeader

from . import t8452
from .t8452 import TrT8452
from .t8452.blocks import T8452InBlock, T8452Request, T8452RequestHeader
from . import t8453
from .t8453 import TrT8453
from .t8453.blocks import T8453InBlock, T8453Request, T8453RequestHeader
from . import t1665
from .t1665 import TrT1665
from .t1665.blocks import T1665InBlock, T1665Request, T1665RequestHeader

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class Chart:
    """
    국내 주식 차트를 조회하는 Chart 클래스입니다.
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t8451(
        self,
        body: T8451InBlock,
        header: Optional[T8451RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT8451:
        """
        LS openAPI의 t8451 주식차트(일주월년) API용을 조회합니다.

        Args:
            body (T8451InBlock): 조회를 위한 입력 데이터입니다.
            header (Optional[T8451RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT8451: 조회를 위한 TrT8451 인스턴스
        """

        request_data = T8451Request(
            body={
                "t8451InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT8451(request_data)

    주식차트 = t8451
    주식차트.__doc__ = "주식차트(일주월년)를 조회합니다."

    @require_korean_alias
    def t8452(
        self,
        body: T8452InBlock,
        header: Optional[T8452RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT8452:
        """
        LS openAPI의 t8452 주식차트N분을(를) 조회합니다.
        """

        request_data = T8452Request(
            body={
                "t8452InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT8452(request_data)

    주식차트N분 = t8452
    주식차트N분.__doc__ = "주식 차트(N분)를 조회합니다."

    @require_korean_alias
    def t8453(
        self,
        body: T8453InBlock,
        header: Optional[T8453RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT8453:
        """
        LS openAPI의 t8453 주식차트틱을(를) 조회합니다.
        """

        request_data = T8453Request(
            body={
                "t8453InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT8453(request_data)

    주식차트틱 = t8453
    주식차트틱.__doc__ = "주식 차트(틱/N틱)를 조회합니다."

    @require_korean_alias
    def t1665(
        self,
        body: T1665InBlock,
        header: Optional[T1665RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1665:
        """
        LS openAPI의 t1665 기간별투자자매매추이(차트)을(를) 조회합니다.
        """

        request_data = T1665Request(
            body={
                "t1665InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1665(request_data)

    기간별투자자매매추이 = t1665
    기간별투자자매매추이.__doc__ = "기간별 투자자 매매추이(차트)를 조회합니다."


__all__ = [
    Chart,
    t8451,
    t8452,
    t8453,
    t1665,
]
