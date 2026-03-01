
from typing import Optional
from programgarden_finance.ls.tr_base import set_tr_header_options
from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager
from . import t1702
from .t1702 import TrT1702
from .t1702.blocks import T1702InBlock, T1702Request, T1702RequestHeader

from programgarden_core.korea_alias import require_korean_alias


class FrgrItt:
    """
    국내 주식 외인/기관 동향을 조회하는 FrgrItt 클래스입니다.

    외인, 기관 종목별 매매동향 조회 TR을 제공합니다.
    API 엔드포인트: /stock/frgr-itt
    """

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def t1702(
        self,
        body: T1702InBlock,
        header: Optional[T1702RequestHeader] = None,
        options: Optional[SetupOptions] = None,
    ) -> TrT1702:
        """
        LS openAPI의 t1702 외인기관종목별동향을(를) 조회합니다.
        """

        request_data = T1702Request(
            body={
                "t1702InBlock": body
            },
        )
        set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )

        return TrT1702(request_data)

    외인기관종목별동향 = t1702
    외인기관종목별동향.__doc__ = "외인, 기관 종목별 매매동향을 조회합니다."


__all__ = [
    FrgrItt,
    t1702,
]
