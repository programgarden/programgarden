from programgarden_finance.ls.overseas_futureoption.real import Real
from programgarden_finance.ls.token_manager import TokenManager
from .market import Market
from .accno import Accno
from .chart import Chart
from .order import Order
from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class OverseasFutureoption(metaclass=EnforceKoreanAliasMeta):

    def __init__(self, token_manager: TokenManager):
        if not token_manager:
            raise ValueError("token_manager is required")
        self.token_manager = token_manager

    @require_korean_alias
    def market(self) -> Market:
        return Market(self.token_manager)

    선물옵션시세 = market
    선물옵션시세.__doc__ = "해외선물옵션 시세 데이터를 조회합니다."

    @require_korean_alias
    def accno(self) -> Accno:
        return Accno(self.token_manager)

    선물옵션계좌 = accno
    선물옵션계좌.__doc__ = "해외선물옵션 계좌 정보를 조회합니다."

    @require_korean_alias
    def chart(self) -> Chart:
        return Chart(self.token_manager)

    선물옵션차트 = chart
    선물옵션차트.__doc__ = "해외선물옵션 차트 정보를 조회합니다."

    @require_korean_alias
    def order(self) -> Order:
        return Order(self.token_manager)

    선물옵션주문 = order
    선물옵션주문.__doc__ = "해외선물옵션 주문 정보를 조회합니다."

    @require_korean_alias
    def real(
        self,
        reconnect=True,
        recv_timeout=5.0,
        ping_interval=30.0,
        ping_timeout=5.0,
        max_backoff=60.0
    ):
        return Real(
            token_manager=self.token_manager,
            reconnect=reconnect,
            recv_timeout=recv_timeout,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            max_backoff=max_backoff
        )

    실시간 = real
    실시간.__doc__ = "실시간 데이터를 조회합니다."


__all__ = [
    OverseasFutureoption,
    Market,
    Accno,
    Order,
]
