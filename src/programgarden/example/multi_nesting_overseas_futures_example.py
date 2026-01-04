"""
다중 중첩 해외선물 예제 (Multi Nesting Overseas Futures Example)

이 예제는 3계층 다중 중첩 조건을 사용하는 해외선물 전략을 보여줍니다.
하위 조건이 먼저 평가되고, 통과하면 상위 조건이 평가됩니다.
계층별로 서로 다른 논리 연산자와 position_side 조합 패턴을 적용합니다.

구조:
├── conditions (logic: "all") ← 전략 레벨
│   └── FuturesADX (추세 강도 필터) → position_side: neutral ← 1계층 (하위 통과 후 실행)
│       └── conditions (logic: "any") ← 2계층 (먼저 실행)
│           ├── FuturesSMAEMACross (추세 방향) → position_side: long/short
│           └── conditions (logic: "at_least", threshold: 1) ← 3계층 (최하위, 가장 먼저 실행)
│               ├── FuturesBollingerBands → position_side: long/short
│               └── FuturesCCI → position_side: long/short

실행 순서:
1. 3계층(at_least): BollingerBands, CCI 중 1개 이상 통과, 방향 결정
2. 3계층 통과 → 2계층(any): SMAEMACross 또는 3계층 결과 중 하나라도 통과, 방향 합의
3. 2계층 통과 → 1계층(all): FuturesADX(neutral) 평가 후 최종 결정, 방향은 2계층에서 전파

position_side 합성 규칙:
- neutral 조건은 통과/실패만 결정, 방향 결정에 영향 없음
- long/short가 결정되면 상위로 전파
- 동일 레벨에서 long과 short가 혼재하면 → 충돌 처리 (기본: flat)

특징:
- 3계층 다중 중첩 구조 (하위 → 상위 순차 실행)
- 필터 조건(neutral)과 방향 결정 조건(long/short) 혼합
- 주문 조건(orders) 블록 포함 → TwoPercentRuleEntry로 2% 룰 진입
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
                "system_id": "multi_nesting_overseas_futures_001",
                "name": "다중 중첩 해외선물 예제",
                "description": "3계층 다중 중첩 조건 (all → any → at_least) 해외선물 예제",
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
                    "id": "multi_nested_futures_strategy",
                    "description": "3계층 중첩: 필터(ADX) → 방향 선택(SMA/EMA or BB/CCI)",
                    
                    # 스케줄: 1분마다 실행
                    "schedule": "0 */1 * * * *",
                    "timezone": "Asia/Hong_Kong",
                    "run_once_on_start": True,
                    
                    # 논리 연산자
                    "logic": "all",
                    
                    # 대상 종목 (홍콩 선물)
                    "symbols": [
                        {"symbol": "HSIF", "exchange": "HKEX"},  # 항셍지수 선물
                    ],
                    
                    # 주문 블록 연결
                    "order_id": "two_percent_rule_order",
                    
                    # ========================================
                    # 조건들 (3계층 다중 중첩 - 하위 → 상위 순차 실행)
                    # ========================================
                    "conditions": [
                        # ========================
                        # 1계층: 최상위 조건 (FuturesADX, neutral) - 하위 통과 후 실행
                        # ========================
                        # 추세 강도를 확인하지만 방향은 결정하지 않음
                        {
                            "condition_id": "FuturesADX",
                            "weight": 0.3,
                            "params": {
                                "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                                "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                                "period": 14,
                                "threshold": 20,  # ADX > 20 = 추세 존재
                            },
                            # position_side: neutral 반환 (필터, 방향 결정 위임)
                            
                            # ========================
                            # 2계층: 중간 중첩 (any) - 먼저 실행
                            # ========================
                            # SMAEMACross 또는 3계층 결과 중 하나만 통과해도 OK
                            "logic": "any",
                            "conditions": [
                                # 2계층 조건 1: FuturesSMAEMACross (방향 결정)
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
                                    # position_side: long/short 반환 (방향 결정)
                                },
                                
                                # ========================
                                # 3계층: 최하위 중첩 (at_least) - 가장 먼저 실행
                                # ========================
                                # BollingerBands, CCI 중 1개 이상 통과
                                {
                                    "logic": "at_least",
                                    "threshold": 1,  # 1개 이상 조건 통과
                                    "conditions": [
                                        # 3계층 조건 1: FuturesBollingerBands (방향 결정)
                                        {
                                            "condition_id": "FuturesBollingerBands",
                                            "weight": 0.3,
                                            "params": {
                                                "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                                                "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                                                "period": 20,
                                                "std_dev": 2.0,
                                            },
                                            # position_side: long (하단 터치) / short (상단 터치)
                                        },
                                        # 3계층 조건 2: FuturesCCI (방향 결정)
                                        {
                                            "condition_id": "FuturesCCI",
                                            "weight": 0.3,
                                            "params": {
                                                "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                                                "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                                                "period": 20,
                                            },
                                            # position_side: long (과매도) / short (과매수)
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
            
            # ========================================
            # 4. 주문 정의 (orders) - 2% 룰 진입
            # ========================================
            "orders": [
                {
                    "order_id": "two_percent_rule_order",
                    "description": "2% 룰 기반 포지션 사이징 진입 주문",
                    
                    # 주문 시간 설정 (홍콩 시장)
                    "order_time": {
                        "start": "09:30:00",
                        "end": "16:00:00",
                        "days": ["mon", "tue", "wed", "thu", "fri"],
                        "timezone": "Asia/Hong_Kong",
                        "behavior": "defer",
                        "max_delay_seconds": 86400,
                    },
                    
                    # 주문 조건: 2% 룰 진입
                    "condition": {
                        "condition_id": "TwoPercentRuleEntry",
                        "params": {
                            "appkey": os.getenv("APPKEY_FUTURE_FAKE"),
                            "appsecretkey": os.getenv("APPSECRET_FUTURE_FAKE"),
                            "risk_percent": 2.0,  # 자본의 2% 리스크
                            "atr_period": 14,
                            "atr_multiplier": 2.0,  # 손절폭 = ATR * 2
                        },
                    },
                },
            ],
        }
    )
