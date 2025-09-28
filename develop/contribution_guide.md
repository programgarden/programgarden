# 자동화매매 오픈소스 성장에 기여하기

## 1. 개요

ProgramGarden은 오픈소스 프로젝트로, 커뮤니티의 기여를 통해 성장하고 있습니다. 이 가이드는 개발자들이 자신만의 커스텀 전략을 공유하거나, 코드를 개선하여 프로젝트에 기여하는 방법을 설명합니다.

커스텀 전략을 ProgramGarden Community에 기여하면, 다른 사용자들이 쉽게 사용할 수 있고, AI 바이브 코딩도 전략을 기반으로 DSL을 작성하여 비개발자가 쉽게 사용하도록 지원됩니다.

이는 시스템 트레이더의 생태계를 풍부하게 만듭니다.

\


## 2. 커스텀 전략 공유하기

### 2.1. 전략 파일 위치 및 구조

커스텀 전략은 ProgramGarden Community에 기여되며, 상품에 맞는 각 전략별로 **전용 폴더**를 만들어야 합니다. 폴더 이름은 전략의 `클래스` 이름과 동일하게 하세요.

* **컨디션 클래스**: `src/community/programgarden_community/overseas_stock/strategy_conditions/{StrategyID}/` 폴더 생성
* **신규매수 전략 클래스**: `src/community/programgarden_community/overseas_stock/new_buy_conditions/{StrategyID}/` 폴더 생성
* **신규매도 전략 클래스**: `src/community/programgarden_community/overseas_stock/new_sell_conditions/{StrategyID}/` 폴더 생성

외에도 상품과 전략 유형에 따라 적절한 디렉토리에 폴더를 생성하세요. 각 전략 폴더에는 다음 파일들이 **필수**로 포함되어야 합니다:

1. **`__init__.py`**: 전략 클래스를 정의하고, `from . import *`로 내보내세요.
2. **`README.md`**: 전략의 상세 설명, 사용법, 파라미터 설명을 작성하세요.

예시 파일 구조:

```
src/community/programgarden_community/overseas_stock/
├── strategy_conditions/
│   └── MySMACondition/
│       ├── __init__.py
│       └── README.md
├── new_buy_conditions/
│   └── MyBuyStrategy/
│       ├── __init__.py
│       └── README.md
└── new_sell_conditions/
    └── MySellStrategy/
        ├── __init__.py
        └── README.md
    ...
```

### 3.2. 전략 파일 작성

커스텀 전략 클래스를 작성할 때는 다음을 준수하세요:

* [커스텀 DSL 개발자 가이드](custom_dsl.md)를 참고하여 클래스를 구현하세요.
* 클래스 이름은 명확하고, 고유하게 지으세요.
* `id` 속성은 클래스명과 맞춰주세요.

#### **init**.py 예시

전략 폴더의 `__init__.py` 파일에 클래스 정의를 작성하세요:

```python

from programgarden_core import BaseStrategyCondition, BaseStrategyConditionResponseType

class MySMACondition(BaseStrategyCondition):
    id: str = "MySMACondition"
    description: str = "나만의 SMA 기반 컨디션"

    def __init__(self, short_period: int = 5, long_period: int = 20, **kwargs):
        super().__init__()
        self.short_period = short_period
        self.long_period = long_period

    async def execute(self) -> BaseStrategyConditionResponseType:
        # 구현 로직
        return {
            "condition_id": self.id,
            "success": True,
            "exchange": self.symbol.get("exchcd"),
            "symbol": self.symbol.get("symbol"),
            "data": []
        }
```

#### README.md 예시

전략 폴더의 `README.md` 파일에 전략 설명을 작성하세요:

```markdown
# 작성자 정보
name: 홍길동
email: abc@abc.com
sns: https://youtube.com/abc

## 설명
단기 SMA와 장기 SMA의 교차를 감지하여 매수/매도 시점을 결정합니다.

## 파라미터
- `short_period` (int, 기본값: 5): 단기 이동평균 기간
- `long_period` (int, 기본값: 20): 장기 이동평균 기간

## 주의사항
- 충분한 과거 데이터가 필요합니다.
- 변동성이 높은 시장에서는 신호가 빈번할 수 있습니다.
```

### 3.3. 테스트 및 검증

* 전략을 로컬에서 테스트하세요. [커스텀 DSL 개발자 가이드](custom_dsl.md)의 예시를 참고하여 DSL에 통합해 보세요.
* 코드가 Python 3.9+에서 정상 동작하는지 확인하세요.
* **폴더 구조 검증**: 전략 폴더에 `__init__.py`와 `README.md`가 모두 있는지 확인하세요. 누락 시 PR이 거부될 수 있습니다.

\


## 4. 이슈 보고 및 토론

### 4.1. 이슈 및 토론 참여

* 버그, 기능 요청, 질문 등이 있으면 GitHub Issues를 사용하세요.
* Github Discussions 탭에서 일반적인 토론에 참여하세요.
* 커뮤니티와 소통하며 아이디어를 공유하세요.

\


## 5. 라이선스 및 윤리적 고려사항

* ProgramGarden은 AGPL-3.0 라이선스를 사용합니다. 기여 시 이 라이선스를 준수하세요.
* 저작권이 있는 코드를 복사하지 마세요.
* 전략이 시장 조작이나 불공정 거래를 유발하지 않도록 하세요.

\


질문이 있으면 Issues나 Discussions를 이용하세요. 여러분의 기여를 환영합니다! 🚀
