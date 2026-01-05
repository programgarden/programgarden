"""
다중 중첩 해외주식 예제 (Multi Nesting Overseas Stock Example)

이 예제는 3계층 다중 중첩 조건을 사용하는 방식을 보여줍니다.
계층별로 서로 다른 논리 연산자(all, at_least, weighted)를 적용합니다.

구조:
├── conditions (logic: "all")
│   └── ADX (추세 강도 확인) ← 1계층: 최상위 조건
│       └── conditions (logic: "at_least", threshold: 1) ← 2계층
│           ├── BollingerBands (볼린저밴드)
│           ├── CCI (상품채널지수)
│           └── conditions (logic: "weighted", threshold: 0.6) ← 3계층
│               ├── OBV (거래량 누적, weight: 0.4)
│               └── VolumeSpike (거래량 급증, weight: 0.4)

실행 순서:
1. 3계층(weighted): OBV, VolumeSpike의 가중치 합 >= 0.6 확인
2. 2계층(at_least): BollingerBands, CCI, 3계층 결과 중 1개 이상 통과 확인
3. 1계층(all): ADX와 2계층 결과 모두 통과 확인

특징:
- 3계층 다중 중첩 구조
- 각 계층별 서로 다른 논리 연산자 적용
- 주문 조건(orders) 블록 포함 → TrailingStopSellManager로 트레일링 스탑
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
                "system_id": "multi_nesting_overseas_stock_001",
                "name": "다중 중첩 해외주식 예제",
                "description": "3계층 다중 중첩 조건 (all → at_least → weighted) 예제",
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
                    "id": "multi_nested_strategy",
                    "description": "추세(ADX) + 중첩 그룹(모멘텀/수급) 병렬 조합",
                    
                    # 스케줄: 1분마다 실행
                    "schedule": "0 */1 * * * *",
                    "timezone": "America/New_York",
                    "run_once_on_start": True,
                    
                    # 논리 연산자
                    "logic": "all",
                    
                    # 대상 종목
                    "symbols": [
                        {"symbol": "AMZN", "exchange": "NASDAQ"},
                        {"symbol": "META", "exchange": "NASDAQ"},
                    ],
                    
                    # 주문 블록 연결
                    "order_id": "trailing_stop_order",
                    
                    # ========================================
                    # 조건들 (3계층 다중 중첩 - 하위 → 상위 순차 실행)
                    # ========================================
                    "conditions": [
                        # ========================
                        # 1계층: 최상위 조건 (ADX) - 하위 통과 후 실행
                        # ========================
                        {
                            "condition_id": "ADX",
                            "weight": 0.4,
                            "params": {
                                "appkey": os.getenv("APPKEY"),
                                "appsecretkey": os.getenv("APPSECRET"),
                                "period": 14,
                                "threshold": 20,  # ADX > 20 = 추세 존재
                            },
                            
                            # ========================
                            # 2계층: 중간 중첩 (at_least) - 먼저 실행
                            # ========================
                            # 볼린저밴드, CCI, 3계층 결과 중 1개 이상 통과
                            "logic": "at_least",
                            "threshold": 1,
                            "conditions": [
                                # 2계층 조건 1: 볼린저밴드
                                {
                                    "condition_id": "BollingerBands",
                                    "weight": 0.3,
                                    "params": {
                                        "appkey": os.getenv("APPKEY"),
                                        "appsecretkey": os.getenv("APPSECRET"),
                                        "period": 20,
                                        "std_dev": 2.0,
                                    },
                                },
                                # 2계층 조건 2: CCI
                                {
                                    "condition_id": "CCI",
                                    "weight": 0.3,
                                    "params": {
                                        "appkey": os.getenv("APPKEY"),
                                        "appsecretkey": os.getenv("APPSECRET"),
                                        "period": 20,
                                    },
                                },
                                # ========================
                                # 3계층: 최하위 중첩 (weighted) - 가장 먼저 실행
                                # ========================
                                # OBV와 VolumeSpike의 가중치 합 >= 0.6
                                {
                                    "logic": "weighted",
                                    "threshold": 0.6,  # 가중치 합 0.6 이상
                                    "conditions": [
                                        # 3계층 조건 1: OBV (거래량 누적)
                                        {
                                            "condition_id": "OBV",
                                            "weight": 0.4,
                                            "params": {
                                                "appkey": os.getenv("APPKEY"),
                                                "appsecretkey": os.getenv("APPSECRET"),
                                                "period": 20,
                                            },
                                        },
                                        # 3계층 조건 2: VolumeSpike (거래량 급증) - 커스텀 플러그인
                                        {
                                            "condition_id": "VolumeSpike",
                                            "weight": 0.4,
                                            "params": {
                                                "appkey": os.getenv("APPKEY"),
                                                "appsecretkey": os.getenv("APPSECRET"),
                                                "lookback_period": 20,
                                                "spike_threshold": 1.5,
                                            },
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
            
            # ========================================
            # 4. 주문 정의 (orders) - 트레일링 스탑
            # ========================================
            "orders": [
                {
                    "order_id": "trailing_stop_order",
                    "description": "트레일링 스탑 매도 주문",
                    
                    # 주문 시간 설정
                    "order_time": {
                        "start": "09:30:00",
                        "end": "16:00:00",
                        "days": ["mon", "tue", "wed", "thu", "fri"],
                        "timezone": "America/New_York",
                        "behavior": "defer",
                        "max_delay_seconds": 86400,
                    },
                    
                    # 주문 조건: 트레일링 스탑
                    "condition": {
                        "condition_id": "TrailingStopSellManager",
                        "params": {
                            "appkey": os.getenv("APPKEY"),
                            "appsecretkey": os.getenv("APPSECRET"),
                            "trailing_percent": 5.0,  # 고점 대비 5% 하락 시 매도
                        },
                    },
                },
            ],
        }
    )
