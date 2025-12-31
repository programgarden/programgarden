"""
해외주식 Extension 데이터 모델

손익 계산, 보유종목, 예수금, 미체결 주문을 위한 Pydantic 모델입니다.
"""

from decimal import Decimal
from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class CommissionConfig(BaseModel):
    """통화별 수수료/세금 설정"""
    
    commission_rates: Dict[str, Decimal] = Field(
        default_factory=lambda: {"DEFAULT": Decimal("0.0025")},
        description="통화코드별 수수료율 (예: {'USD': 0.0025, 'DEFAULT': 0.0025})"
    )
    """통화코드별 수수료율"""
    
    tax_rates: Dict[str, Decimal] = Field(
        default_factory=lambda: {"DEFAULT": Decimal("0")},
        description="통화코드별 거래세율 (예: {'HK': 0.001, 'DEFAULT': 0})"
    )
    """통화코드별 거래세율"""
    
    def get_commission_rate(self, currency: str) -> Decimal:
        """통화코드에 해당하는 수수료율 반환"""
        return self.commission_rates.get(currency, self.commission_rates.get("DEFAULT", Decimal("0.0025")))
    
    def get_tax_rate(self, currency: str) -> Decimal:
        """통화코드에 해당하는 거래세율 반환"""
        return self.tax_rates.get(currency, self.tax_rates.get("DEFAULT", Decimal("0")))


class StockTradeInput(BaseModel):
    """해외주식 거래 입력 모델"""
    
    ticker: str = Field(..., description="종목코드")
    """종목코드"""
    
    qty: int = Field(..., description="수량")
    """수량"""
    
    buy_price: Decimal = Field(..., description="매수단가 (외화)")
    """매수단가 (외화)"""
    
    sell_price: Decimal = Field(..., description="매도단가 (외화)")
    """매도단가 (외화)"""
    
    currency: str = Field(default="USD", description="통화코드")
    """통화코드"""
    
    country: str = Field(default="US", description="국가코드")
    """국가코드"""
    
    exchange_rate: Optional[Decimal] = Field(default=None, description="환율 (None이면 기본값 사용)")
    """환율 (None이면 기본값 사용)"""
    
    fee_rate: Optional[Decimal] = Field(default=None, description="수수료율 (None이면 0.25%)")
    """수수료율 (None이면 0.25%)"""
    
    transaction_tax_rate: Optional[Decimal] = Field(default=None, description="거래세율")
    """거래세율"""


class StockPnLResult(BaseModel):
    """해외주식 손익 결과 모델"""
    
    gross_profit_foreign: Decimal = Field(..., description="세전 손익 (외화)")
    """세전 손익 (외화)"""
    
    net_profit_foreign: Decimal = Field(..., description="세후 손익 (외화)")
    """세후 손익 (외화)"""
    
    net_profit_krw: Decimal = Field(..., description="세후 손익 (원화)")
    """세후 손익 (원화)"""
    
    total_fee_foreign: Decimal = Field(..., description="총 수수료+제세금 (외화)")
    """총 수수료+제세금 (외화)"""
    
    buy_fee: Decimal = Field(..., description="매수 수수료")
    """매수 수수료"""
    
    sell_fee: Decimal = Field(..., description="매도 수수료")
    """매도 수수료"""
    
    sec_fee: Decimal = Field(default=Decimal("0"), description="SEC Fee (미국만)")
    """SEC Fee (미국만)"""
    
    taf_fee: Decimal = Field(default=Decimal("0"), description="TAF Fee (미국만)")
    """TAF Fee (미국만)"""
    
    transaction_tax: Decimal = Field(default=Decimal("0"), description="거래세")
    """거래세"""
    
    return_rate_percent: Decimal = Field(..., description="수익률 (%)")
    """수익률 (%)"""
    
    exchange_rate_used: Decimal = Field(..., description="적용 환율")
    """적용 환율"""
    
    is_safety_margin_applied: bool = Field(default=False, description="안전마진 적용 여부")
    """안전마진 적용 여부"""


class StockPositionItem(BaseModel):
    """해외주식 보유종목 모델"""
    
    symbol: str = Field(..., description="종목코드")
    """종목코드"""
    
    symbol_name: str = Field(default="", description="종목명")
    """종목명"""
    
    currency_code: str = Field(default="USD", description="통화코드")
    """통화코드"""
    
    quantity: int = Field(default=0, description="보유수량")
    """보유수량"""
    
    sellable_quantity: int = Field(default=0, description="매도가능수량")
    """매도가능수량"""
    
    buy_price: Decimal = Field(default=Decimal("0"), description="매입단가")
    """매입단가"""
    
    current_price: Decimal = Field(default=Decimal("0"), description="현재가")
    """현재가"""
    
    buy_amount: Decimal = Field(default=Decimal("0"), description="매입금액 (외화)")
    """매입금액 (외화)"""
    
    eval_amount: Decimal = Field(default=Decimal("0"), description="평가금액 (외화)")
    """평가금액 (외화)"""
    
    pnl_amount: Decimal = Field(default=Decimal("0"), description="평가손익 (외화)")
    """평가손익 (외화)"""
    
    pnl_rate: Decimal = Field(default=Decimal("0"), description="손익률 (%)")
    """손익률 (%)"""
    
    exchange_rate: Decimal = Field(default=Decimal("0"), description="기준환율")
    """기준환율"""
    
    market_code: str = Field(default="", description="시장코드")
    """시장코드"""
    
    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트 시간")
    """마지막 업데이트 시간"""
    
    # 실시간 계산된 손익 (수수료/세금 반영)
    realtime_pnl: Optional[StockPnLResult] = Field(default=None, description="실시간 손익 (수수료/세금 반영)")
    """실시간 손익 (수수료/세금 반영)"""


class StockBalanceInfo(BaseModel):
    """해외주식 예수금 정보 모델"""
    
    currency_code: str = Field(default="USD", description="통화코드")
    """통화코드"""
    
    deposit: Decimal = Field(default=Decimal("0"), description="외화예수금")
    """외화예수금"""
    
    orderable_amount: Decimal = Field(default=Decimal("0"), description="주문가능금액")
    """주문가능금액"""
    
    eval_amount: Decimal = Field(default=Decimal("0"), description="평가금액")
    """평가금액"""
    
    pnl_amount: Decimal = Field(default=Decimal("0"), description="평가손익")
    """평가손익"""
    
    pnl_rate: Decimal = Field(default=Decimal("0"), description="손익률 (%)")
    """손익률 (%)"""
    
    exchange_rate: Decimal = Field(default=Decimal("0"), description="기준환율")
    """기준환율"""
    
    deposit_krw: Decimal = Field(default=Decimal("0"), description="원화환산 예수금")
    """원화환산 예수금"""
    
    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트 시간")
    """마지막 업데이트 시간"""


class StockOpenOrder(BaseModel):
    """해외주식 미체결 주문 모델"""
    
    order_no: str = Field(..., description="주문번호")
    """주문번호"""
    
    symbol: str = Field(..., description="종목코드")
    """종목코드"""
    
    symbol_name: str = Field(default="", description="종목명")
    """종목명"""
    
    order_type: str = Field(default="", description="주문유형 (01: 매도, 02: 매수)")
    """주문유형 (01: 매도, 02: 매수)"""
    
    order_qty: int = Field(default=0, description="주문수량")
    """주문수량"""
    
    order_price: Decimal = Field(default=Decimal("0"), description="주문가격")
    """주문가격"""
    
    executed_qty: int = Field(default=0, description="체결수량")
    """체결수량"""
    
    remaining_qty: int = Field(default=0, description="미체결수량")
    """미체결수량"""
    
    order_time: str = Field(default="", description="주문시간")
    """주문시간"""
    
    order_status: str = Field(default="", description="주문상태")
    """주문상태"""
    
    currency_code: str = Field(default="USD", description="통화코드")
    """통화코드"""
    
    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트 시간")
    """마지막 업데이트 시간"""
