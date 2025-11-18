# **종목추출전략**
거래를 하기 위한 종목을 필터링하는 전략들을 모아두었습니다. 원하는 전략이 없다면, 카페에 전략 제작을 요청해주세요([요청하기](https://cafe.naver.com/f-e/cafes/30041992/menus/204?viewType=L)). 또는 파이썬으로 직접 전략을 제작하고 추가하여 ([만드는 방법 보기](../custom_dsl.md)) 사용하실 수도 있습니다.

 | 상품 | 전략 ID | 설명 | 지원 |
|-----|----------|------|-----|
| 해외주식 | [**SMAGoldenDeadCross**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_stock/strategy_conditions/sma_golden_dead/) | 최근 2봉 이내에 데드→골든 전환(골든 가격 > 데드 가격)이 발생했으며 현재 이평선 정렬이 골든인 경우 | 종목 분석 |
| 해외주식 | [**StockSMAEMACross**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_stock/strategy_conditions/sma_ema_trend_cross/) | 느린 SMA와 빠른 EMA의 위치·교차를 비교해 골든/데드 전환과 진행 중인 추세 방향을 라벨로 제공합니다. | 종목 분석 |
| 해외주식 | [**StockMACDShift**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_stock/strategy_conditions/macd_momentum_shift/) | MACD·시그널선·히스토그램을 함께 계산해 최근 골든/데드 교차와 모멘텀 이동 방향을 요약합니다. | 종목 분석 |
| 해외주식 | [**StockRSIStochastic**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_stock/strategy_conditions/rsi_stochastic_oscillator/) | RSI와 스토캐스틱 슬로우가 동시에 과열/침체 구간에 진입하는지를 감시해 반등·차익실현 타이밍을 알립니다. | 종목 분석 |
| 해외선물 | [**FuturesSMAEMACross**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_futureoption/strategy_conditions/sma_ema_trend_cross/) | 해외선물 가격의 SMA·EMA 교차와 정렬을 자동으로 평가해 상승/하락 전환 신호를 제공합니다. | 종목 분석 |
| 해외선물 | [**FuturesMACDShift**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_futureoption/strategy_conditions/macd_momentum_shift/) | MACD 교차·히스토그램 흐름을 통합 분석해 최근 롱/숏 모멘텀 전환과 추천 포지션을 제안합니다. | 종목 분석 |
| 해외선물 | [**FuturesRSIStochastic**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_futureoption/strategy_conditions/rsi_stochastic_oscillator/) | RSI와 스토캐스틱이 동시에 과매수·과매도 영역에 진입하는 시점을 포착해 리스크 완화 구간을 알려줍니다. | 종목 분석 |