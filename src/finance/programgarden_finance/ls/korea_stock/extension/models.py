"""
국내주식 Extension 데이터 모델

손익 계산, 보유종목, 예수금, 미체결 주문을 위한 Pydantic 모델입니다.
해외주식과 달리 KRW 단일통화, 정수 가격, KOSPI/KOSDAQ 시장구분을 사용합니다.
"""

from decimal import Decimal
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class KrCommissionConfig(BaseModel):
    """국내주식 수수료/세금 설정"""

    commission_rate: Decimal = Field(
        default=Decimal("0.00015"),
        description="수수료율 (기본 0.015%, MTS/HTS/API)"
    )
    """수수료율 (기본 0.015%)"""

    # 증권거래세 (법정, 매도 시에만)
    kospi_tax_rate: Decimal = Field(
        default=Decimal("0.0003"),
        description="KOSPI 증권거래세율 (0.03%)"
    )
    """KOSPI 증권거래세율 (0.03%)"""

    kospi_rural_tax_rate: Decimal = Field(
        default=Decimal("0.0015"),
        description="KOSPI 농어촌특별세율 (0.15%)"
    )
    """KOSPI 농어촌특별세율 (0.15%)"""

    kosdaq_tax_rate: Decimal = Field(
        default=Decimal("0.0018"),
        description="KOSDAQ 증권거래세율 (0.18%)"
    )
    """KOSDAQ 증권거래세율 (0.18%)"""

    kosdaq_rural_tax_rate: Decimal = Field(
        default=Decimal("0"),
        description="KOSDAQ 농어촌특별세율 (없음)"
    )
    """KOSDAQ 농어촌특별세율 (없음)"""

    def get_sell_tax_rate(self, market: str) -> Decimal:
        """시장구분에 따른 매도 시 총 세금률 반환 (거래세 + 농특세)"""
        if market in ("1", "10", "KOSPI"):
            return self.kospi_tax_rate + self.kospi_rural_tax_rate
        elif market in ("2", "20", "KOSDAQ"):
            return self.kosdaq_tax_rate + self.kosdaq_rural_tax_rate
        # 기타 시장은 KOSDAQ 세율 적용
        return self.kosdaq_tax_rate


class KrStockTradeInput(BaseModel):
    """국내주식 거래 입력 모델"""

    ticker: str = Field(..., description="종목코드 (6자리, 예: '005930')")
    """종목코드"""

    qty: int = Field(..., description="수량")
    """수량"""

    buy_price: int = Field(..., description="매수단가 (원)")
    """매수단가 (원)"""

    sell_price: int = Field(..., description="매도단가 (원)")
    """매도단가 (원)"""

    market: str = Field(default="KOSPI", description="시장구분 (KOSPI/KOSDAQ)")
    """시장구분"""

    fee_rate: Optional[Decimal] = Field(default=None, description="수수료율 (None이면 0.015%)")
    """수수료율 (None이면 0.015%)"""


class KrStockPnLResult(BaseModel):
    """국내주식 손익 결과 모델"""

    gross_profit: int = Field(..., description="세전 손익 (원)")
    """세전 손익 (원)"""

    net_profit: int = Field(..., description="세후 손익 (원, 수수료+세금 차감)")
    """세후 손익 (원)"""

    total_fee: int = Field(..., description="총 수수료+제세금 (원)")
    """총 수수료+제세금 (원)"""

    buy_fee: int = Field(..., description="매수 수수료 (원)")
    """매수 수수료 (원)"""

    sell_fee: int = Field(..., description="매도 수수료 (원)")
    """매도 수수료 (원)"""

    transaction_tax: int = Field(default=0, description="증권거래세 (원)")
    """증권거래세 (원)"""

    rural_tax: int = Field(default=0, description="농어촌특별세 (원)")
    """농어촌특별세 (원)"""

    return_rate_percent: Decimal = Field(..., description="수익률 (%)")
    """수익률 (%)"""

    market: str = Field(default="KOSPI", description="시장구분")
    """시장구분"""


class KrStockPositionItem(BaseModel):
    """국내주식 보유종목 모델"""

    symbol: str = Field(..., description="종목코드 (6자리)")
    """종목코드"""

    symbol_name: str = Field(default="", description="종목명")
    """종목명"""

    quantity: int = Field(default=0, description="보유수량")
    """보유수량"""

    sellable_quantity: int = Field(default=0, description="매도가능수량")
    """매도가능수량"""

    buy_price: int = Field(default=0, description="매입단가 (원)")
    """매입단가 (원)"""

    current_price: int = Field(default=0, description="현재가 (원)")
    """현재가 (원)"""

    buy_amount: int = Field(default=0, description="매입금액 (원)")
    """매입금액 (원)"""

    eval_amount: int = Field(default=0, description="평가금액 (원)")
    """평가금액 (원)"""

    pnl_amount: int = Field(default=0, description="평가손익 (원)")
    """평가손익 (원)"""

    pnl_rate: float = Field(default=0.0, description="손익률 (%)")
    """손익률 (%)"""

    market: str = Field(default="", description="시장구분 (1:KOSPI, 2:KOSDAQ)")
    """시장구분"""

    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트 시간")
    """마지막 업데이트 시간"""

    realtime_pnl: Optional[KrStockPnLResult] = Field(default=None, description="실시간 손익 (수수료/세금 반영)")
    """실시간 손익 (수수료/세금 반영)"""


class KrStockBalanceInfo(BaseModel):
    """국내주식 예수금 정보 모델"""

    deposit: int = Field(default=0, description="예수금 (원)")
    """예수금 (원)"""

    d1_deposit: int = Field(default=0, description="D1예수금 (원)")
    """D1예수금 (원)"""

    d2_deposit: int = Field(default=0, description="D2예수금 (원)")
    """D2예수금 (원)"""

    orderable_amount: int = Field(default=0, description="현금주문가능금액 (원)")
    """현금주문가능금액 (원)"""

    substitute_amount: int = Field(default=0, description="대용금액 (원)")
    """대용금액 (원)"""

    margin_cash: int = Field(default=0, description="증거금현금 (원)")
    """증거금현금 (원)"""

    receivable_amount: int = Field(default=0, description="미수금액 (원)")
    """미수금액 (원)"""

    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트 시간")
    """마지막 업데이트 시간"""


class KrStockOpenOrder(BaseModel):
    """국내주식 미체결 주문 모델"""

    order_no: int = Field(..., description="주문번호")
    """주문번호"""

    symbol: str = Field(..., description="종목코드")
    """종목코드"""

    order_type: str = Field(default="", description="매매구분 (매도/매수)")
    """매매구분"""

    order_qty: int = Field(default=0, description="주문수량")
    """주문수량"""

    order_price: int = Field(default=0, description="주문가격 (원)")
    """주문가격 (원)"""

    executed_qty: int = Field(default=0, description="체결수량")
    """체결수량"""

    executed_price: int = Field(default=0, description="체결가격 (원)")
    """체결가격 (원)"""

    remaining_qty: int = Field(default=0, description="미체결잔량")
    """미체결잔량"""

    order_time: str = Field(default="", description="주문시간")
    """주문시간"""

    order_status: str = Field(default="", description="주문상태")
    """주문상태"""

    order_method: str = Field(default="", description="호가유형")
    """호가유형"""

    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트 시간")
    """마지막 업데이트 시간"""


class KrAccountPnLInfo(BaseModel):
    """국내주식 계좌 전체 수익률 정보"""

    account_pnl_rate: Decimal = Field(default=Decimal("0"), description="계좌 수익률 (%)")
    """계좌 수익률 (%)"""
    total_eval_amount: int = Field(default=0, description="총 평가금액 (원)")
    """총 평가금액 (원)"""
    total_buy_amount: int = Field(default=0, description="총 매입금액 (원)")
    """총 매입금액 (원)"""
    total_pnl_amount: int = Field(default=0, description="총 평가손익 (원)")
    """총 평가손익 (원)"""
    realized_pnl: int = Field(default=0, description="실현손익 (원)")
    """실현손익 (원)"""
    estimated_asset: int = Field(default=0, description="추정순자산 (원)")
    """추정순자산 (원)"""
    position_count: int = Field(default=0, description="보유종목 수")
    """보유종목 수"""
    last_updated: Optional[datetime] = Field(default=None, description="마지막 업데이트")
    """마지막 업데이트"""
