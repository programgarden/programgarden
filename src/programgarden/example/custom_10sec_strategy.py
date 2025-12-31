# 10초 간격 커스텀 DSL 전략
# 직접 작성한 커스텀 조건 클래스를 사용하는 예제

# ⚠️ 로깅 설정은 반드시 다른 모듈 import 전에 해야 합니다!
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

from dotenv import load_dotenv
from programgarden import Programgarden
from programgarden_core import (
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionResponseOverseasStockType,
    BaseNewOrderOverseasStock,
    BaseNewOrderOverseasStockResponseType,
)
from typing import List
import os
import asyncio
import time
import threading
import random
from datetime import datetime

load_dotenv()

# ⚠️ programgarden_core가 propagate=False로 설정하므로, import 후에 다시 True로 설정
logger = logging.getLogger("programgarden")
logger.setLevel(logging.DEBUG)
logger.propagate = True  # 루트 로거로 전파 활성화


# ============================================================
# 커스텀 조건 클래스들
# ============================================================
class CustomDummyCondition(BaseStrategyConditionOverseasStock):
    """기본 더미 조건"""

    id = "CustomDummyCondition"
    description = "기본 더미 조건"
    securities = ["ls-sec.co.kr"]

    _global_execution_count = 0

    def __init__(self, name: str = "Dummy", delay_range: tuple = (1.0, 2.0)):
        super().__init__()
        self.name = name
        self.delay_range = delay_range
        self.id = name  # 조건 ID를 이름으로 설정

    async def execute(self) -> BaseStrategyConditionResponseOverseasStockType:
        CustomDummyCondition._global_execution_count += 1
        execution_num = CustomDummyCondition._global_execution_count
        symbol = self.symbol or {}

        # 조건 계산 시뮬레이션
        delay = random.uniform(*self.delay_range)
        await asyncio.sleep(delay)

        is_success = True

        return {
            "condition_id": self.id,
            "success": is_success,
            "symbol": symbol.get("symbol", ""),
            "exchcd": symbol.get("exchcd", ""),
            "data": {"execution_count": execution_num},
            "weight": 1 if is_success else 0,
            "product": "overseas_stock",
        }


class RSICondition(BaseStrategyConditionOverseasStock):
    """RSI 조건 (더미)"""

    id = "RSI_Check"
    description = "RSI 과매도 체크"
    securities = ["ls-sec.co.kr"]

    def __init__(self, threshold: int = 30):
        super().__init__()
        self.threshold = threshold

    async def execute(self) -> BaseStrategyConditionResponseOverseasStockType:
        symbol = self.symbol or {}
        await asyncio.sleep(random.uniform(0.8, 1.5))
        
        # 랜덤하게 50% 확률로 성공
        is_success = random.random() > 0.5

        return {
            "condition_id": self.id,
            "success": is_success,
            "symbol": symbol.get("symbol", ""),
            "exchcd": symbol.get("exchcd", ""),
            "data": {"rsi": random.randint(20, 80)},
            "weight": 1 if is_success else 0,
            "product": "overseas_stock",
        }


class VolumeCondition(BaseStrategyConditionOverseasStock):
    """거래량 조건 (더미)"""

    id = "Volume_Check"
    description = "거래량 급증 체크"
    securities = ["ls-sec.co.kr"]

    def __init__(self):
        super().__init__()

    async def execute(self) -> BaseStrategyConditionResponseOverseasStockType:
        symbol = self.symbol or {}
        await asyncio.sleep(random.uniform(0.5, 1.2))
        
        is_success = random.random() > 0.3  # 70% 확률로 성공

        return {
            "condition_id": self.id,
            "success": is_success,
            "symbol": symbol.get("symbol", ""),
            "exchcd": symbol.get("exchcd", ""),
            "data": {"volume_ratio": random.uniform(1.0, 3.0)},
            "weight": 1 if is_success else 0,
            "product": "overseas_stock",
        }


class MACDCondition(BaseStrategyConditionOverseasStock):
    """MACD 조건 (더미)"""

    id = "MACD_Check"
    description = "MACD 골든크로스 체크"
    securities = ["ls-sec.co.kr"]

    def __init__(self):
        super().__init__()

    async def execute(self) -> BaseStrategyConditionResponseOverseasStockType:
        symbol = self.symbol or {}
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        is_success = random.random() > 0.4  # 60% 확률로 성공

        return {
            "condition_id": self.id,
            "success": is_success,
            "symbol": symbol.get("symbol", ""),
            "exchcd": symbol.get("exchcd", ""),
            "data": {"macd_signal": "bullish" if is_success else "bearish"},
            "weight": 2 if is_success else 0,  # 가중치 2
            "product": "overseas_stock",
        }


# ============================================================
# 커스텀 주문 클래스 (통합)
# ============================================================
class DummyNewOrder(BaseNewOrderOverseasStock):
    """테스트용 더미 주문 - 실제 주문 안 넣음 (success=False)"""

    id: str = "DummyNewOrder"
    description: str = "테스트용 더미 주문 (실제 주문 없음)"
    securities: List[str] = ["ls-sec.co.kr"]
    order_types = ["new_buy"]

    def __init__(self, default_qty: int = 1):
        super().__init__()
        self.default_qty = default_qty

    async def execute(self) -> List[BaseNewOrderOverseasStockResponseType]:
        orders: List[BaseNewOrderOverseasStockResponseType] = []
        
        print(f"\n📦 [DummyNewOrder] 주문 실행 호출됨")
        print(f"   - available_symbols: {len(self.available_symbols or [])}개")
        print(f"   - held_symbols: {len(self.held_symbols or [])}개")
        print(f"   - system_id: {self.system_id}")
        
        for symbol_info in (self.available_symbols or []):
            symbol = symbol_info.get("symbol", "")
            exchcd = symbol_info.get("exchcd", "82")  # 기본 NASDAQ
            
            print(f"   📝 주문 생성: {symbol} (거래소: {exchcd})")
            
            orders.append({
                "success": False,  # ✅ 실제 주문 안 넣음!
                "ord_ptn_code": "02",        # 매수
                "ord_mkt_code": exchcd,
                "shtn_isu_no": symbol,
                "ord_qty": self.default_qty,
                "ovrs_ord_prc": 100.0,       # 더미 가격
                "ordprc_ptn_code": "00",     # 지정가
                "brk_tp_code": "",
                "crcy_code": "USD",
                "pnl_rat": 0.0,
                "pchs_amt": 0.0,
                "bns_tp_code": "2",          # 매수
            })
        
        print(f"   ✅ 총 {len(orders)}개 주문 생성 (success=False이므로 실제 전송 안함)")
        return orders

    async def on_real_order_receive(self, order_type, response):
        """실시간 주문 응답 콜백"""
        print(f"\n📨 [DummyNewOrder] 실시간 주문 응답: {order_type}")
        print(f"   response: {response}")


# ============================================================
# 메인 실행
# ============================================================
if __name__ == "__main__":
    pg = Programgarden()

    # 콜백 설정 (간소화)
    pg.on_strategy(
        callback=lambda msg: None  # 조용히
    )
    pg.on_order(
        callback=lambda msg: None
    )
    pg.on_performance_message(
        callback=lambda msg: None
    )

    # 60초 후 자동 종료 타이머
    def stop_after_60_seconds():
        print("\n⏱️  60초 타이머 시작...")
        time.sleep(60)
        print("\n🛑 60초 경과 - 시스템 자동 종료합니다...")
        os._exit(0)

    timer_thread = threading.Thread(target=stop_after_60_seconds, daemon=True)
    timer_thread.start()

    print("=" * 60)
    print("🚀 병렬 전략 테스트")
    print("   - 전략 3개 (각각 다른 스케줄)")
    print("   - 각 전략 조건 2~3개")
    print("   - 자동 종료: 60초 후")
    print("=" * 60)

    pg.run(
        system={
            "settings": {
                "system_id": "parallel_strategy_test",
                "name": "병렬 전략 테스트",
                "description": "여러 전략이 병렬로 실행되는 테스트",
                "version": "1.0.0",
                "author": "ProgramGarden User",
                "date": "2025-12-26",
                "dry_run_mode": "test",
            },
            "securities": {
                "company": "ls",
                "product": "overseas_stock",
                "appkey": os.getenv("APPKEY"),
                "appsecretkey": os.getenv("APPSECRET"),
                "paper_trading": True,
            },
            "strategies": [
                # 전략 1: 10초마다, RSI + Volume 조건
                {
                    "id": "tech_momentum",
                    "description": "기술적 모멘텀 전략",
                    "schedule": "*/10 * * * * *",
                    "timezone": "Asia/Seoul",
                    "run_once_on_start": True,
                    "logic": "all",
                    "order_id": "unified_order",  # 통합 주문과 연결
                    "symbols": [
                        {"symbol": "AAPL", "name": "애플", "exchange": "NASDAQ"},
                        {"symbol": "MSFT", "name": "마이크로소프트", "exchange": "NASDAQ"},
                    ],
                    "conditions": [
                        RSICondition(threshold=30),
                        VolumeCondition(),
                    ],
                },
                # 전략 2: 15초마다, MACD + RSI + Volume 조건
                {
                    "id": "swing_trade",
                    "description": "스윙 트레이딩 전략",
                    "schedule": "*/15 * * * * *",
                    "timezone": "Asia/Seoul",
                    "run_once_on_start": True,
                    "logic": "any",  # 하나만 만족해도 OK
                    "order_id": "unified_order",  # 통합 주문과 연결
                    "symbols": [
                        {"symbol": "TSLA", "name": "테슬라", "exchange": "NASDAQ"},
                        {"symbol": "NVDA", "name": "엔비디아", "exchange": "NASDAQ"},
                        {"symbol": "AMD", "name": "AMD", "exchange": "NASDAQ"},
                    ],
                    "conditions": [
                        MACDCondition(),
                        RSICondition(threshold=25),
                        VolumeCondition(),
                    ],
                },
                # 전략 3: 20초마다, 단순 더미 조건 2개
                {
                    "id": "simple_check",
                    "description": "단순 체크 전략",
                    "schedule": "*/20 * * * * *",
                    "timezone": "Asia/Seoul",
                    "run_once_on_start": True,
                    "logic": "all",
                    "order_id": "unified_order",  # 통합 주문과 연결
                    "symbols": [
                        {"symbol": "GOOGL", "name": "구글", "exchange": "NASDAQ"},
                    ],
                    "conditions": [
                        CustomDummyCondition(name="Price_Check", delay_range=(0.5, 1.0)),
                        CustomDummyCondition(name="Trend_Check", delay_range=(0.8, 1.5)),
                    ],
                },
            ],
            # ============================================================
            # 주문 전략 (통합 1개)
            # ============================================================
            "orders": [
                {
                    "order_id": "unified_order",
                    "description": "통합 더미 주문 (테스트용, 실제 주문 안함)",
                    "block_duplicate_buy": True,  # 중복 매수 방지
                    "condition": DummyNewOrder(default_qty=1),
                },
            ],
        }
    )
