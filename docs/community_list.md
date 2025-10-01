# 커뮤니티 전략 모음

이 문서는 ProgramGarden의 커뮤니티 폴더에 있는 외부 플러그인 전략들을 소개합니다. 외부 플러그인은 커뮤니티에서 개발 및 공유한 전략들로, 사용자가 직접 추가하여 활용할 수 있습니다. 또한 커뮤니티 전략을 원하지 않으신다면 직접 파이썬으로 커스텀[DSL 커스텀 하기](custom_dsl.md)하여 사용하실 수도 있습니다.

## **🌎 해외주식**

### **종목추출전략(strategy\_conditions)**

* [**SMAGoldenDeadCross**](../src/community/programgarden_community/overseas_stock/strategy_conditions/sma_golden_dead/)
  * 최근 2봉 이내에 데드→골든 전환(골든 가격 > 데드 가격)이 발생했으며 현재 이평선 정렬이 골든인 경우

### **신규매매전략(new\_order\_conditions)**

* [**StockSplitFunds**](../src/community/programgarden_community/overseas_stock/new_order_conditions/stock_split_funds/)
  * 사용 가능한 예수금의 설정된 비율을 사용해 자금을 균등 분할하여 최대 지정 수의 해외 주식에 매수 주문을 생성하는 전략입니다.

* [**BasicLossCutManager**](../src/community/programgarden_community/overseas_stock/new_order_conditions/loss_cut/)
  * 보유 주식의 손익률이 설정된 임계값 이하로 떨어지면 자동으로 매도 주문을 생성해 손실을 제한하는 자동 손절매 전략

### **정정매매 전략(modify\_order\_conditions)**

* [**TrackingPriceModifyBuy**](../src/community/programgarden_community/overseas_stock/modify_order_conditions/tracking_price/)
  * 해외 주식 정정매수 시 주문 가격이 시장 가격과 일정 틱 이상 차이가 날 경우, 자동으로 1호가 가격으로 주문을 수정하는 전략입니다. 주문이 체결되지 않는 상황을 방지하여 효율적인 매매 실행을 돕습니다.

### **취소매매 전략(cancel_order_conditions)**

* [**PriceRangeCanceller**](../src/community/programgarden_community/overseas_stock/cancel_order_conditions/price_range_canceller/)
  * 해외 주식에서 주문 가격과 현재 시장 가격의 차이가 설정한 임계값보다 커지면 자동으로 주문을 취소하는 기능입니다. 가격이 불리하게 변동할 때 손실을 막고, 주문을 효율적으로 관리합니다.




## **🌏 해외선물옵션**

전략 공간을 구축중입니다.
