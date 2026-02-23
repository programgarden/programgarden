from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t8451
from .t8451 import TrT8451
from .t8451.blocks import T8451InBlock, T8451Request, T8451RequestHeader

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


__init__ = [
    Chart,
    t8451,
]
