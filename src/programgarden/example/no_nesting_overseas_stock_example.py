"""
중첩 없음 해외주식 예제 (No Nesting Overseas Stock Example)

이 예제는 중첩 조건 없이 평면적으로 여러 조건을 조합하는 방식을 보여줍니다.
모든 조건이 동일한 레벨에서 logic: "all"로 평가됩니다.

구조:
├── conditions (logic: "all")
│   ├── SMAGoldenDeadCross (골든크로스 확인)
│   ├── ADX (추세 강도 확인)
│   └── ATR (변동성 확인)

특징:
- 중첩 없이 모든 조건이 같은 레벨에 존재
- logic: "all" → 모든 조건이 True여야 전략 통과
- 주문 조건(orders) 블록 미포함 → 전략 분석만 수행
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

    # 실시간 주문 응답 콜백 (이 예제에서는 orders 블록이 없으므로 호출되지 않음)
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
                "system_id": "no_nesting_overseas_stock_001",
                "name": "중첩 없음 해외주식 예제",
                "description": "중첩 조건 없이 평면적으로 여러 조건을 조합하는 예제",
                "version": "1.0.0",
                "author": "ProgramGarden",
                "date": "2026-01-02",
                "dry_run_mode": "test",  # test | live | guarded_live
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
                    "id": "flat_conditions_strategy",
                    "description": "중첩 없이 여러 조건을 동일 레벨에서 AND 조합",
                    
                    # 스케줄: 10초마다 실행
                    "schedule": "*/10 * * * * *",
                    "timezone": "America/New_York",
                    "run_once_on_start": True,
                    
                    # 논리 연산자: 모든 조건이 True여야 함
                    "logic": "all",
                    
                    # 대상 종목
                    "symbols": [
                        {"symbol": "AAPL", "exchange": "NASDAQ"},
                        {"symbol": "TSLA", "exchange": "NASDAQ"},
                    ],
                    
                    # 주문 블록 없음 (order_id 미지정)
                    # → 전략 분석만 수행하고 주문은 실행하지 않음
                    
                    # ========================================
                    # 조건들 (중첩 없음, 평면 구조)
                    # ========================================
                    "conditions": [
                        # 조건 1: SMA 골든크로스 확인
                        {
                            "condition_id": "SMAGoldenDeadCross",
                            "weight": 0.4,
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
                        },
                        
                        # 조건 2: ADX 추세 강도 확인
                        {
                            "condition_id": "ADX",
                            "weight": 0.3,
                            "params": {
                                "appkey": os.getenv("APPKEY"),
                                "appsecretkey": os.getenv("APPSECRET"),
                                "period": 14,
                                "threshold": 25,  # ADX > 25 이면 강한 추세
                            },
                        },
                        
                        # 조건 3: ATR 변동성 확인
                        {
                            "condition_id": "ATR",
                            "weight": 0.3,
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
            
            # ========================================
            # 4. 주문 정의 (orders) - 이 예제에서는 미포함
            # ========================================
            # orders 블록이 없으면 전략은 분석만 수행하고 주문은 실행하지 않습니다.
            # 이는 전략 테스트 또는 시그널 확인 용도로 유용합니다.
            "orders": [],
        }
    )
