
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import g3101
from .g3101 import TrG3101
from .g3101.blocks import G3101InBlock, G3101Request, G3101RequestHeader

from . import g3102
from .g3102 import TrG3102
from .g3102.blocks import G3102InBlock, G3102Request, G3102RequestHeader

from . import g3104
from .g3104 import TrG3104
from .g3104.blocks import G3104InBlock, G3104Request, G3104RequestHeader

from . import g3106
from .g3106 import TrG3106
from .g3106.blocks import G3106InBlock, G3106Request, G3106RequestHeader

from . import g3190
from .g3190 import TrG3190
from .g3190.blocks import G3190InBlock, G3190Request, G3190RequestHeader

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class Market(metaclass=EnforceKoreanAliasMeta):
    """
    현재가를 조회하는 Market 클래스입니다.
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def g3101(
        self,
        body: G3101InBlock,
        header: Optional[G3101RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrG3101:
        """
        LS openAPI의 g3101 현재가를 조회합니다.

        Args:
            body (G3101Request): 조회를 위한 입력 데이터입니다.
            header (Optional[G3101RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrG3101: 조회를 위한 TrG3101 인스턴스
        """

        request_data = G3101Request(
            body={
                "g3101InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrG3101(request_data)

    현재가조회 = g3101
    현재가조회.__doc__ = "현재가를 조회합니다."

    @require_korean_alias
    def g3102(
        self,
        body: G3102InBlock,
        header: Optional[G3102RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        LS openAPI의 g3102 시간대별 조회를 합니다.

        Args:
            body (G3102InBlock): 조회를 위한 입력 데이터입니다.
            header (Optional[G3102RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrG3102: 조회를 위한 TrG3102 인스턴스
        """
        request_data = G3102Request(
            body={
                "g3102InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )
        return TrG3102(request_data)

    시간대별조회 = g3102
    시간대별조회.__doc__ = "시간대별 조회를 합니다."

    @require_korean_alias
    def g3104(
        self,
        body: G3104InBlock,
        header: Optional[G3104RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        LS openAPI의 g3104 종목정보 조회를 합니다.

        Args:
            body (G3104InBlock): 조회를 위한 입력 데이터입니다.
            header (Optional[G3104RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrG3104: 조회를 위한 TrG3104 인스턴스
        """
        request_data = G3104Request(
            body={
                "g3104InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )
        return TrG3104(request_data)

    종목정보조회 = g3104
    종목정보조회.__doc__ = "종목정보 조회를 합니다."

    @require_korean_alias
    def g3106(
        self,
        body: G3106InBlock,
        header: Optional[G3106RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        LS openAPI의 g3106 현재가호가 조회를 합니다.

        Args:
            body (G3106InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrG3106: 조회를 위한 TrG3106 인스턴스
        """

        request_data = G3106Request(
            body={
                "g3106InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrG3106(request_data)

    현재가호가조회 = g3106
    현재가호가조회.__doc__ = "현재가호가 조회를 합니다."

    @require_korean_alias
    def g3190(
        self,
        body: G3190InBlock,
        header: Optional[G3190RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        LS openAPI의 g3190 상장 종목들 조회를 합니다.

        Args:
            body (G3190InBlock): 조회를 위한 입력 데이터입니다.
            header (Optional[G3190RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrG3190: 조회를 위한 TrG3190 인스턴스
        """

        request_data = G3190Request(
            body={
                "g3190InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )
        return TrG3190(request_data)

    마스터상장종목조회 = g3190
    마스터상장종목조회.__doc__ = "상장 종목들 조회를 합니다."


__init__ = [
    Market,
    g3101,
    g3102,
    g3104,
    g3106,
    g3190,
]
