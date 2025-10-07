# **종목추출전략**
거래를 하기 위한 종목을 필터링하는 전략들을 모아두었습니다. 원하는 전략이 없다면, 카페에 전략 제작을 요청해주세요([요청하기](https://cafe.naver.com/f-e/cafes/30041992/menus/204?viewType=L)). 또는 파이썬으로 직접 전략을 제작하고 추가하여 ([만드는 방법 보기](../custom_dsl.md)) 사용하실 수도 있습니다.

 | 상품 | 전략 ID | 설명 | 지원 |
|-----|----------|------|-----|
| 해외주식 | [**SMAGoldenDeadCross**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_stock/strategy_conditions/sma_golden_dead/) | 최근 2봉 이내에 데드→골든 전환(골든 가격 > 데드 가격)이 발생했으며 현재 이평선 정렬이 골든인 경우 | 종목 분석 |