"""
단일 중첩 해외주식 예제 (Single Nesting Overseas Stock Example)

이 예제는 단일 레벨 중첩 조건을 사용하는 방식을 보여줍니다.
하위 conditions가 먼저 평가되고, 통과하면 상위 condition_id가 평가됩니다.

구조:
├── conditions (logic: "all") ← 전략 레벨
│   └── SMAGoldenDeadCross (골든크로스 확인) ← 상위: 하위 통과 후 실행
│       └── conditions (logic: "all") ← 하위: 먼저 실행
│           ├── ADX (추세 강도 필터)
│           └── ATR (변동성 필터)

실행 순서:
1. 하위 conditions 내 ADX, ATR이 병렬 평가됨
2. 하위 조건이 모두 통과하면 상위 SMAGoldenDeadCross 평가
3. 상위도 통과하면 최종 성공

특징:
- 단일 레벨 중첩 구조 (하위 → 상위 순차 실행)
- 필터 조건(하위)이 통과해야 메인 조건(상위)이 실행됨
- 주문 조건(orders) 블록 포함 → StockSplitFunds로 분할 매수
"""
from dotenv import load_dotenv
from programgarden import Programgarden
import os

load_dotenv()


if __name__ == "__main__":
    pg = Programgarden()

    # 전략 수행 응답 콜백
    pg.on_strategy(
        callback=lambda message: print(
            f"[전략] {message.get('event_type')}: {message.get('condition_id')} - {message.get('message')}"
        )
    )

    # 실시간 주문 응답 콜백
    pg.on_order(
        callback=lambda message: print(
            f"[주문] {message.get('event_type')}: {message.get('order_type')}, {message.get('message')}"
        )
    )

    # 퍼포먼스 모니터링 콜백
    pg.on_performance_message(
        callback=lambda message: print(
            f"[성능] {message.get('event_type')}: {message.get('context')} - Duration: {message.get('stats', {}).get('duration_seconds')}s"
        )
    )

    pg.run(
        system={
            # ========================================
            # 1. 시스템 설정 (settings)
            # ========================================
            "settings": {
                "system_id": "single_nesting_overseas_stock_001",
                "name": "단일 중첩 해외주식 예제",
                "description": "단일 레벨 중첩 조건을 사용하는 예제 (외부 조건 + 내부 필터)",
                "version": "1.0.0",
                "author": "ProgramGarden",
                "date": "2026-01-02",
                "dry_run_mode": "test",
            },
            
            # ========================================
            # 2. 증권사 설정 (securities)
            # ========================================
            "securities": {
                "company": "ls",
                "product": "overseas_stock",
                "appkey": os.getenv("APPKEY"),
                "appsecretkey": os.getenv("APPSECRET"),
            },
            
            # ========================================
            # 3. 전략 정의 (strategies)
            # ========================================
            "strategies": [
                {
                    "id": "single_nested_strategy",
                    "description": "골든크로스 + 필터 그룹(추세/변동성) 병렬 조합",
                    
                    # 스케줄: 30초마다 실행
                    "schedule": "*/30 * * * * *",
                    "timezone": "America/New_York",
                    "run_once_on_start": True,
                    
                    # 논리 연산자
                    "logic": "all",
                    
                    # 대상 종목
                    "symbols": [
                        {"symbol": "NVDA", "exchange": "NASDAQ"},
                        {"symbol": "MSFT", "exchange": "NASDAQ"},
                        {"symbol": "GOOGL", "exchange": "NASDAQ"},
                    ],
                    
                    # 주문 블록 연결
                    "order_id": "split_buy_order",
                    
                    # ========================================
                    # 조건들 (하위 → 상위 순차 실행 구조)
                    # ========================================
                    "conditions": [
                        # ========================
                        # 상위 조건: SMA 골든크로스 (하위 통과 후 실행)
                        # ========================
                        {
                            "condition_id": "SMAGoldenDeadCross",
                            "weight": 0.5,
                            "params": {
                                "use_ls": True,
                                "appkey": os.getenv("APPKEY"),
                                "appsecretkey": os.getenv("APPSECRET"),
                                "start_date": "20250101",
                                "end_date": "20260101",
                                "alignment": "golden",
                                "long_period": 50,
                                "short_period": 20,
                                "time_category": "days",
                            },
                            
                            # ========================
                            # 하위 조건: 필터 그룹 (먼저 실행)
                            # ========================
                            # 이 conditions가 먼저 평가되고, 통과하면 상위 SMAGoldenDeadCross가 평가됨
                            "logic": "all",  # 모든 필터 조건 통과 필요
                            "conditions": [
                                # 필터 1: ADX 추세 강도
                                {
                                    "condition_id": "ADX",
                                    "weight": 0.3,
                                    "params": {
                                        "appkey": os.getenv("APPKEY"),
                                        "appsecretkey": os.getenv("APPSECRET"),
                                        "period": 14,
                                        "threshold": 25,  # ADX > 25 = 강한 추세
                                    },
                                },
                                # 필터 2: ATR 변동성
                                {
                                    "condition_id": "ATR",
                                    "weight": 0.2,
                                    "params": {
                                        "appkey": os.getenv("APPKEY"),
                                        "appsecretkey": os.getenv("APPSECRET"),
                                        "period": 14,
                                        "atr_multiplier": 1.5,
                                    },
                                },
                            ],
                        },
                    ],
                },
            ],
            
            # ========================================
            # 4. 주문 정의 (orders) - 분할 매수
            # ========================================
            "orders": [
                {
                    "order_id": "split_buy_order",
                    "description": "예수금 기반 분할 매수 주문",
                    "block_duplicate_buy": True,  # 중복 매수 방지
                    
                    # 주문 시간 설정
                    "order_time": {
                        "start": "09:30:00",
                        "end": "16:00:00",
                        "days": ["mon", "tue", "wed", "thu", "fri"],
                        "timezone": "America/New_York",
                        "behavior": "defer",
                        "max_delay_seconds": 86400,
                    },
                    
                    # 주문 조건
                    "condition": {
                        "condition_id": "StockSplitFunds",
                        "params": {
                            "appkey": os.getenv("APPKEY"),
                            "appsecretkey": os.getenv("APPSECRET"),
                            "percent_balance": 0.1,  # 예수금의 10%
                            "max_symbols": 3,  # 최대 3종목
                        },
                    },
                },
            ],
        }
    )
