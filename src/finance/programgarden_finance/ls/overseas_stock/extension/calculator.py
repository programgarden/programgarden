"""
해외주식 손익 계산기

SEC Fee, TAF, 국가별 거래세를 반영한 정확한 손익 계산을 제공합니다.
Safety Margin 개념을 적용하여 비용을 보수적으로 책정합니다.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional

from .models import StockTradeInput, StockPnLResult, CommissionConfig

# ===== 상수 정의 =====
DEFAULT_EXCHANGE_RATE = Decimal("1400")  # 기본 환율 (원/달러)
DEFAULT_FEE_RATE = Decimal("0.0025")     # 기본 수수료 0.25%

# 미국 SEC Fee (매도 시에만, 변동 가능)
SEC_FEE_RATE = Decimal("0.000008")  # $8 per $1,000,000
TAF_FEE_PER_SHARE = Decimal("0.000166")  # 주당 $0.000166 (최소 $0.01, 최대 $8.30)

# 국가별 기본 거래세율 (Safety Margin)
COUNTRY_TAX_RATES: Dict[str, Decimal] = {
    "US": Decimal("0"),        # 미국은 SEC/TAF로 대체
    "HK": Decimal("0.001"),    # 홍콩 Stamp Duty 0.1%
    "CN": Decimal("0.001"),    # 중국 0.1%
    "JP": Decimal("0"),        # 일본 없음
    "DEFAULT": Decimal("0.001")  # 기타 0.1% (Safety Margin)
}

# 통화코드 -> 국가코드 매핑
CURRENCY_TO_COUNTRY: Dict[str, str] = {
    "USD": "US",
    "HKD": "HK",
    "CNY": "CN",
    "JPY": "JP",
    "EUR": "EU",
    "GBP": "GB",
}


def get_country_from_currency(currency: str) -> str:
    """통화코드에서 국가코드 추출"""
    return CURRENCY_TO_COUNTRY.get(currency, "US")


def calculate_stock_pnl(
    trade: StockTradeInput,
    commission_config: Optional[CommissionConfig] = None
) -> StockPnLResult:
    """
    해외주식 손익 계산 (Safety Margin 적용)
    
    Args:
        trade: 거래 입력 데이터
        commission_config: 통화별 수수료/세금 설정 (None이면 기본값 사용)
    
    Returns:
        StockPnLResult: 손익 계산 결과
    """
    safety_margin_applied = False
    
    # CommissionConfig 기본값 설정
    if commission_config is None:
        commission_config = CommissionConfig()
    
    # 1. 환율 결정
    exchange_rate = trade.exchange_rate
    if exchange_rate is None:
        exchange_rate = DEFAULT_EXCHANGE_RATE
        safety_margin_applied = True
    
    # 2. 수수료율 결정
    fee_rate = trade.fee_rate
    if fee_rate is None:
        fee_rate = commission_config.get_commission_rate(trade.currency)
        if fee_rate == DEFAULT_FEE_RATE:
            safety_margin_applied = True
    
    # 3. 매수/매도 금액 계산
    qty = Decimal(str(trade.qty))
    buy_price = trade.buy_price
    sell_price = trade.sell_price
    
    buy_amount = buy_price * qty
    sell_amount = sell_price * qty
    
    # 4. 수수료 계산 (매수/매도 각각)
    buy_fee = (buy_amount * fee_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
    sell_fee = (sell_amount * fee_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
    
    # 5. 미국 SEC Fee / TAF (매도 시에만)
    sec_fee = Decimal("0")
    taf_fee = Decimal("0")
    country = trade.country or get_country_from_currency(trade.currency)
    
    if country == "US":
        # SEC Fee: 매도 금액 × 0.000008
        sec_fee = (sell_amount * SEC_FEE_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        # TAF Fee: 주당 $0.000166 (최소 $0.01, 최대 $8.30)
        taf_fee = (TAF_FEE_PER_SHARE * qty).quantize(Decimal("0.01"), ROUND_HALF_UP)
        taf_fee = max(Decimal("0.01"), min(taf_fee, Decimal("8.30")))
    
    # 6. 거래세 계산 (국가별)
    tax_rate = trade.transaction_tax_rate
    if tax_rate is None:
        tax_rate = commission_config.get_tax_rate(trade.currency)
        if tax_rate is None or tax_rate == Decimal("0"):
            tax_rate = COUNTRY_TAX_RATES.get(country, COUNTRY_TAX_RATES["DEFAULT"])
        if tax_rate > 0:
            safety_margin_applied = True
    
    transaction_tax = (sell_amount * tax_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
    
    # 7. 손익 계산
    gross_profit = sell_amount - buy_amount
    total_fees = buy_fee + sell_fee + sec_fee + taf_fee + transaction_tax
    net_profit_foreign = gross_profit - total_fees
    net_profit_krw = (net_profit_foreign * exchange_rate).quantize(Decimal("1"), ROUND_HALF_UP)
    
    # 8. 수익률 계산
    total_cost = buy_amount + buy_fee
    if total_cost > 0:
        return_rate = ((net_profit_foreign / total_cost) * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    else:
        return_rate = Decimal("0")
    
    return StockPnLResult(
        gross_profit_foreign=gross_profit,
        net_profit_foreign=net_profit_foreign,
        net_profit_krw=net_profit_krw,
        total_fee_foreign=total_fees,
        buy_fee=buy_fee,
        sell_fee=sell_fee,
        sec_fee=sec_fee,
        taf_fee=taf_fee,
        transaction_tax=transaction_tax,
        return_rate_percent=return_rate,
        exchange_rate_used=exchange_rate,
        is_safety_margin_applied=safety_margin_applied
    )


class StockPnLCalculator:
    """
    해외주식 손익 계산기 클래스
    
    통화별 수수료/세금 설정을 관리하며 손익 계산을 수행합니다.
    """
    
    def __init__(self, commission_config: Optional[CommissionConfig] = None):
        """
        Args:
            commission_config: 통화별 수수료/세금 설정
        """
        self._config = commission_config or CommissionConfig()
    
    @property
    def commission_config(self) -> CommissionConfig:
        """현재 수수료/세금 설정"""
        return self._config
    
    def update_config(self, commission_config: CommissionConfig):
        """수수료/세금 설정 업데이트"""
        self._config = commission_config
    
    def calculate(self, trade: StockTradeInput) -> StockPnLResult:
        """
        손익 계산
        
        Args:
            trade: 거래 입력 데이터
        
        Returns:
            StockPnLResult: 손익 계산 결과
        """
        return calculate_stock_pnl(trade, self._config)
    
    def calculate_realtime_pnl(
        self,
        symbol: str,
        quantity: int,
        buy_price: Decimal,
        current_price: Decimal,
        currency: str = "USD",
        exchange_rate: Optional[Decimal] = None
    ) -> StockPnLResult:
        """
        실시간 손익 계산 (보유 중인 종목)
        
        Args:
            symbol: 종목코드
            quantity: 보유수량
            buy_price: 매입단가
            current_price: 현재가
            currency: 통화코드
            exchange_rate: 환율 (None이면 기본값 사용)
        
        Returns:
            StockPnLResult: 손익 계산 결과
        """
        trade = StockTradeInput(
            ticker=symbol,
            qty=quantity,
            buy_price=buy_price,
            sell_price=current_price,
            currency=currency,
            country=get_country_from_currency(currency),
            exchange_rate=exchange_rate,
            fee_rate=self._config.get_commission_rate(currency),
            transaction_tax_rate=self._config.get_tax_rate(currency),
        )
        return calculate_stock_pnl(trade, self._config)
