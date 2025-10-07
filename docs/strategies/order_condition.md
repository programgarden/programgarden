# **신규매매전략**

신규 매수 또는 매도 주문 방식을 설정하는 전략들을 모아두었습니다. 원하는 전략이 없다면, 카페에 전략 제작을 요청해주세요([요청하기](https://cafe.naver.com/f-e/cafes/30041992/menus/204?viewType=L)). 또는 파이썬으로 직접 전략을 제작하고 추가하여 ([만드는 방법 보기](../custom_dsl.md)) 사용하실 수도 있습니다.

 | 상품 | 전략 ID | 설명 | 지원 |
|-----|----------|------|-----|
| 해외주식 | [**StockSplitFunds**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_stock/new_order_conditions/stock_split_funds/) | 사용 가능한 예수금의 설정된 비율을 사용해 자금을 균등 분할하여 최대 지정 수의 해외 주식에 매수 주문을 생성하는 전략입니다.  | 신규매수 |
| 해외주식 | [**BasicLossCutManager**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_stock/new_order_conditions/loss_cut/) | 보유 주식의 손익률이 설정된 임계값 이하로 떨어지면 자동으로 매도 주문을 생성해 손실을 제한하는 자동 손절매 전략 | 신규매도 |
| 해외주식 | [**TrackingPriceModifyBuy**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_stock/modify_order_conditions/tracking_price/) | 해외 주식 정정매수/매도 시 주문 가격이 시장 가격과 일정 틱 이상 차이가 날 경우, 자동으로 1호가 가격으로 주문을 수정하는 전략입니다. 주문이 체결되지 않는 상황을 방지하여 효율적인 매매 실행을 돕습니다. | 정정매수, 정정매도 |
| 해외주식 | [**PriceRangeCanceller**](https://github.com/programgarden/programgarden_community/tree/main/programgarden_community/overseas_stock/cancel_order_conditions/price_range_canceller) | 해외 주식에서 주문 가격과 현재 시장 가격의 차이가 설정한 임계값보다 커지면 자동으로 주문을 취소하는 기능입니다. 가격이 불리하게 변동할 때 손실을 막고, 주문을 효율적으로 관리합니다. | 주문취소 |