"""Data type adapters for Tracker ↔ TypedDict conversions.

EN:
    Provides adapter functions to convert between finance package Tracker models
    (StockPositionItem, StockBalanceInfo, StockOpenOrder, etc.) and programgarden
    core TypedDict formats (HeldSymbolOverseasStock, NonTradedSymbolOverseasStock, etc.).

KR:
    finance 패키지의 Tracker 모델과 programgarden core의 TypedDict 포맷 간
    변환을 담당하는 어댑터 함수를 제공합니다.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from programgarden_core import (
    HeldSymbolOverseasStock,
    HeldSymbolOverseasFutures,
    NonTradedSymbolOverseasStock,
    NonTradedSymbolOverseasFutures,
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    DpsTyped,
)


def to_float(value: Any) -> float:
    """Decimal/숫자를 float로 변환"""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def to_int(value: Any) -> int:
    """숫자를 int로 변환"""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# ===== 해외주식 어댑터 =====

def adapt_stock_position_to_held(position: Any) -> HeldSymbolOverseasStock:
    """StockPositionItem → HeldSymbolOverseasStock 변환"""
    return HeldSymbolOverseasStock(
        CrcyCode=getattr(position, 'currency_code', 'USD'),
        ShtnIsuNo=getattr(position, 'symbol', ''),
        AstkBalQty=to_int(getattr(position, 'quantity', 0)),
        AstkSellAbleQty=to_int(getattr(position, 'sellable_quantity', 0)),
        PnlRat=to_float(getattr(position, 'pnl_rate', 0)),
        BaseXchrat=to_float(getattr(position, 'exchange_rate', 0)),
        PchsAmt=to_float(getattr(position, 'buy_amount', 0)),
        FcurrMktCode=getattr(position, 'market_code', ''),
    )


def adapt_stock_positions_to_held_list(
    positions: Dict[str, Any]
) -> Tuple[List[HeldSymbolOverseasStock], Set[str]]:
    """보유종목 딕셔너리 → HeldSymbolOverseasStock 리스트 + 종목코드 셋"""
    held_list: List[HeldSymbolOverseasStock] = []
    held_symbols: Set[str] = set()
    
    for symbol, pos in positions.items():
        held_list.append(adapt_stock_position_to_held(pos))
        held_symbols.add(symbol.strip())
    
    return held_list, held_symbols


def adapt_stock_open_order_to_non_traded(order: Any) -> NonTradedSymbolOverseasStock:
    """StockOpenOrder → NonTradedSymbolOverseasStock 변환"""
    return NonTradedSymbolOverseasStock(
        OrdTime=getattr(order, 'order_time', ''),
        OrdNo=to_int(getattr(order, 'order_no', 0)),
        OrgOrdNo=to_int(getattr(order, 'org_order_no', 0)) if hasattr(order, 'org_order_no') else 0,
        ShtnIsuNo=getattr(order, 'symbol', ''),
        MrcAbleQty=to_int(getattr(order, 'remaining_qty', 0)),  # 정정/취소 가능 수량
        OrdQty=to_int(getattr(order, 'order_qty', 0)),
        OvrsOrdPrc=to_float(getattr(order, 'order_price', 0)),
        OrdprcPtnCode=getattr(order, 'order_price_type', '') if hasattr(order, 'order_price_type') else '',
        OrdPtnCode=getattr(order, 'order_type', ''),
        MrcTpCode='',  # 정정구분
        OrdMktCode=getattr(order, 'market_code', '') if hasattr(order, 'market_code') else '',
        UnercQty=to_int(getattr(order, 'remaining_qty', 0)),
        CnfQty=to_int(getattr(order, 'executed_qty', 0)),
        CrcyCode=getattr(order, 'currency_code', 'USD'),
        RegMktCode='',
        IsuNo=getattr(order, 'symbol', ''),
        BnsTpCode=getattr(order, 'order_type', ''),
    )


def adapt_stock_open_orders_to_non_traded_list(
    orders: Dict[str, Any],
    exchcd_filter: Optional[str] = None
) -> Tuple[List[NonTradedSymbolOverseasStock], Set[str]]:
    """미체결 딕셔너리 → NonTradedSymbolOverseasStock 리스트 + 종목코드 셋"""
    non_traded_list: List[NonTradedSymbolOverseasStock] = []
    non_traded_symbols: Set[str] = set()
    
    for order_no, order in orders.items():
        # 거래소 필터링 (있는 경우)
        if exchcd_filter:
            order_market = getattr(order, 'market_code', '') if hasattr(order, 'market_code') else ''
            if order_market and order_market != exchcd_filter:
                continue
        
        non_traded_list.append(adapt_stock_open_order_to_non_traded(order))
        symbol = getattr(order, 'symbol', '').strip()
        if symbol:
            non_traded_symbols.add(symbol)
    
    return non_traded_list, non_traded_symbols


def adapt_stock_balances_to_dps(balances: Dict[str, Any]) -> List[DpsTyped]:
    """예수금 딕셔너리 → DpsTyped 리스트"""
    result: List[DpsTyped] = []
    
    for currency, balance in balances.items():
        result.append({
            "deposit": to_float(getattr(balance, 'deposit', 0)),
            "orderable_amount": to_float(getattr(balance, 'orderable_amount', 0)),
            "currency": currency,
        })
    
    # USD 기본값 보장
    if not result:
        result.append({
            "deposit": 0.0,
            "orderable_amount": 0.0,
            "currency": "USD",
        })
    
    return result


# ===== 해외선물 어댑터 =====

def adapt_futures_position_to_held(position: Any) -> HeldSymbolOverseasFutures:
    """FuturesPositionItem → HeldSymbolOverseasFutures 변환"""
    # is_long (bool) → BnsTpCode ("1": 매도, "2": 매수)
    is_long = getattr(position, 'is_long', True)
    bns_tp_code = "2" if is_long else "1"
    
    return HeldSymbolOverseasFutures(
        IsuCodeVal=getattr(position, 'symbol', ''),
        IsuNm=getattr(position, 'symbol_name', ''),
        BnsTpCode=bns_tp_code,
        BalQty=to_float(getattr(position, 'quantity', 0)),
        OvrsDrvtNowPrc=to_float(getattr(position, 'current_price', 0)),
        AbrdFutsEvalPnlAmt=to_float(getattr(position, 'pnl_amount', 0)),
        PchsPrc=to_float(getattr(position, 'entry_price', 0)),
        MaintMgn=to_float(getattr(position, 'maintenance_margin', 0)),
        CsgnMgn=to_float(getattr(position, 'opening_margin', 0)),
    )


def adapt_futures_positions_to_held_list(
    positions: Dict[str, Any]
) -> Tuple[List[HeldSymbolOverseasFutures], Dict[str, Set[str]]]:
    """보유종목 딕셔너리 → HeldSymbolOverseasFutures 리스트 + 방향별 종목셋"""
    held_list: List[HeldSymbolOverseasFutures] = []
    held_positions: Dict[str, Set[str]] = {}  # symbol -> {"long", "short", ...}
    
    for symbol, pos in positions.items():
        held_list.append(adapt_futures_position_to_held(pos))
        
        code = symbol.strip()
        is_long = getattr(pos, 'is_long', None)
        
        bucket = held_positions.setdefault(code, set())
        if is_long is None:
            bucket.add("__any__")
        else:
            bucket.discard("__any__")
            bucket.add("long" if is_long else "short")
    
    return held_list, held_positions


def adapt_futures_open_order_to_non_traded(order: Any) -> NonTradedSymbolOverseasFutures:
    """FuturesOpenOrder → NonTradedSymbolOverseasFutures 변환"""
    return NonTradedSymbolOverseasFutures(
        OrdNo=getattr(order, 'order_no', ''),
        IsuCodeVal=getattr(order, 'symbol', ''),
        IsuNm=getattr(order, 'symbol_name', '') if hasattr(order, 'symbol_name') else '',
        BnsTpCode=getattr(order, 'order_type', ''),
        OrdQty=to_int(getattr(order, 'order_qty', 0)),
        OrdPrc=to_float(getattr(order, 'order_price', 0)),
        UnercQty=to_int(getattr(order, 'remaining_qty', 0)),
        CnfQty=to_int(getattr(order, 'executed_qty', 0)),
        OrdTime=getattr(order, 'order_time', ''),
    )


def adapt_futures_open_orders_to_non_traded_list(
    orders: Dict[str, Any]
) -> Tuple[List[NonTradedSymbolOverseasFutures], Dict[str, Set[str]]]:
    """미체결 딕셔너리 → NonTradedSymbolOverseasFutures 리스트 + 방향별 종목셋"""
    non_traded_list: List[NonTradedSymbolOverseasFutures] = []
    non_traded_positions: Dict[str, Set[str]] = {}
    
    for order_no, order in orders.items():
        non_traded_list.append(adapt_futures_open_order_to_non_traded(order))
        
        symbol = getattr(order, 'symbol', '').strip()
        if symbol:
            bns_code = getattr(order, 'order_type', '')
            bucket = non_traded_positions.setdefault(symbol, set())
            
            if bns_code == "1":
                bucket.add("short")
            elif bns_code == "2":
                bucket.add("long")
            else:
                bucket.add("__any__")
    
    return non_traded_list, non_traded_positions


def adapt_futures_balance_to_dps(balance: Any) -> List[DpsTyped]:
    """FuturesBalanceInfo → DpsTyped 리스트"""
    if balance is None:
        return [{
            "deposit": 0.0,
            "orderable_amount": 0.0,
            "currency": "USD",
        }]
    
    return [{
        "deposit": to_float(getattr(balance, 'deposit', 0)),
        "orderable_amount": to_float(getattr(balance, 'orderable_amount', 0)),
        "currency": getattr(balance, 'currency_code', 'USD'),
    }]
