# 커뮤니티 전략 모음

이 문서는 ProgramGarden의 커뮤니티 폴더에 있는 외부 플러그인 전략들을 소개합니다.

## **🌎 해외주식**

### **종목추출전략(strategy_conditions)**
- [**SMAGoldenDeadCross**](../src/community/programgarden_community/overseas_stock/strategy_conditions/sma_golden_dead/README.md)
    - 최근 2봉 이내에 데드→골든 전환(골든 가격 > 데드 가격)이 발생했으며 현재 이평선 정렬이 골든인 경우

### **신규매수전략(new_buy_conditions)**
- [**StockSplitFunds**](../src/community/programgarden_community/overseas_stock/new_buy_conditions/stock_split_funds/README.md)
    - 사용 가능한 예수금의 설정된 비율을 사용해 자금을 균등 분할하여 최대 지정 수의 해외 주식에 매수 주문을 생성하는 전략입니다.

### **신규매도전략(new_sell_conditions)**
- [**BasicLossCutManager**](../src/community/programgarden_community/overseas_stock/new_sell_conditions/loss_cut/README.md)
    - 보유 주식의 손익률이 설정된 임계값 이하로 떨어지면 자동으로 매도 주문을 생성해 손실을 제한하는 자동 손절매 전략

<br>

## **🌏 해외선물옵션**
전략 공간을 구축중입니다.