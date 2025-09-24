from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from .g3103 import TrG3103
from .g3103.blocks import G3103InBlock, G3103Request, G3103RequestHeader

from .g3202 import TrG3202
from .g3202.blocks import G3202InBlock, G3202Request, G3202RequestHeader

from .g3203 import TrG3203
from .g3203.blocks import G3203InBlock, G3203Request, G3203RequestHeader

from .g3204 import TrG3204
from .g3204.blocks import G3204InBlock, G3204Request, G3204RequestHeader

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class Chart(metaclass=EnforceKoreanAliasMeta):
    """
    특정 일자를 기준으로 매월,매일,매년을 조회하는 클래스
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def g3103(
        self,
        body: G3103InBlock,
        header: Optional[G3103RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        LS openAPI의 g3103 일주월 기간을 조회합니다.

        Args:
            body (G3103InBlock): 일주월 조회를 위한 입력 데이터입니다.
            header (Optional[G3103RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrG3103: 일주월 조회를 위한 TrG3103 인스턴스
        """

        request_data = G3103Request(
                body={
                    "g3103InBlock": body
                },
            )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrG3103(request_data)

    일주월조회 = g3103
    일주월조회.__doc__ = "특정 일자를 기준으로 매월,매일,매년을 조회합니다."

    @require_korean_alias
    def g3202(
        self,
        body: G3202InBlock,
        header: Optional[G3202RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        LS openAPI의 g3202 차트TICK 조회합니다.

        Args:
            body (G3202InBlock): 차트TICK 조회를 위한 입력 데이터입니다.
            header (Optional[G3202RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrG3202: 차트TICK 조회를 위한 TrG3202 인스턴스
        """
        request_data = G3202Request(
            body={
                "g3202InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrG3202(request_data)

    차트N틱조회 = g3202
    차트N틱조회.__doc__ = "특정 일자를 기준으로 TICK을 조회합니다."

    @require_korean_alias
    def g3203(
        self,
        body: G3203InBlock,
        header: Optional[G3203RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        LS openAPI의 g3203 차트MIN 조회합니다.

        Args:
            body (G3203InBlock): 차트MIN 조회를 위한 입력 데이터입니다.
            header (Optional[G3203RequestHeader]): 요청 헤더 데이터 블록
            options (Optional[SetupOptions]): 설정 옵션

        Returns:
            TrG3203: 차트MIN 조회를 위한 TrG3103 인스턴스
        """
        request_data = G3203Request(
            body={
                "g3203InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrG3203(request_data)

    차트N분조회 = g3203
    차트N분조회.__doc__ = "특정 일자를 기준으로 MIN을 조회"

    @require_korean_alias
    def g3204(
        self,
        body: G3204InBlock,
        header: Optional[G3204RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ):
        """
        LS openAPI의 g3204 차트일주월년별 조회합니다.

        Args:
            body (G3204InBlock): 차트 조회를 위한 입력 데이터입니다.

        Returns:
            TrG3204: 차트 조회를 위한 TrG3204 인스턴스
        """
        request_data = G3204Request(
            body={
                "g3204InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrG3204(request_data)

    차트일주월년별조회 = g3204
    차트일주월년별조회.__doc__ = "특정 일자를 기준으로 일주월년별을 조회합니다."


__init__ = [
    Chart,
    TrG3103,
    G3103InBlock,
    G3103Request,
    TrG3202,
    G3202InBlock,
    G3202Request,
    TrG3203,
    G3203InBlock,
    G3203Request,
    TrG3204,
    G3204InBlock,
    G3204Request
]
