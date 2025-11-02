# Programgarden

Programgarden은 AI 시대 발전에 맞춰, AI 시대 발전에 맞춰, 파이썬을 모르는 투자자들도 쉽게 개인화된 시스템 트레이딩을 자동으로 이행할 수 있도록 돕는 시스템 트레이딩 전용 DSL(Domain Specific Language, 특정 도메인 언어) 오픈소스 프로젝트입니다.

수십만 가지의 전략 조합을 통해 맞춤형 자동화 매매를 구현하며, LS증권의 OpenAPI를 메인으로 활용하여 해외 주식 거래를 안전하고 효율적으로 처리합니다. 다른 증권사는 커스터마이징을 통해서 이용 할 수 있습니다.

## 특징

- **자동화 전략 실행**: 스케줄 기반으로 전략을 실행하고 조건을 평가합니다.
- **실시간 주문 처리**: 매수/매도 주문을 자동으로 실행합니다.
- **증권사 API 통합**: 증권사 API를 사용하여 안전한 거래를 지원합니다.
- **플러그인 기반 조건**: 다양한 자동화매매 전략(예: 추세전략, 손절매)을 [커뮤니티의 플러그인](https://github.com/programgarden/programgarden/tree/main/src/community)으로 확장 가능합니다.

## 공식 문서 및 커뮤니티

- 비개발자를 위한 빠른 시작 가이드를 참고하세요: [https://programgarden.gitbook.io/docs/invest/non_dev_quick_guide](https://programgarden.gitbook.io/docs/invest/non_dev_quick_guide)
- 개발자는 파이썬으로 커스텀이 가능합니다.
[https://programgarden.gitbook.io/docs/develop/custom_dsl](https://programgarden.gitbook.io/docs/develop/custom_dsl)
- 유튜브: https://www.youtube.com/@programgarden
- 실시간 오픈톡방: https://open.kakao.com/o/gKVObqUh


## 사용 방법

### 설치

```bash
pip install programgarden

# 또는 poetry 환경에서는
poetry add programgarden
```

요구 사항: Python 3.9+

### 빠른 시작

### 1. 환경 변수 설정
LS증권에서 API 키를 발급받아 `.env` 파일에 아래와 같이 입력합니다.
```bash
APPKEY=your_stock_appkey
APPSECRET=your_stock_appsecret
APPKEY_FUTURE=your_futures_appkey
APPSECRET_FUTURE=your_futures_appsecret
```

### 2. 해외주식 자동매매 예제 실행

`example/auto_overseas_stock.py`를 참고하면, 아래와 같이 Programgarden을 실행할 수 있습니다.

```python
from dotenv import load_dotenv
from programgarden import Programgarden
import os

load_dotenv()

pg = Programgarden()

# 전략 수행 응답 콜백 등록
pg.on_strategies_message(
	callback=lambda message: print(f"Strategies: {message.get('condition_id')}")
)

# 실시간 주문 응답 콜백 등록
pg.on_real_order_message(
	callback=lambda message: print(f"Real Order Message: {message.get('order_type')}, {message.get('message')}")
)

pg.run(
	system={
		"settings": {...},
		"securities": {...},
		"strategies": [...],
		"orders": [...]
	}
)
```

### 3. 해외선물 신규/정정/취소 주문 예제

`example/new_order_overseasfutures.py`, `modify_order_overseas_futures.py`, `cancel_order_overseas_futures.py`를 참고하면, 직접 전략/주문 클래스를 만들어서 시스템에 등록할 수 있습니다.

예시:
```python
from programgarden_core import BaseStrategyConditionOverseasFutures, BaseNewOrderOverseasFutures

class MyStrategy(BaseStrategyConditionOverseasFutures):
	... # 조건 구현

class MyOrder(BaseNewOrderOverseasFutures):
	... # 주문 구현

pg = Programgarden()
pg.run(system={
	"settings": {...},
	"securities": {...},
	"strategies": [
		{"conditions": [MyStrategy()]}
	],
	"orders": [
		{"condition": MyOrder()}
	]
})
```

### 4. 실시간 주문/체결 리스너 등록
DSL로 작성한 전략과 주문이 실행되는 동안, 실시간으로 전략 수행 결과와 주문 체결 결과를 수신하려면 리스너를 등록하면 됩니다.

```python
# 실시간 전략/분석 리스너 등록
pg.on_strategies_message(
	callback=lambda message: print(f"Strategies: {message}")
)

# 실시간 주문 리스너 등록
pg.on_real_order_message(
	callback=lambda message: print(
		f"Real Order Message: {message.get('order_type')}, {message.get('message')}"
	)
)

# 실시간 에러 리스너 등록
pg.on_error_message(
    callback=lambda message: print(f"Error Message: {message}")
)
```

### 예제 폴더 구조
자동화매매를 어떻게 구현하는지 보여주는 단순한 예제를 모았으며 누구나 쉽게 다양한 구조의 자동매매 시스템을 구현할 수 있습니다.
```
example/
├── auto_overseas_stock.py           # 해외주식 자동매매 예제
├── new_order_overseasfutures.py     # 해외선물 신규주문 예제
├── modify_order_overseas_futures.py # 해외선물 주문정정 예제
├── cancel_order_overseas_futures.py # 해외선물 주문취소 예제
```
