# TrackingPriceModifyBuy - 가격 추적 정정매수 전략

## 작성자 정보

- 작성자: 프로그램 동산
- 유튜브: https://youtube.com/@programgarden

## 개요

`TrackingPriceModifyBuy`는 해외 주식 정정매수 시 주문 가격이 시장 가격과 일정 틱 이상 차이가 날 경우, 자동으로 1호가 가격으로 주문을 수정하는 전략입니다. 이 전략은 주문이 체결되지 않는 상황을 방지하여 효율적인 매수 실행을 돕습니다.

## 개발 배경

해외 주식 매수 주문을 넣을 때, 주문 가격이 시장 가격과 너무 차이가 나면 주문이 체결되지 않을 수 있습니다. 특히 변동성이 높은 시장에서는 빠른 가격 변동으로 인해 주문이 유효하지 않게 될 수 있습니다. `TrackingPriceModifyBuy`는 이러한 문제를 해결하기 위해 주문 가격을 실시간으로 모니터링하고, 필요 시 1호가로 자동 수정하여 체결 확률을 높이는 것을 목표로 합니다.

## 전략의 목적

해외 주식 정정매수는 기존 주문의 가격을 조정하여 시장 상황에 맞게 최적화하는 과정입니다. 인간의 수동 조정은 지연과 실수를 유발할 수 있습니다. `TrackingPriceModifyBuy`는 자동화된 가격 추적을 통해 다음과 같은 목적을 달성합니다:

- **체결 확률 향상**: 주문 가격이 시장 가격과 너무 차이가 나지 않도록 자동 조정합니다.
- **효율성 증대**: 수동 모니터링의 번거로움을 줄이고, 실시간 대응을 가능하게 합니다.
- **리스크 관리**: 주문이 장기간 미체결되는 것을 방지하여 투자 기회를 놓치지 않습니다.

## 주요 기능

### 클래스 구조
- **상속**: `BaseModifyBuyOverseasStock`을 상속받아 표준화된 인터페이스를 따릅니다.
- **식별자**: `id = "TrackingPriceModifyBuy"`
- **설명**: `description = "가격 추적 정정매수"`
- **지원 증권사**: `securities = ["ls-sec.co.kr"]`

### 파라미터
- `appkey` (Optional[str]): LS증권 API 앱키 (로그인용).
- `appsecretkey` (Optional[str]): LS증권 API 앱시크릿키 (로그인용).
- `tick_threshold` (float, 기본값: 0.1): 가격 차이 임계값 (틱 단위). 주문 가격과 현재 가격의 차이가 이 값 이상일 때 정정 주문을 생성합니다.

### 동작 방식
1. LS증권 API에 로그인합니다 (필요 시).
2. 보유 주식 목록(`held_symbols`)을 순회합니다.
3. 각 주식의 기존 주문 가격과 현재 시장 가격을 비교합니다.
4. 가격 차이가 `tick_threshold` 이상인 경우:
   - 현재 가격(1호가)을 기준으로 정정 주문을 생성합니다.
   - 주문 유형: 정정 (`ord_ptn_code = "03"`)
   - 가격 유형: 지정가 (`ordprc_ptn_code = "00"`)
   - 가격: 현재 시장 가격
5. 생성된 정정 주문 목록을 반환합니다.

## 사용 예시

```python
from programgarden_community.overseas_stock.modify_buy_conditions.tracking_price import TrackingPriceModifyBuy

# 가격 차이 임계값을 0.5로 설정
tracking_modify = TrackingPriceModifyBuy(
    appkey="your_appkey",
    appsecretkey="your_appsecretkey",
    tick_threshold=0.5
)

# 전략 실행
results = await tracking_modify.execute()
```

## 주의사항

- 이 전략은 과거 데이터나 시뮬레이션에서 테스트된 후 실제 투자에 적용해야 합니다.
- API 키는 안전하게 관리해야 하며, 실제 투자 시 유효한 키를 사용하세요.
- 가격 차이 임계값은 시장 상황과 종목 특성에 따라 조정해야 합니다.
- 자동화된 전략이므로, 실행 전에 충분한 검토와 테스트를 권장합니다.
