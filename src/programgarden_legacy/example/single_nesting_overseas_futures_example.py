"""
단일 중첩 해외선물 예제 (Single Nesting Overseas Futures Example)

이 예제는 단일 레벨 중첩 조건을 사용하는 해외선물 전략을 보여줍니다.
하위 필터 조건(neutral)이 먼저 평가되고, 통과하면 상위 방향 조건(long/short)이 평가됩니다.

구조:
├── conditions (logic: "all") ← 전략 레벨
│   └── FuturesSMAEMACross (추세 방향) → position_side: long/short ← 상위: 하위 통과 후 실행
│       └── conditions (logic: "all") ← 하위: 먼저 실행
│           ├── FuturesVolatilityFilter (변동성 필터) → position_side: neutral
│           └── FuturesADX (추세 강도 필터) → position_side: neutral

실행 순서:
1. 하위 conditions 내 FuturesVolatilityFilter, FuturesADX가 병렬 평가됨
2. 하위 조건이 모두 통과하면 상위 FuturesSMAEMACross 평가
3. 상위도 통과하면 최종 성공 (long/short 방향 결정)

position_side 합성:
- 하위 필터 조건(neutral)은 통과/실패만 결정, 방향에 영향 없음
- 상위 방향 조건(long/short)이 최종 방향 결정

특징:
- 단일 레벨 중첩 구조 (하위 → 상위 순차 실행)
- 필터 조건(하위)이 통과해야 방향 조건(상위)이 실행됨
- 주문 조건(orders) 블록 포함 → VolatilityBreakoutEntry로 변동성 돌파 진입
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
                "system_id": "single_nesting_overseas_futures_001",
                "name": "단일 중첩 해외선물 예제",
                "description": "단일 레벨 중첩 조건을 사용하는 해외선물 예제 (방향 조건 + 내부 필터)",
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
                    "id": "single_nested_futures_strategy",
                    "description": "추세 방향(SMA/EMA) + 필터 그룹(변동성/추세강도) 병렬 조합",
                    
                    # 스케줄: 30초마다 실행
                    "schedule": "*/30 * * * * *",
                    "timezone": "Asia/Hong_Kong",
                    "run_once_on_start": True,
                    
                    # 논리 연산자
                    "logic": "all",
                    
                    # 대상 종목 (홍콩 선물)
                    "symbols": [
                        {"symbol": "HSIF", "exchange": "HKEX"},  # 항셍지수 선물
                    ],
                    
                    # 주문 블록 연결
                    "order_id": "volatility_breakout_order",
                    
                    # ========================================
                    # 조건들 (하위 → 상위 순차 실행 구조)
                    # ========================================
                    "conditions": [
                        # ========================
                        # 상위 조건: FuturesSMAEMACross (하위 통과 후 실행)
                        # ========================
                        # 방향 결정 (long/short) 플러그인
                        {
                            "condition_id": "FuturesSMAEMACross",
                            "weight": 0.5,
                            "params": {
                                "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                                "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                                "period_sma": 55,
                                "period_ema": 21,
                                "lookback": 3,
                                "timeframe": "days",
                            },
                            # position_side: long/short 반환 (방향 결정)
                            
                            # ========================
                            # 하위 조건: 필터 그룹 (먼저 실행)
                            # ========================
                            # 이 conditions가 먼저 평가되고, 통과하면 상위 FuturesSMAEMACross가 평가됨
                            "logic": "all",  # 모든 필터 조건 통과 필요
                            "conditions": [
                                # 필터 1: FuturesVolatilityFilter (변동성 필터) - 커스텀 플러그인
                                {
                                    "condition_id": "FuturesVolatilityFilter",
                                    "weight": 0.25,
                                    "params": {
                                        "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                                        "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                                        "atr_period": 14,
                                        "min_atr_percent": 0.5,  # 최소 0.5% 변동성
                                        "max_atr_percent": 5.0,  # 최대 5% 변동성
                                        "timeframe": "days",
                                    },
                                    # position_side: neutral 반환 (필터)
                                },
                                # 필터 2: FuturesADX (추세 강도 필터)
                                {
                                    "condition_id": "FuturesADX",
                                    "weight": 0.25,
                                    "params": {
                                        "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                                        "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                                        "period": 14,
                                        "threshold": 20,  # ADX > 20 = 추세 존재
                                    },
                                    # position_side: neutral 반환 (필터)
                                },
                            ],
                        },
                    ],
                },
            ],
            
            # ========================================
            # 4. 주문 정의 (orders) - 변동성 돌파 진입
            # ========================================
            "orders": [
                {
                    "order_id": "volatility_breakout_order",
                    "description": "변동성 돌파 진입 주문",
                    
                    # 주문 시간 설정 (홍콩 시장)
                    "order_time": {
                        "start": "09:30:00",
                        "end": "16:00:00",
                        "days": ["mon", "tue", "wed", "thu", "fri"],
                        "timezone": "Asia/Hong_Kong",
                        "behavior": "defer",
                        "max_delay_seconds": 86400,
                    },
                    
                    # 주문 조건: 변동성 돌파 진입
                    "condition": {
                        "condition_id": "VolatilityBreakoutEntry",
                        "params": {
                            "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                            "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                            "breakout_multiplier": 0.5,  # ATR의 0.5배 돌파 시 진입
                            "position_size_percent": 2.0,  # 자본의 2% 리스크
                        },
                    },
                },
            ],
        }
    )
