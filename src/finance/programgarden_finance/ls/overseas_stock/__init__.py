
from typing import Dict

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias
from programgarden_core.bases import BaseOverseasStock
from programgarden_finance.ls.token_manager import TokenManager

from .accno import Accno
from .chart import Chart
from .market import Market
from .order import Order
from .real import Real


class OverseasStock(BaseOverseasStock):

    _real_instances: Dict[int, "Real"] = {}

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def accno(self) -> Accno:
        return Accno(token_manager=self.token_manager)

    계좌 = accno
    계좌.__doc__ = "계좌 정보를 조회합니다."

    @require_korean_alias
    def chart(self) -> Chart:
        return Chart(token_manager=self.token_manager)

    차트 = chart
    차트.__doc__ = "차트 데이터를 조회합니다."

    @require_korean_alias
    def market(self) -> Market:
        return Market(token_manager=self.token_manager)

    시세 = market
    시세.__doc__ = "시세 데이터를 조회합니다."

    @require_korean_alias
    def order(self):
        return Order(token_manager=self.token_manager)

    주문 = order
    주문.__doc__ = "주문 정보를 조회합니다."

    @require_korean_alias
    def real(
        self,
        reconnect=True,
        recv_timeout=5.0,
        ping_interval=30.0,
        ping_timeout=5.0,
        max_backoff=60.0
    ):
        key = id(self.token_manager)
        cached = OverseasStock._real_instances.get(key)
        if cached is not None:
            return cached
        instance = Real(
            token_manager=self.token_manager,
            reconnect=reconnect,
            recv_timeout=recv_timeout,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            max_backoff=max_backoff
        )
        OverseasStock._real_instances[key] = instance
        return instance

    실시간 = real
    실시간.__doc__ = "실시간 데이터를 조회합니다."

    @classmethod
    def _clear_real_instance(cls, token_manager_id: int):
        cls._real_instances.pop(token_manager_id, None)

    @classmethod
    def _clear_all_real_instances(cls):
        cls._real_instances.clear()


__all__ = [
    OverseasStock,
    Accno,
    Chart,
    Market,
    Order,
    Real
]
