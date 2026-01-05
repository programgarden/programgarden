"""
중첩 없음 해외선물 예제 (No Nesting Overseas Futures Example)

이 예제는 중첩 조건 없이 평면적으로 여러 조건을 조합하는 방식을 보여줍니다.
해외선물은 position_side(long/short/neutral/flat)를 반환해야 합니다.

구조:
├── conditions (logic: "all")
│   ├── FuturesADX (추세 강도 확인) → position_side: neutral
│   ├── FuturesATR (변동성 확인) → position_side: neutral
│   └── FuturesSMAEMACross (추세 방향) → position_side: long/short

position_side 규칙:
- neutral: 필터 조건 (방향 결정 위임)
- long/short: 방향 결정 조건
- flat: 진입 신호 없음
- 모든 조건이 neutral이면 방향 결정 불가 → 주문 실행 안됨

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
            f"[전략] {message.get('event_type')}: {message.get('condition_id')} - "
            f"position_side: {message.get('position_side')} - {message.get('message')}"
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
                "system_id": "no_nesting_overseas_futures_001",
                "name": "중첩 없음 해외선물 예제",
                "description": "중첩 조건 없이 평면적으로 여러 조건을 조합하는 해외선물 예제",
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
                "product": "overseas_futures",  # 해외선물
                "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                "paper_trading": True,  # 모의투자
                # 참고: 해외선물 모의투자는 HKEX(홍콩거래소)만 지원
            },
            
            # ========================================
            # 3. 전략 정의 (strategies)
            # ========================================
            "strategies": [
                {
                    "id": "flat_conditions_futures_strategy",
                    "description": "중첩 없이 여러 조건을 동일 레벨에서 AND 조합 (선물)",
                    
                    # 스케줄: 10초마다 실행
                    "schedule": "*/10 * * * * *",
                    "timezone": "Asia/Hong_Kong",  # 홍콩 시간대
                    "run_once_on_start": True,
                    
                    # 논리 연산자: 모든 조건이 True여야 함
                    "logic": "all",
                    
                    # 대상 종목 (홍콩 선물)
                    "symbols": [
                        {"symbol": "HSIF", "exchange": "HKEX"},  # 항셍지수 선물
                    ],
                    
                    # 주문 블록 없음 (order_id 미지정)
                    # → 전략 분석만 수행하고 주문은 실행하지 않음
                    
                    # ========================================
                    # 조건들 (중첩 없음, 평면 구조)
                    # ========================================
                    "conditions": [
                        # 조건 1: FuturesADX 추세 강도 확인 (필터, neutral 반환)
                        {
                            "condition_id": "FuturesADX",
                            "weight": 0.3,
                            "params": {
                                "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                                "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                                "period": 14,
                                "threshold": 25,  # ADX > 25 = 강한 추세
                            },
                            # position_side: neutral 반환 (필터 조건)
                        },
                        
                        # 조건 2: FuturesATR 변동성 확인 (필터, neutral 반환)
                        {
                            "condition_id": "FuturesATR",
                            "weight": 0.3,
                            "params": {
                                "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                                "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                                "period": 14,
                                "atr_multiplier": 1.5,
                            },
                            # position_side: neutral 반환 (필터 조건)
                        },
                        
                        # 조건 3: FuturesSMAEMACross 추세 방향 (방향 결정, long/short 반환)
                        {
                            "condition_id": "FuturesSMAEMACross",
                            "weight": 0.4,
                            "params": {
                                "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                                "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                                "period_sma": 55,
                                "period_ema": 21,
                                "lookback": 3,
                                "timeframe": "days",
                            },
                            # position_side: long/short 반환 (방향 결정 조건)
                        },
                    ],
                },
            ],
            
            # ========================================
            # 4. 주문 정의 (orders) - 이 예제에서는 미포함
            # ========================================
            # orders 블록이 없으면 전략은 분석만 수행하고 주문은 실행하지 않습니다.
            "orders": [],
        }
    )
