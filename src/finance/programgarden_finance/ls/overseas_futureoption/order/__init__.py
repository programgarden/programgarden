from typing import Optional

from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from .CIDBT00100 import TrCIDBT00100
from .CIDBT00100.blocks import (
    CIDBT00100InBlock1,
    CIDBT00100Request,
    CIDBT00100RequestHeader,
)
from .CIDBT00900 import TrCIDBT00900
from .CIDBT00900.blocks import (
    CIDBT00900InBlock1,
    CIDBT00900Request,
    CIDBT00900RequestHeader,
)
from .CIDBT01000 import TrCIDBT01000
from .CIDBT01000.blocks import (
    CIDBT01000InBlock1,
    CIDBT01000Request,
    CIDBT01000RequestHeader,
)

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class Order(metaclass=EnforceKoreanAliasMeta):

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def CIDBT00100(
        self,
        body: CIDBT00100InBlock1,
        header: Optional[CIDBT00100RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCIDBT00100:
        """
        LS openAPI의 CIDBT00100 해외선물 신규주문합니다.

        Args:
            body (O3103InBlock): 입력 데이터입니다.

        Returns:
            TrO3103: 주문를 위한 TrO3103 인스턴스
        """

        request_data = CIDBT00100Request(
            body={
                "CIDBT00100InBlock1": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCIDBT00100(request_data)

    해외선물_신규주문 = CIDBT00100
    해외선물_신규주문.__doc__ = "해외선물 신규주문합니다."

    @require_korean_alias
    def CIDBT00900(
        self,
        body: CIDBT00900InBlock1,
        header: Optional[CIDBT00900RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCIDBT00900:
        """
        LS openAPI의 CIDBT00900 해외선물 정정주문합니다.

        Args:
            body (CIDBT00900InBlock1): 입력 데이터입니다.

        Returns:
            TrCIDBT00900: 주문를 위한 TrCIDBT00900 인스턴스
        """

        request_data = CIDBT00900Request(
            body={
                "CIDBT00900InBlock1": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCIDBT00900(request_data)

    해외선물_정정주문 = CIDBT00900
    해외선물_정정주문.__doc__ = "해외선물 정정주문합니다."

    @require_korean_alias
    def CIDBT01000(
        self,
        body: CIDBT01000InBlock1,
        header: Optional[CIDBT01000RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrCIDBT01000:
        """
        LS openAPI의 CIDBT01000 해외선물 취소주문합니다.

        Args:
            body (CIDBT01000InBlock1): 입력 데이터입니다.

        Returns:
            TrCIDBT01000: 주문를 위한 TrCIDBT01000 인스턴스
        """

        request_data = CIDBT01000Request(
            body={
                "CIDBT01000InBlock1": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrCIDBT01000(request_data)

    해외선물_취소주문 = CIDBT01000
    해외선물_취소주문.__doc__ = "해외선물 취소주문합니다."


__all__ = [
    Order,

    TrCIDBT00100,
    TrCIDBT00900,
    TrCIDBT01000,

    CIDBT00100InBlock1,
    CIDBT00900InBlock1,
    CIDBT01000InBlock1,

    CIDBT00100Request,
    CIDBT00900Request,
    CIDBT01000Request,
]
