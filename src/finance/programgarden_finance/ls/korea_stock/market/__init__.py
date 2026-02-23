
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t9945
from .t9945 import TrT9945
from .t9945.blocks import T9945InBlock, T9945Request, T9945RequestHeader

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class Market:
    """
    국내 주식 시세를 조회하는 Market 클래스입니다.
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t9945(
        self,
        body: T9945InBlock,
        header: Optional[T9945RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT9945:
        """
        LS openAPI의 t9945 주식마스터조회API용을 조회합니다.

        Args:
            body (T9945InBlock): 조회를 위한 입력 데이터입니다.
            header (Optional[T9945RequestHeader]): 요청 헤더 정보입니다.
            options (Optional[SetupOptions]): 추가 설정 옵션입니다.

        Returns:
            TrT9945: 조회를 위한 TrT9945 인스턴스
        """

        request_data = T9945Request(
            body={
                "t9945InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT9945(request_data)

    주식마스터조회 = t9945
    주식마스터조회.__doc__ = "주식마스터를 조회합니다."


__init__ = [
    Market,
    t9945,
]
