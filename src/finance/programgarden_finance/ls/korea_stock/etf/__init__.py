
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t1901
from .t1901 import TrT1901
from .t1901.blocks import T1901InBlock, T1901Request, T1901RequestHeader
from . import t1903
from .t1903 import TrT1903
from .t1903.blocks import T1903InBlock, T1903Request, T1903RequestHeader
from . import t1904
from .t1904 import TrT1904
from .t1904.blocks import T1904InBlock, T1904Request, T1904RequestHeader

from programgarden_core.korea_alias import require_korean_alias


class Etf:
    """
    국내 주식 ETF 정보를 조회하는 Etf 클래스입니다.

    ETF 현재가, 일별추이, 구성종목 조회 TR을 제공합니다.
    API 엔드포인트: /stock/etf
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t1901(
        self,
        body: T1901InBlock,
        header: Optional[T1901RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1901:
        """
        LS openAPI의 t1901 ETF현재가(시세)조회을(를) 조회합니다.
        """

        request_data = T1901Request(
            body={
                "t1901InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1901(request_data)

    ETF현재가조회 = t1901
    ETF현재가조회.__doc__ = "ETF 현재가(시세)를 조회합니다."

    @require_korean_alias
    def t1903(
        self,
        body: T1903InBlock,
        header: Optional[T1903RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1903:
        """
        LS openAPI의 t1903 ETF일별추이을(를) 조회합니다.
        """

        request_data = T1903Request(
            body={
                "t1903InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1903(request_data)

    ETF일별추이 = t1903
    ETF일별추이.__doc__ = "ETF 일별 추이를 조회합니다."

    @require_korean_alias
    def t1904(
        self,
        body: T1904InBlock,
        header: Optional[T1904RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1904:
        """
        LS openAPI의 t1904 ETF구성종목조회을(를) 조회합니다.
        """

        request_data = T1904Request(
            body={
                "t1904InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1904(request_data)

    ETF구성종목조회 = t1904
    ETF구성종목조회.__doc__ = "ETF 구성 종목을 조회합니다."


__all__ = [
    Etf,
    t1901,
    t1903,
    t1904,
]
