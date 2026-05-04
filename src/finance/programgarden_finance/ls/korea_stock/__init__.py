
from typing import Dict

from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias
from programgarden_finance.ls.token_manager import TokenManager

from .market import Market
from .chart import Chart
from .ranking import Ranking
from .etc import Etc
from .etf import Etf
from .frgr_itt import FrgrItt
from .accno import Accno
from .order import Order
from .sector import Sector
from .investor import Investor
from .program import Program
from .real import Real


class KoreaStock:

    _real_instances: Dict[int, "Real"] = {}

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

    @require_korean_alias
    def etf(self) -> Etf:
        return Etf(token_manager=self.token_manager)

    ETF = etf
    ETF.__doc__ = "ETF 시세/일별추이/구성종목을 조회합니다."

    @require_korean_alias
    def frgr_itt(self) -> FrgrItt:
        return FrgrItt(token_manager=self.token_manager)

    외인기관 = frgr_itt
    외인기관.__doc__ = "외인/기관 종목별 매매동향을 조회합니다."

    @require_korean_alias
    def accno(self) -> Accno:
        return Accno(token_manager=self.token_manager)

    계좌 = accno
    계좌.__doc__ = "계좌 정보(예수금, 주문가능금액, 잔고 등)를 조회합니다."

    @require_korean_alias
    def order(self) -> Order:
        return Order(token_manager=self.token_manager)

    주문 = order
    주문.__doc__ = "주문(매수/매도/정정)을 처리합니다."

    @require_korean_alias
    def sector(self) -> Sector:
        return Sector(token_manager=self.token_manager)

    업종테마 = sector
    업종테마.__doc__ = "업종/테마 현재가, 종목시세, 테마별종목을 조회합니다."

    @require_korean_alias
    def investor(self) -> Investor:
        return Investor(token_manager=self.token_manager)

    투자자 = investor
    투자자.__doc__ = "투자자별 매매 동향(종합, 시간대별, 차트)을 조회합니다."

    @require_korean_alias
    def program(self) -> Program:
        """Return the Program domain client for Korean stock program-trading TRs (``/stock/program``)."""
        return Program(token_manager=self.token_manager)

    프로그램매매 = program
    프로그램매매.__doc__ = (
        "Query Korean stock program-trading flow data — comprehensive "
        "summary (t1631 / 프로그램매매종합조회), time-bucketed trend "
        "(t1632 / 시간대별프로그램매매추이), period trend (t1633 / "
        "기간별프로그램매매추이), per-symbol snapshot (t1636 / "
        "종목별프로그램매매동향), per-symbol time series (t1637 / "
        "종목별프로그램매매추이), and mini snapshot (t1640 / "
        "프로그램매매종합조회미니)."
    )

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
        cached = KoreaStock._real_instances.get(key)
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
        KoreaStock._real_instances[key] = instance
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
    KoreaStock,
    Market,
    Chart,
    Ranking,
    Etc,
    Etf,
    FrgrItt,
    Accno,
    Order,
    Sector,
    Investor,
    Program,
    Real,
]
