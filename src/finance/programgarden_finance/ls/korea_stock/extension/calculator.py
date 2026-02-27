"""
국내주식 손익 계산기

수수료(0.015%), 증권거래세, 농어촌특별세를 반영한 정확한 손익 계산을 제공합니다.
원화(KRW) 정수 기반으로 계산합니다.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from .models import KrStockTradeInput, KrStockPnLResult, KrCommissionConfig

# ===== 상수 정의 =====
DEFAULT_COMMISSION_RATE = Decimal("0.00015")  # 기본 수수료 0.015%

# 증권거래세 (법정세율, 2025년 기준)
KOSPI_TAX_RATE = Decimal("0.0003")       # KOSPI 증권거래세 0.03%
KOSPI_RURAL_TAX_RATE = Decimal("0.0015") # KOSPI 농어촌특별세 0.15%
KOSDAQ_TAX_RATE = Decimal("0.0018")      # KOSDAQ 증권거래세 0.18%
KOSDAQ_RURAL_TAX_RATE = Decimal("0")     # KOSDAQ 농어촌특별세 없음


def _is_kospi(market: str) -> bool:
    """KOSPI 시장 여부 판별"""
    return market in ("1", "10", "KOSPI")


def calculate_kr_stock_pnl(
    trade: KrStockTradeInput,
    commission_config: Optional[KrCommissionConfig] = None
) -> KrStockPnLResult:
    """
    국내주식 손익 계산

    Args:
        trade: 거래 입력 데이터
        commission_config: 수수료/세금 설정 (None이면 기본값 사용)

    Returns:
        KrStockPnLResult: 손익 계산 결과
    """
    if commission_config is None:
        commission_config = KrCommissionConfig()

    # 1. 수수료율 결정
    fee_rate = trade.fee_rate if trade.fee_rate is not None else commission_config.commission_rate

    # 2. 매수/매도 금액 계산
    buy_amount = trade.buy_price * trade.qty
    sell_amount = trade.sell_price * trade.qty

    # 3. 수수료 계산 (매수/매도 각각)
    buy_fee = int((Decimal(str(buy_amount)) * fee_rate).quantize(Decimal("1"), ROUND_HALF_UP))
    sell_fee = int((Decimal(str(sell_amount)) * fee_rate).quantize(Decimal("1"), ROUND_HALF_UP))

    # 4. 거래세 + 농특세 계산 (매도 시에만)
    if _is_kospi(trade.market):
        tax_rate = commission_config.kospi_tax_rate
        rural_rate = commission_config.kospi_rural_tax_rate
    else:
        tax_rate = commission_config.kosdaq_tax_rate
        rural_rate = commission_config.kosdaq_rural_tax_rate

    transaction_tax = int((Decimal(str(sell_amount)) * tax_rate).quantize(Decimal("1"), ROUND_HALF_UP))
    rural_tax = int((Decimal(str(sell_amount)) * rural_rate).quantize(Decimal("1"), ROUND_HALF_UP))

    # 5. 손익 계산
    gross_profit = sell_amount - buy_amount
    total_fee = buy_fee + sell_fee + transaction_tax + rural_tax
    net_profit = gross_profit - total_fee

    # 6. 수익률 계산
    total_cost = buy_amount + buy_fee
    if total_cost > 0:
        return_rate = (Decimal(str(net_profit)) / Decimal(str(total_cost)) * 100).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
    else:
        return_rate = Decimal("0")

    return KrStockPnLResult(
        gross_profit=gross_profit,
        net_profit=net_profit,
        total_fee=total_fee,
        buy_fee=buy_fee,
        sell_fee=sell_fee,
        transaction_tax=transaction_tax,
        rural_tax=rural_tax,
        return_rate_percent=return_rate,
        market=trade.market,
    )


class KrStockPnLCalculator:
    """
    국내주식 손익 계산기 클래스

    수수료/세금 설정을 관리하며 손익 계산을 수행합니다.
    """

    def __init__(self, commission_config: Optional[KrCommissionConfig] = None):
        self._config = commission_config or KrCommissionConfig()

    @property
    def commission_config(self) -> KrCommissionConfig:
        """현재 수수료/세금 설정"""
        return self._config

    def update_config(self, commission_config: KrCommissionConfig):
        """수수료/세금 설정 업데이트"""
        self._config = commission_config

    def calculate(self, trade: KrStockTradeInput) -> KrStockPnLResult:
        """손익 계산"""
        return calculate_kr_stock_pnl(trade, self._config)

    def calculate_realtime_pnl(
        self,
        symbol: str,
        quantity: int,
        buy_price: int,
        current_price: int,
        market: str = "KOSPI",
    ) -> KrStockPnLResult:
        """
        실시간 손익 계산 (보유 중인 종목)

        Args:
            symbol: 종목코드
            quantity: 보유수량
            buy_price: 매입단가 (원)
            current_price: 현재가 (원)
            market: 시장구분 (KOSPI/KOSDAQ 또는 1/2)
        """
        trade = KrStockTradeInput(
            ticker=symbol,
            qty=quantity,
            buy_price=buy_price,
            sell_price=current_price,
            market=market,
            fee_rate=self._config.commission_rate,
        )
        return calculate_kr_stock_pnl(trade, self._config)
