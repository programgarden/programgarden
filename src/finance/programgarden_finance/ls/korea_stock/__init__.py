
from typing import Dict

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias
from programgarden_finance.ls.token_manager import TokenManager

from .market import Market
from .chart import Chart
from .ranking import Ranking
from .etc import Etc


class KoreaStock:

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def market(self) -> Market:
        return Market(token_manager=self.token_manager)

    시세 = market
    시세.__doc__ = "시세 데이터를 조회합니다."

    @require_korean_alias
    def chart(self) -> Chart:
        return Chart(token_manager=self.token_manager)

    차트 = chart
    차트.__doc__ = "차트 데이터를 조회합니다."

    @require_korean_alias
    def ranking(self) -> Ranking:
        return Ranking(token_manager=self.token_manager)

    순위 = ranking
    순위.__doc__ = "순위(상위종목) 데이터를 조회합니다."

    @require_korean_alias
    def etc(self) -> Etc:
        return Etc(token_manager=self.token_manager)

    기타 = etc
    기타.__doc__ = "기타 종목 정보(신규상장, 관리종목 등)를 조회합니다."


__all__ = [
    KoreaStock,
    Market,
    Chart,
    Ranking,
    Etc,
]
