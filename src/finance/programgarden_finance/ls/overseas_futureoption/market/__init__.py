from typing import List, Optional

from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from .o3101 import TrO3101
from .o3101.blocks import (
    O3101InBlock,
    O3101Request,
    O3101RequestHeader,
)
from .o3104 import TrO3104
from .o3104.blocks import (
    O3104InBlock,
    O3104Request,
    O3104RequestHeader,
)
from .o3105 import TrO3105
from .o3105.blocks import (
    O3105InBlock,
    O3105Request,
    O3105RequestHeader,
)
from .o3106 import TrO3106
from .o3106.blocks import (
    O3106InBlock,
    O3106Request,
    O3106RequestHeader,
)
from .o3107 import TrO3107
from .o3107.blocks import (
    O3107InBlock,
    O3107Request,
    O3107RequestHeader
)
from .o3116 import TrO3116
from .o3116.blocks import (
    O3116InBlock,
    O3116Request,
    O3116RequestHeader
)
from .o3121 import TrO3121
from .o3121.blocks import (
    O3121InBlock,
    O3121Request,
    O3121RequestHeader
)
from .o3123 import TrO3123
from .o3123.blocks import (
    O3123InBlock,
    O3123Request,
    O3123RequestHeader,
)
from .o3125 import TrO3125
from .o3125.blocks import (
    O3125InBlock,
    O3125Request,
    O3125RequestHeader
)
from .o3126 import TrO3126
from .o3126.blocks import (
    O3126InBlock,
    O3126Request,
    O3126RequestHeader,
)
from .o3127 import TrO3127
from .o3127.blocks import (
    O3127InBlock,
    O3127InBlock1,
    O3127Request,
    O3127RequestHeader
)
from .o3128 import TrO3128
from .o3128.blocks import (
    O3128InBlock,
    O3128Request,
    O3128RequestHeader,
)
from .o3136 import TrO3136
from .o3136.blocks import (
    O3136InBlock,
    O3136Request,
    O3136RequestHeader,
)
from .o3137 import TrO3137
from .o3137.blocks import (
    O3137InBlock,
    O3137Request,
    O3137RequestHeader,
)

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class Market(metaclass=EnforceKoreanAliasMeta):

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def o3101(
        self,
        body: O3101InBlock,
        header: Optional[O3101RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3101:
        """
        LS openAPI의 o3101 해외선물 마스터를 조회합니다.

        Args:
            body (O3101InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3101: 조회를 위한 TrO3101 인스턴스
        """

        request_data = O3101Request(
            body={
                "o3101InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3101(request_data)

    해외선물마스터조회 = o3101
    해외선물마스터조회.__doc__ = "해외선물 마스터(상품들)를 조회합니다."

    @require_korean_alias
    def o3104(
        self,
        body: O3104InBlock,
        header: Optional[O3104RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3104:
        """
        LS openAPI의 o3104 해외선물 일별체결 조회합니다.

        Args:
            body (O3104InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3104: 조회를 위한 TrO3104 인스턴스
        """

        request_data = O3104Request(
            body={
                "o3104InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3104(request_data)

    해외선물_일별체결조회 = o3104
    해외선물_일별체결조회.__doc__ = "해외선물 일별체결 조회합니다."

    @require_korean_alias
    def o3105(
        self,
        body: O3105InBlock,
        header: Optional[O3105RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3105:
        """
        LS openAPI의 o3105 해외선물 현재가(종목정보) 조회합니다.

        Args:
            body (O3105InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3105: 조회를 위한 TrO3105 인스턴스
        """

        request_data = O3105Request(
            body={
                "o3105InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3105(request_data)

    해외선물_현재가조회 = o3105
    해외선물_현재가조회.__doc__ = "해외선물 현재가 조회합니다."

    @require_korean_alias
    def o3106(
        self,
        body: O3106InBlock,
        header: Optional[O3106RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3106:
        """
        LS openAPI의 o31056 해외선물 현재가호가 조회합니다.

        Args:
            body (O3106InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3106: 조회를 위한 TrO3106 인스턴스
        """
        request_data = O3106Request(
            body={
                "o3106InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3106(request_data)

    해외선물_현재가호가조회 = o3106
    해외선물_현재가호가조회.__doc__ = "해외선물 현재가 호가 조회합니다."

    @require_korean_alias
    def o3107(
        self,
        body: O3107InBlock,
        header: Optional[O3107RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3107:
        """
        LS openAPI의 o3107 해외선물 관심종목 조회합니다.

        Args:
            body (O3107InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3107: 조회를 위한 TrO3107 인스턴스
        """
        request_data = O3107Request(
            body={
                "o3107InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3107(request_data)

    해외선물_관심종목조회 = o3107
    해외선물_관심종목조회.__doc__ = "해외선물 관심종목 조회합니다."

    @require_korean_alias
    def o3116(
        self,
        body: O3116InBlock,
        header: Optional[O3116RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3116:
        """
        LS openAPI의 o3116 해외선물 시간대별(Tick)체결 조회합니다.

        Args:
            body (O3116InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3116: 조회를 위한 TrO3116 인스턴스
        """
        request_data = O3116Request(
            body={
                "o3116InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3116(request_data)

    해외선물_시간대별Tick체결조회 = o3116
    해외선물_시간대별Tick체결조회.__doc__ = "해외선물 시간대별(Tick)체결 조회합니다."

    @require_korean_alias
    def o3121(
        self,
        body: O3121InBlock,
        header: Optional[O3121RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3121:
        """
        LS openAPI의 o3121 해외선물옵션 마스터 조회합니다.

        Args:
            body (O3121InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3121: 조회를 위한 TrO3121 인스턴스
        """
        request_data = O3121Request(
            body={
                "o3121InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3121(request_data)

    해외선물옵션_마스터조회 = o3121
    해외선물옵션_마스터조회.__doc__ = "해외선물옵션 마스터 조회합니다."

    @require_korean_alias
    def o3123(
        self,
        body: O3123InBlock,
        header: Optional[O3123RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3123:
        """
        LS openAPI의 o3123 해외선물옵션 차트 분봉 조회합니다.

        Args:
            body (O3123InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3123: 조회를 위한 TrO3123 인스턴스
        """
        request_data = O3123Request(
            body={
                "o3123InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3123(request_data)

    해외선물옵션_차트분봉조회 = o3123
    해외선물옵션_차트분봉조회.__doc__ = "해외선물옵션 차트 분봉 조회합니다."

    @require_korean_alias
    def o3125(
        self,
        body: O3125InBlock,
        header: Optional[O3125RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3125:
        """
        LS openAPI의 o3125 해외선물옵션 현재가 조회합니다.

        Args:
            body (O3125InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3125: 조회를 위한 TrO3125 인스턴스
        """
        request_data = O3125Request(
            body={
                "o3125InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3125(request_data)

    해외선물옵션_현재가조회 = o3125
    해외선물옵션_현재가조회.__doc__ = "해외선물옵션 현재가 조회합니다."

    @require_korean_alias
    def o3126(
        self,
        body: O3126InBlock,
        header: Optional[O3126RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3126:
        """
        LS openAPI의 o3126 해외선물옵션 현재가호가 조회합니다.

        Args:
            body (O3126InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3126: 조회를 위한 TrO3126 인스턴스
        """
        request_data = O3126Request(
            body={
                "o3126InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3126(request_data)

    해외선물옵션_현재가호가조회 = o3126
    해외선물옵션_현재가호가조회.__doc__ = "해외선물옵션 현재가호가 조회합니다."

    @require_korean_alias
    def o3127(
        self,
        o3127InBlock_body: O3127InBlock,
        o3127InBlock1_body: Optional[List[O3127InBlock1]] = None,
        header: Optional[O3127RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3127:
        """
        LS openAPI의 o3127 해외선물옵션 관심종목 조회합니다.

        Args:
            o3127InBlock_body (O3127InBlock): 조회를 위한 입력 데이터입니다.
            o3127InBlock1_body (Optional[List[O3127InBlock1]]): 조회를 위한 입력 데이터입니다.
            header (Optional[O3127RequestHeader]): 요청 헤더 데이터입니다.
            options (Optional[SetupOptions]): 설정 옵션입니다.

        Returns:
            TrO3127: 조회를 위한 TrO3127 인스턴스
        """
        request_data = O3127Request(
            body={
                "o3127InBlock": o3127InBlock_body,
                "o3127InBlock1": o3127InBlock1_body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3127(request_data)

    해외선물옵션_관심종목조회 = o3127
    해외선물옵션_관심종목조회.__doc__ = "해외선물옵션 관심종목 조회합니다."

    @require_korean_alias
    def o3128(
        self,
        body: O3128InBlock,
        header: Optional[O3128RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3128:
        """
        LS openAPI의 o3128 해외선물옵션 차트 일주월 조회합니다.

        Args:
            body (O3128InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3128: 조회를 위한 TrO3128 인스턴스
        """
        request_data = O3128Request(
            body={
                "o3128InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3128(request_data)

    해외선물옵션_차트일주월조회 = o3128
    해외선물옵션_차트일주월조회.__doc__ = "해외선물옵션 차트 일주월 조회합니다."

    @require_korean_alias
    def o3136(
        self,
        body: O3136InBlock,
        header: Optional[O3136RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3136:
        request_data = O3136Request(
            body={
                "o3136InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3136(request_data)

    해외선물옵션_시간대별Tick체결조회 = o3136
    해외선물옵션_시간대별Tick체결조회.__doc__ = "해외선물옵션 시간대별 Tick 체결 조회합니다."

    @require_korean_alias
    def o3137(
        self,
        body: O3137InBlock,
        header: Optional[O3137RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrO3137:
        """
        LS openAPI의 o3137 해외선물옵션 차트 NTick 체결 조회합니다.

        Args:
            body (O3137InBlock): 조회를 위한 입력 데이터입니다.

        Returns:
            TrO3137: 조회를 위한 TrO3137 인스턴스
        """
        request_data = O3137Request(
            body={
                "o3137InBlock": body,
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrO3137(request_data)

    해외선물옵션_차트NTick체결조회 = o3137
    해외선물옵션_차트NTick체결조회.__doc__ = "해외선물옵션 차트 NTick 체결 조회합니다."


__all__ = [
    Market,

    TrO3101,
    TrO3104,
    TrO3105,
    TrO3106,
    TrO3116,
    TrO3121,
    TrO3123,
    TrO3125,
    TrO3126,
    TrO3127,
    TrO3128,
    TrO3136,

    O3101InBlock,
    O3104InBlock,
    O3105InBlock,
    O3106InBlock,
    O3116InBlock,
    O3121InBlock,
    O3123InBlock,
    O3125InBlock,
    O3126InBlock,
    O3127InBlock,
    O3128InBlock,
    O3136InBlock,

    O3101Request,
    O3104Request,
    O3105Request,
    O3106Request,
    O3116Request,
    O3121Request,
    O3123Request,
    O3125Request,
    O3126Request,
    O3127Request,
    O3128Request,
    O3136Request
]
