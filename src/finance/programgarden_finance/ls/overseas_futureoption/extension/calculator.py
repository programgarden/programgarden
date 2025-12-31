"""
해외선물 손익 계산기

Tick 기반 정확한 손익 계산을 제공합니다.
Safety Margin 개념을 적용하여 비용을 보수적으로 책정합니다.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from .symbol_spec_manager import SymbolSpecManager, SymbolSpec
from .models import FuturesTradeInput, FuturesPnLResult

# ===== 상수 정의 =====
DEFAULT_EXCHANGE_RATE = Decimal("1400")  # 기본 환율 (원/달러)
DEFAULT_FEE_PER_CONTRACT = Decimal("7.5")  # 편도 $7.5 Safety Margin (왕복 $15)
CAPITAL_GAINS_TAX_RATE = Decimal("0.11")  # 양도소득세 11%


def calculate_futures_pnl(
    trade: FuturesTradeInput,
    spec: Optional[SymbolSpec] = None
) -> FuturesPnLResult:
    """
    해외선물 손익 계산 (Tick 기반, Safety Margin 적용)
    
    Args:
        trade: 거래 입력 데이터
        spec: 종목 명세 (None이면 manual_tick_size/manual_tick_value 필수)
    
    Returns:
        FuturesPnLResult: 손익 계산 결과
    """
    safety_margin_applied = False
    
    # 1. Tick Size/Value 결정
    if trade.manual_tick_size is not None and trade.manual_tick_value is not None:
        tick_size = trade.manual_tick_size
        tick_value = trade.manual_tick_value
        decimal_places = 2
    elif spec:
        tick_size = spec.tick_size
        tick_value = spec.tick_value
        decimal_places = spec.decimal_places
    else:
        raise ValueError(
            f"Symbol spec not provided and manual_tick_size/manual_tick_value not set. "
            f"Provide either spec or manual values."
        )
    
    # 2. 환율 결정
    exchange_rate = trade.exchange_rate
    if exchange_rate is None:
        exchange_rate = DEFAULT_EXCHANGE_RATE
        safety_margin_applied = True
    
    # 3. 수수료 결정 (계약당)
    fee_per_contract = trade.custom_fee_usd
    if fee_per_contract is None:
        fee_per_contract = DEFAULT_FEE_PER_CONTRACT
        safety_margin_applied = True
    
    # 4. 틱 수 계산: (매도가 - 매수가) / Tick Size
    price_diff = trade.sell_price - trade.buy_price
    if not trade.is_long:  # 숏 포지션이면 반대
        price_diff = -price_diff
    
    # 소수점 정밀도 적용
    if decimal_places > 0:
        quantize_str = "0." + "0" * decimal_places
    else:
        quantize_str = "1"
    
    total_ticks = (price_diff / tick_size).quantize(Decimal(quantize_str), ROUND_HALF_UP)
    
    # 5. 손익 계산: 틱 수 × Tick Value × 계약수
    qty = Decimal(str(trade.qty))
    gross_pl = total_ticks * tick_value * qty
    
    # 6. 슬리피지 비용 (Safety Margin 모드에서 옵션)
    slippage_cost = Decimal("0")
    if trade.apply_slippage and safety_margin_applied:
        slippage_cost = tick_value * qty * 2  # 진입/청산 각 1틱
    
    # 7. 수수료 계산 (왕복)
    total_fees = fee_per_contract * qty * 2  # 진입 + 청산
    
    # 8. 순손익
    net_pl_usd = gross_pl - total_fees - slippage_cost
    net_pl_krw = (net_pl_usd * exchange_rate).quantize(Decimal("1"), ROUND_HALF_UP)
    
    # 9. 예상 양도소득세 (수익일 때만, 11%)
    estimated_tax_krw = Decimal("0")
    if net_pl_krw > 0:
        estimated_tax_krw = (net_pl_krw * CAPITAL_GAINS_TAX_RATE).quantize(Decimal("1"), ROUND_HALF_UP)
    
    return FuturesPnLResult(
        total_ticks=total_ticks,
        gross_pl_usd=gross_pl,
        net_pl_usd=net_pl_usd,
        net_pl_krw=net_pl_krw,
        total_fees_usd=total_fees,
        slippage_cost_usd=slippage_cost,
        estimated_tax_krw=estimated_tax_krw,
        tick_size_used=tick_size,
        tick_value_used=tick_value,
        exchange_rate_used=exchange_rate,
        is_safety_margin_applied=safety_margin_applied
    )


class FuturesPnLCalculator:
    """
    해외선물 손익 계산기 클래스
    
    SymbolSpecManager와 연동하여 종목별 정확한 손익 계산을 수행합니다.
    """
    
    def __init__(
        self,
        spec_manager: Optional[SymbolSpecManager] = None,
        default_fee_per_contract: Decimal = DEFAULT_FEE_PER_CONTRACT
    ):
        """
        Args:
            spec_manager: 종목 명세 관리자
            default_fee_per_contract: 기본 계약당 수수료 ($)
        """
        self._spec_manager = spec_manager
        self._default_fee = default_fee_per_contract
    
    @property
    def spec_manager(self) -> Optional[SymbolSpecManager]:
        """종목 명세 관리자"""
        return self._spec_manager
    
    def set_spec_manager(self, spec_manager: SymbolSpecManager):
        """종목 명세 관리자 설정"""
        self._spec_manager = spec_manager
    
    def calculate(self, trade: FuturesTradeInput) -> FuturesPnLResult:
        """
        손익 계산
        
        Args:
            trade: 거래 입력 데이터
        
        Returns:
            FuturesPnLResult: 손익 계산 결과
        """
        spec = None
        if self._spec_manager:
            spec = self._spec_manager.get_spec(trade.symbol)
        
        return calculate_futures_pnl(trade, spec)
    
    def calculate_realtime_pnl(
        self,
        symbol: str,
        quantity: int,
        entry_price: Decimal,
        current_price: Decimal,
        is_long: bool = True,
        exchange_rate: Optional[Decimal] = None,
        custom_fee_usd: Optional[Decimal] = None
    ) -> FuturesPnLResult:
        """
        실시간 손익 계산 (보유 중인 포지션)
        
        Args:
            symbol: 종목코드
            quantity: 보유수량
            entry_price: 진입가격
            current_price: 현재가
            is_long: True: 매수, False: 매도
            exchange_rate: 환율 (None이면 기본값 사용)
            custom_fee_usd: 계약당 수수료 (None이면 기본값 사용)
        
        Returns:
            FuturesPnLResult: 손익 계산 결과
        """
        # 종목 명세 조회
        spec = None
        manual_tick_size = None
        manual_tick_value = None
        
        if self._spec_manager:
            spec = self._spec_manager.get_spec(symbol)
        
        if not spec:
            # spec이 없으면 수동 입력 필요
            raise ValueError(
                f"Symbol '{symbol}' not found in spec_manager. "
                f"Initialize spec_manager first or provide manual_tick_size/manual_tick_value."
            )
        
        trade = FuturesTradeInput(
            symbol=symbol,
            buy_price=entry_price if is_long else current_price,
            sell_price=current_price if is_long else entry_price,
            qty=quantity,
            is_long=is_long,
            custom_fee_usd=custom_fee_usd or self._default_fee,
            exchange_rate=exchange_rate,
            apply_slippage=False
        )
        
        return calculate_futures_pnl(trade, spec)
    
    def get_symbol_spec(self, symbol: str) -> Optional[SymbolSpec]:
        """종목 명세 조회"""
        if self._spec_manager:
            return self._spec_manager.get_spec(symbol)
        return None
