"""
해외선물 Extension 데이터 모델

손익 계산, 보유종목, 예수금, 미체결 주문을 위한 Pydantic 모델입니다.
"""

from decimal import Decimal
from typing import Dict, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class FuturesTradeInput(BaseModel):
    """해외선물 거래 입력 모델"""
    
    symbol: str = Field(..., description="종목코드")
    """종목코드"""
    
    buy_price: Decimal = Field(..., description="매수가")
    """매수가"""
    
    sell_price: Decimal = Field(..., description="매도가")
    """매도가"""
    
    qty: int = Field(..., description="계약수")
    """계약수"""
    
    is_long: bool = Field(default=True, description="True: 매수 포지션, False: 매도 포지션")
    """True: 매수 포지션, False: 매도 포지션"""
    
    custom_fee_usd: Optional[Decimal] = Field(default=None, description="계약당 수수료 (None이면 Safety Margin 적용)")
    """계약당 수수료 (None이면 Safety Margin 적용)"""
    
    manual_tick_size: Optional[Decimal] = Field(default=None, description="직접 입력 Tick Size")
    """직접 입력 Tick Size"""
    
    manual_tick_value: Optional[Decimal] = Field(default=None, description="직접 입력 Tick Value")
    """직접 입력 Tick Value"""

    manual_currency: str = Field(default="USD", description="Currency of manual tick values in the legacy USD estimator.")
    
    exchange_rate: Optional[Decimal] = Field(default=None, description="환율 (None이면 기본값 사용)")
    """환율 (None이면 기본값 사용)"""
    
    apply_slippage: bool = Field(default=False, description="슬리피지 1틱 차감 여부")
    """슬리피지 1틱 차감 여부"""


class FuturesPnLResult(BaseModel):
    """해외선물 손익 결과 모델"""
    
    total_ticks: Decimal = Field(..., description="획득한 총 틱 수")
    """획득한 총 틱 수"""
    
    gross_pl_usd: Decimal = Field(..., description="수수료 차감 전 손익 ($)")
    """수수료 차감 전 손익 ($)"""
    
    net_pl_usd: Decimal = Field(..., description="수수료 차감 후 손익 ($)")
    """수수료 차감 후 손익 ($)"""
    
    net_pl_krw: Decimal = Field(..., description="원화 환산 손익")
    """원화 환산 손익"""
    
    total_fees_usd: Decimal = Field(..., description="총 수수료 ($)")
    """총 수수료 ($)"""
    
    slippage_cost_usd: Decimal = Field(default=Decimal("0"), description="슬리피지 비용 ($)")
    """슬리피지 비용 ($)"""
    
    estimated_tax_krw: Decimal = Field(default=Decimal("0"), description="예상 양도소득세 (원화)")
    """예상 양도소득세 (원화)"""
    
    tick_size_used: Decimal = Field(..., description="적용된 Tick Size")
    """적용된 Tick Size"""
    
    tick_value_used: Decimal = Field(..., description="적용된 Tick Value")
    """적용된 Tick Value"""
    
    exchange_rate_used: Decimal = Field(..., description="적용 환율")
    """적용 환율"""
    
    is_safety_margin_applied: bool = Field(default=False, description="안전마진 적용 여부")
    """안전마진 적용 여부"""


NativePnLBasis = Literal["estimated_gross_price_change"]
PnLAvailability = Literal["available", "unavailable"]


class FuturesNativePnLResult(BaseModel):
    """Native-currency gross price-change estimate; excludes fees, tax and FX."""

    amount: Decimal
    currency: str
    basis: NativePnLBasis = "estimated_gross_price_change"
    total_ticks: Decimal
    tick_size_used: Decimal
    tick_value_used: Decimal


class FuturesPositionItem(BaseModel):
    """해외선물 보유종목(미결제약정) 모델"""
    
    symbol: str = Field(..., description="종목코드")
    """종목코드"""
    
    symbol_name: str = Field(default="", description="종목명")
    """종목명"""
    
    is_long: bool = Field(default=True, description="True: 매수, False: 매도")
    """True: 매수, False: 매도"""
    
    quantity: int = Field(default=0, description="잔고수량")
    """잔고수량"""
    
    entry_price: Decimal = Field(default=Decimal("0"), description="매입가격")
    """매입가격"""
    
    current_price: Decimal = Field(default=Decimal("0"), description="현재가")
    """현재가"""
    
    pnl_amount: Optional[Decimal] = Field(default=None, description="Native gross price-change estimate; see pnl_currency, pnl_basis and pnl_status.")
    pnl_currency: Optional[str] = None
    pnl_basis: Optional[NativePnLBasis] = None
    pnl_status: PnLAvailability = "unavailable"
    pnl_unavailable_reason: Optional[str] = None
    broker_pnl_amount: Optional[Decimal] = Field(default=None, description="Unmodified broker-reported amount; its monetary unit and cost basis remain unconfirmed.")
    broker_pnl_basis: Literal["broker_reported_unconfirmed"] = "broker_reported_unconfirmed"
    
    pnl_rate: Decimal = Field(default=Decimal("0"), description="Nominal quoted-price change (%), not account-equity return.")
    """손익률 (%)"""
    
    opening_margin: Decimal = Field(default=Decimal("0"), description="개시증거금")
    """개시증거금"""
    
    maintenance_margin: Decimal = Field(default=Decimal("0"), description="유지증거금")
    """유지증거금"""
    
    margin_call_rate: Decimal = Field(default=Decimal("0"), description="마진콜율")
    """마진콜율"""
    
    currency: str = Field(default="", description="Observed position currency code; not proof of the broker PnL amount's unit.")
    """통화"""
    
    exchange_code: str = Field(default="", description="거래소코드")
    """거래소코드"""
    
    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트 시간")
    """마지막 업데이트 시간"""
    
    # Retained for legacy consumers; the account tracker no longer fills this
    # standalone USD estimator slot with a value in an unverified native unit.
    realtime_pnl: Optional[FuturesPnLResult] = Field(default=None, description="Legacy USD estimator result; not populated by native account tracking.")


class FuturesBalanceInfo(BaseModel):
    """해외선물 예수금/증거금 정보 모델"""
    
    deposit: Decimal = Field(default=Decimal("0"), description="해외선물예수금")
    """해외선물예수금"""
    
    total_margin: Decimal = Field(default=Decimal("0"), description="위탁증거금")
    """위탁증거금"""
    
    orderable_amount: Decimal = Field(default=Decimal("0"), description="주문가능금액")
    """주문가능금액"""
    
    withdrawable_amount: Decimal = Field(default=Decimal("0"), description="인출가능금액")
    """인출가능금액"""
    
    pnl_amount: Decimal = Field(default=Decimal("0"), description="평가손익")
    """평가손익"""
    
    realized_pnl: Decimal = Field(default=Decimal("0"), description="실현손익")
    """실현손익"""
    
    currency: str = Field(default="USD", description="통화")
    """통화"""
    
    exchange_rate: Decimal = Field(default=Decimal("0"), description="기준환율")
    """기준환율"""
    
    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트 시간")
    """마지막 업데이트 시간"""


class FuturesOpenOrder(BaseModel):
    """해외선물 미체결 주문 모델"""
    
    order_no: str = Field(..., description="주문번호")
    """주문번호"""
    
    symbol: str = Field(..., description="종목코드")
    """종목코드"""
    
    symbol_name: str = Field(default="", description="종목명")
    """종목명"""
    
    exchange_code: str = Field(default="", description="거래소코드")
    """거래소코드 (HKEX, CME 등)"""
    
    is_long: bool = Field(default=True, description="True: 매수, False: 매도")
    """True: 매수, False: 매도"""
    
    order_type: str = Field(default="", description="주문유형 (1: 시장가, 2: 지정가)")
    """주문유형 (1: 시장가, 2: 지정가)"""
    
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
    
    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트 시간")
    """마지막 업데이트 시간"""


class FuturesCurrencyPnL(BaseModel):
    """Subtotal of available compatible estimates, not an equity valuation."""

    currency: str
    basis: NativePnLBasis = "estimated_gross_price_change"
    total_pnl_amount: Decimal
    position_count: int


class AccountPnLInfo(BaseModel):
    """Compatible native estimates and availability, not account accounting."""
    
    account_pnl_rate: Optional[Decimal] = Field(default=None, description="Unavailable without a confirmed account-return denominator.")
    """계좌 총 수익률 (%)"""
    
    total_eval_amount: Optional[Decimal] = Field(default=None, description="Unavailable without a confirmed valuation and currency basis.")
    """총 평가금액"""
    
    total_margin_used: Optional[Decimal] = Field(default=None, description="Unavailable without confirmed margin units; raw position margins are retained separately.")
    """총 사용 증거금"""
    
    total_pnl_amount: Optional[Decimal] = Field(default=None, description="Single-currency native gross subtotal, only when all positions have compatible available estimates.")
    """총 평가손익"""
    
    position_count: int = Field(default=0, description="보유 포지션 수")
    """보유 포지션 수"""
    
    currency: Optional[str] = None
    """통화"""

    pnl_status: PnLAvailability = "unavailable"
    pnl_basis: Optional[NativePnLBasis] = None
    pnl_unavailable_reason: Optional[str] = None
    pnl_by_currency: Dict[str, FuturesCurrencyPnL] = Field(default_factory=dict)
    unavailable_position_count: int = 0
    
    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트 시간")
    """마지막 업데이트 시간"""
