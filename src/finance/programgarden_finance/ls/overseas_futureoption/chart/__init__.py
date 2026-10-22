from typing import Optional

from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from .o3103 import TrO3103
from .o3103.blocks import (
    O3103InBlock,
    O3103Request,
    O3103RequestHeader,
)
from .o3108 import TrO3108
from .o3108.blocks import (
    O3108InBlock,
    O3108Request,
    O3108RequestHeader,
)
from .o3117 import TrO3117
from .o3117.blocks import (
    O3117InBlock,
    O3117Request,
    O3117RequestHeader,
)
from .o3139 import TrO3139
from .o3139.blocks import (
    O3139InBlock,
    O3139Request,
    O3139RequestHeader,
)

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class Chart(metaclass=EnforceKoreanAliasMeta):

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def o3103(
        self,
        body: O3103InBlock,
        header: Optional[O3103RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3103:
        """
        LS openAPI의 o3103 해외선물차트 분봉 조회합니다.

        Args:
            body (O3103InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3103: 조회를 위한 TrO3103 인스턴스
        """

        request_data = O3103Request(
            body={
                "o3103InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3103(request_data)

    해외선물_차트분봉조회 = o3103
    해외선물_차트분봉조회.__doc__ = "해외선물차트 분봉 조회합니다."

    @require_korean_alias
    def o3108(
        self,
        body: O3108InBlock,
        header: Optional[O3108RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3108:
        """
        LS openAPI의 o3108 해외선물차트 일주월 조회합니다.

        Args:
            body (O3108InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3108: 조회를 위한 TrO3108 인스턴스
        """

        request_data = O3108Request(
            body={
                "o3108InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3108(request_data)

    해외선물_차트일주월조회 = o3108
    해외선물_차트일주월조회.__doc__ = "해외선물차트 일주월 조회합니다."

    @require_korean_alias
    def o3117(
        self,
        body: O3117InBlock,
        header: Optional[O3117RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3117:
        """
        LS openAPI의 o3117 해외선물 차트 NTick 체결 조회합니다.

        Args:
            body (O3117InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3117: 조회를 위한 TrO3117 인스턴스
        """

        request_data = O3117Request(
            body={
                "o3117InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3117(request_data)

    해외선물_차트NTick체결조회 = o3117
    해외선물_차트NTick체결조회.__doc__ = "해외선물 차트 NTick 체결 조회합니다."

    @require_korean_alias
    def o3139(
        self,
        body: O3139InBlock,
        header: Optional[O3139RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3139:
        """
        LS openAPI의 o3139 해외선물옵션차트용NTick(고정형)-API용

        Args:
            body (O3139InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3139: 조회를 위한 TrO3139 인스턴스
        """

        request_data = O3139Request(
            body={
                "o3139InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3139(request_data)

    해외선물옵션_차트용NTick = o3139
    해외선물옵션_차트용NTick.__doc__ = "해외선물옵션차트용NTick(고정형)-API용"


__all__ = [
    Chart,

    TrO3103,
    TrO3108,
    TrO3117,
    TrO3139,

    O3103InBlock,
    O3108InBlock,
    O3117InBlock,
    O3139InBlock,

    O3103Request,
    O3108Request,
    O3117Request,
    O3139Request
]
