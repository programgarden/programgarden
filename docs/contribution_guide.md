# 자동화매매 오픈소스 성장에 기여하기

## 1. 개요

ProgramGarden은 오픈소스 프로젝트로, 커뮤니티의 기여를 통해 성장하고 있습니다. 이 가이드는 개발자들이 자신만의 커스텀 플러그인을 공유하거나, 코드를 개선하여 프로젝트에 기여하는 방법을 설명합니다.

외부 플러그인을 [`programgarden-community`](https://github.com/programgarden/programgarden_community)에 기여하면, 다른 사용자들이 트레이딩에 쉽게 사용할 수 있고, AI 바이브 코딩도 플러그인을 기반으로 노드 기반 DSL을 작성하여 비개발자가 쉽게 사용하도록 지원됩니다.

이는 시스템 트레이더의 생태계를 풍부하게 만드는데 큰 도움이 됩니다. 🚀

여러분의 기여가 더 나은 자동화매매 환경을 만드는 데 중요한 역할을 합니다!

---

## 2. 개발 환경 설정

### 요구 사항
- Python 3.10 이상
- Poetry (패키지 관리)

### 설치
1. 이 리포지토리를 클론합니다:
   ```bash
   git clone https://github.com/your-repo/programgarden_community.git
   cd programgarden_community
   ```

2. Poetry를 설치합니다 (아직 설치하지 않은 경우):
   ```bash
   pip install poetry
   ```

3. 의존성을 설치합니다:
   ```bash
   poetry install
   ```

4. 가상 환경을 활성화합니다:
   ```bash
   poetry shell
   ```

---

## 3. 커스텀 플러그인 공유하기

### 3.1. 플러그인 파일 위치 및 구조

커스텀 플러그인은 [`programgarden-community`](https://github.com/programgarden/programgarden_community)에 기여되며, 상품에 맞는 각 플러그인별로 **전용 폴더**를 만들어야 합니다. 폴더 이름은 플러그인의 `클래스` 이름과 동일하게 만드는 것을 추천드립니다.

| 상품 | 플러그인 유형 | 폴더 경로 |
| --- | --- | --- |
| 해외주식 (`overseas_stock`) | 조건 분석 | `programgarden_community/overseas_stock/strategy_conditions/{Plugin ID}/` |
|  | 신규 주문 | `programgarden_community/overseas_stock/new_order_conditions/{Plugin ID}/` |
|  | 정정 주문 | `programgarden_community/overseas_stock/modify_order_conditions/{Plugin ID}/` |
|  | 취소 주문 | `programgarden_community/overseas_stock/cancel_order_conditions/{Plugin ID}/` |
| 해외선물 (`overseas_futureoption`) | 조건 분석 | `programgarden_community/overseas_futureoption/strategy_conditions/{Plugin ID}/` |
|  | 신규 주문 | `programgarden_community/overseas_futureoption/new_order_conditions/{Plugin ID}/` |
|  | 정정 주문 | `programgarden_community/overseas_futureoption/modify_order_conditions/{Plugin ID}/` |
|  | 취소 주문 | `programgarden_community/overseas_futureoption/cancel_order_conditions/{Plugin ID}/` |

각 플러그인 폴더에는 다음 파일들이 **필수**로 포함되어야 합니다:

1. **`__init__.py`**: 플러그인 클래스를 정의하고, `from . import *`로 내보내세요.
2. **`README.md`**: 플러그인의 상세 설명, 사용법, 파라미터 설명을 작성하세요.

예시 파일 구조:

```
programgarden_community/overseas_stock/
├── strategy_conditions/
│   └── MySMACondition/
│       ├── __init__.py
│       └── README.md
├── new_order_conditions/
│   └── MyBuyStrategy/
│       ├── __init__.py
│       └── README.md
├── modify_order_conditions/
│   └── MyModifyStrategy/
│       ├── __init__.py
│       └── README.md
└── cancel_order_conditions/
    └── MyCancelStrategy/
        ├── __init__.py
        └── README.md
```

### 3.2. 플러그인 파일 작성

커스텀 플러그인 클래스를 작성할 때는 다음을 준수하세요:

* [커스텀 DSL 개발자 가이드](custom_dsl.md)를 참고하여 클래스를 구현하세요.
* 클래스 이름은 명확하고, 고유하게 지으세요.
* `id` 속성은 클래스명과 맞춰주세요.
* **`version` 필드를 반드시 추가**하세요 (예: `"1.0.0"`).
* **파라미터 스키마를 Pydantic으로 정의**하여 외부 사용자가 쉽게 파라미터 정보를 조회할 수 있도록 하세요.

#### 플러그인 필수 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | str | 플러그인 고유 ID (클래스명과 동일 권장) |
| `version` | str | 버전 (예: "1.0.0") |
| `description` | str | 설명 |
| `securities` | List[str] | 지원 증권사 |
| `parameter_schema` | dict | Pydantic 모델의 JSON Schema (선택) |

#### 파라미터 정의 규칙 (Pydantic Field)

외부 사용자가 플러그인의 파라미터 정보를 JSON 형태로 받을 수 있도록, **Pydantic 모델**을 사용하여 파라미터를 정의해야 합니다.

**필수 규칙:**

1. **Pydantic BaseModel 사용**: 플러그인 클래스와 별도로 `{PluginName}Params` 클래스를 생성하세요.
2. **Field 정의**: 모든 필드는 `Field()`를 사용하여 메타데이터를 포함하세요.
   - `title`: 필드의 한글 이름 (UI에 표시)
   - `description`: 상세 설명 (필수 조건, 제약사항 포함)
   - `json_schema_extra={"example": ...}`: 예시값 (직접 `example=` 사용 금지)
3. **유효성 검사**: 숫자 필드에는 적절한 검증을 추가하세요.
   - `gt=0`: 0보다 큰 값
   - `ge=0`: 0 이상의 값
   - `le=1`: 1 이하의 값
4. **parameter_schema 속성**: 플러그인 클래스에 `parameter_schema: dict = {PluginName}Params.model_json_schema()` 추가

**파라미터 정의 예시:**

```python
from pydantic import BaseModel, Field
from typing import Optional

class MySMAConditionParams(BaseModel):
    """
    나만의 SMA 기반 조건 파라미터
    
    외부 사용자가 이 플러그인을 사용할 때 필요한 파라미터를 정의합니다.
    """
    
    short_period: int = Field(
        5,
        title="단기 이동평균 기간",
        description="단기 이동평균을 계산할 기간 (예: 5일)",
        gt=0,
        json_schema_extra={"example": 5}
    )
    
    long_period: int = Field(
        20,
        title="장기 이동평균 기간",
        description="장기 이동평균을 계산할 기간 (예: 20일)",
        gt=0,
        json_schema_extra={"example": 20}
    )
    
    threshold: Optional[float] = Field(
        None,
        title="임계값",
        description="매수/매도 신호를 발생시킬 임계값 (%)",
        ge=0,
        le=100,
        json_schema_extra={"example": 5.0}
    )
```

#### __init__.py 예시

플러그인 폴더의 `__init__.py` 파일에 Pydantic 파라미터 모델과 플러그인 클래스를 모두 정의하세요:

```python
from pydantic import BaseModel, Field
from programgarden_core import (
    BaseStrategyConditionOverseasStock,
    BaseStrategyConditionResponseOverseasStockType,
)


class MySMAConditionParams(BaseModel):
    """나만의 SMA 기반 조건 파라미터"""
    
    short_period: int = Field(
        5,
        title="단기 이동평균 기간",
        description="단기 이동평균을 계산할 기간",
        gt=0,
        json_schema_extra={"example": 5}
    )
    
    long_period: int = Field(
        20,
        title="장기 이동평균 기간",
        description="장기 이동평균을 계산할 기간",
        gt=0,
        json_schema_extra={"example": 20}
    )


class MySMACondition(BaseStrategyConditionOverseasStock):
    id: str = "MySMACondition"
    version: str = "1.0.0"
    name: str = "나만의 SMA 기반 조건"
    description: str = "매수/매도 신호를 생성합니다."
    securities: list = ["ls-sec.co.kr"]
    parameter_schema: dict = MySMAConditionParams.model_json_schema()

    def __init__(self, short_period: int = 5, long_period: int = 20, **kwargs):
        super().__init__()
        self.short_period = short_period
        self.long_period = long_period

    async def execute(self) -> BaseStrategyConditionResponseOverseasStockType:
        symbol = self.symbol or {}
        # 구현 로직
        is_cross = True  # 실제 로직으로 대체
        return {
            "condition_id": self.id,
            "success": is_cross,
            "symbol": symbol.get("symbol", ""),
            "exchcd": symbol.get("exchcd", ""),
            "data": {"short": self.short_period, "long": self.long_period},
            "weight": 1 if is_cross else 0,
            "product": "overseas_stock",
            "analysis": {
                "time_series": [...],
                "threshold": {"value": 0, "direction": "cross"},
            },
        }


__all__ = ["MySMACondition"]
```

이렇게 정의하면 외부 사용자가 `MySMACondition.parameter_schema`를 통해 다음과 같은 JSON Schema를 받을 수 있습니다:

```json
{
  "title": "MySMAConditionParams",
  "type": "object",
  "properties": {
    "short_period": {
      "type": "integer",
      "title": "단기 이동평균 기간",
      "description": "단기 이동평균을 계산할 기간",
      "example": 5,
      "exclusiveMinimum": 0
    },
    "long_period": {
      "type": "integer",
      "title": "장기 이동평균 기간",
      "description": "장기 이동평균을 계산할 기간",
      "example": 20,
      "exclusiveMinimum": 0
    }
  },
  "required": ["short_period", "long_period"]
}
```

#### README.md 예시

플러그인 폴더의 `README.md` 파일에 플러그인 설명을 작성하세요:

```markdown
# 작성자 정보
name: 홍길동
email: abc@abc.com
sns: https://youtube.com/abc

## 설명
단기 SMA와 장기 SMA의 교차를 감지하여 매수/매도 시점을 결정합니다.

## 필요한 데이터 값
- `short_period` (int, 기본값: 5): 단기 이동평균 기간
- `long_period` (int, 기본값: 20): 장기 이동평균 기간

## DSL에서 사용하기

```json
{
  "id": "sma",
  "type": "ConditionNode",
  "plugin": "MySMACondition",
  "fields": {
    "short_period": 5,
    "long_period": 20
  }
}
```

## 주의사항
- 충분한 과거 데이터가 필요합니다.
- 변동성이 높은 시장에서는 신호가 빈번할 수 있습니다.
```

### 3.3. 테스트 및 검증

* 플러그인을 로컬에서 테스트하세요. [커스텀 DSL 개발자 가이드](custom_dsl.md)의 예시를 참고하여 DSL에 통합해 보세요.
* 코드가 Python 3.10+에서 정상 동작하는지 확인하세요.
* **폴더 구조 검증**: 플러그인 폴더에 `__init__.py`와 `README.md`가 모두 있는지 확인하세요. 누락 시 PR이 거부될 수 있습니다.
* **버전 필드 확인**: 플러그인 클래스에 `version` 필드가 있는지 확인하세요.

---

## 4. 커뮤니티 노드 기여하기

플러그인 외에도 **새로운 노드 타입**을 커뮤니티에 기여할 수 있습니다. 예: TelegramNode, SlackNode, DiscordNode 등.

### 4.1. 노드 vs 플러그인

| 구분 | 플러그인 | 노드 |
|------|----------|------|
| 용도 | 기존 노드의 로직 확장 | 완전히 새로운 기능 |
| 예시 | RSI, MACD, BollingerBands | TelegramNode, SlackNode |
| 베이스 | `BaseStrategyCondition*` | `BaseNotificationNode`, `BaseNode` |
| 위치 | `plugins/` | `nodes/` |

### 4.2. 노드 파일 구조

```
programgarden_community/
├── nodes/
│   ├── __init__.py
│   └── messaging/
│       ├── __init__.py
│       ├── telegram.py      # TelegramNode
│       ├── slack.py         # SlackNode
│       └── discord.py       # DiscordNode
└── nodes_registry.py        # 노드 등록
```

### 4.3. 알림 노드 작성하기

알림/메시징 노드는 `BaseNotificationNode`를 상속합니다:

```python
from typing import Literal, Optional, Dict, Any, ClassVar
from pydantic import Field
from programgarden_core.nodes.base import BaseNotificationNode


class SlackNode(BaseNotificationNode):
    """Slack 메시지 전송 노드"""
    
    type: Literal["SlackNode"] = "SlackNode"
    description: str = "Send messages via Slack Webhook"
    
    # 노드 아이콘 (선택)
    _img_url: ClassVar[str] = "https://example.com/slack-logo.svg"
    
    # Credential에서 자동 주입되는 필드들
    # credential_id를 설정하면 GenericNodeExecutor가 자동으로 값을 채워줍니다
    webhook_url: Optional[str] = Field(
        default=None,
        description="Slack Webhook URL. credential_id 사용 시 자동 주입됨",
    )
    channel: Optional[str] = Field(
        default=None,
        description="Slack channel name",
    )
    
    async def execute(self, context: Any) -> Dict[str, Any]:
        """
        Slack 메시지 전송
        
        Note:
            credential_id가 설정되어 있으면 webhook_url이 자동 주입됩니다.
            self.webhook_url을 바로 사용하면 됩니다.
        """
        if not self.webhook_url:
            return {"sent": False, "error": "webhook_url required"}
        
        # 템플릿 렌더링
        event_data = getattr(context, "event_data", {}) or {}
        message = context.render_template(self.template, event_data)
        
        # Slack API 호출
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(self.webhook_url, json={"text": message}) as resp:
                if resp.status == 200:
                    return {"sent": True}
                else:
                    return {"sent": False, "error": f"HTTP {resp.status}"}
```

### 4.4. Credential 자동 주입 패턴

**핵심**: 필드만 선언하면 credential 값이 자동 주입됩니다!

```python
# ❌ 예전 방식 (더 이상 필요 없음)
class MyNode(BaseNotificationNode):
    _credential_keys = ["api_key"]  # 불필요
    
    async def execute(self, context):
        creds = self.resolve_credentials(context)  # 불필요
        api_key = creds["api_key"]

# ✅ 새로운 방식 (권장)
class MyNode(BaseNotificationNode):
    api_key: Optional[str] = None  # 필드만 선언
    
    async def execute(self, context):
        api_key = self.api_key  # 바로 사용!
```

**동작 원리**:
1. 워크플로우에서 `credential_id: "my-credential"` 설정
2. `GenericNodeExecutor`가 실행 전에 credential store에서 값 조회
3. credential의 필드명과 노드의 필드명이 일치하면 자동 주입
4. `execute()`에서 `self.필드명`으로 바로 사용

**우선순위**: 직접 설정 값 > credential 값

### 4.5. 노드 등록하기

`nodes_registry.py`에 노드를 등록합니다:

```python
def register_all_nodes():
    """커뮤니티 노드를 NodeTypeRegistry에 등록"""
    from programgarden_core.registry import NodeTypeRegistry
    from programgarden_community.nodes.messaging.telegram import TelegramNode
    from programgarden_community.nodes.messaging.slack import SlackNode
    
    registry = NodeTypeRegistry()
    registry.register_external(TelegramNode)
    registry.register_external(SlackNode)
```

### 4.6. 워크플로우에서 사용하기

```json
{
  "nodes": [
    {
      "id": "telegram",
      "type": "TelegramNode",
      "credential_id": "telegram-bot-001",
      "template": "🎯 체결: {{symbol}} {{quantity}}주 @ {{price}}",
      "on": ["order_filled"]
    }
  ]
}
```

credential store에 다음과 같이 저장:
```json
{
  "telegram-bot-001": {
    "bot_token": "123456:ABC-DEF...",
    "chat_id": "880982510"
  }
}
```

---

## 5. 코드 스타일

- Python 코드 스타일 가이드 (PEP 8)를 따릅니다.
- Black 포맷터를 사용합니다:
  ```bash
  poetry run black .
  ```
- Flake8로 린팅합니다:
  ```bash
  poetry run flake8 .
  ```

---

## 6. 테스트

모든 변경 사항은 테스트를 통과해야 합니다: DSL 언어에서 커스텀하여 정상 동작을 확인하세요.

```python
from programgarden import Programgarden

pg = Programgarden()

pg.run(workflow={
    "nodes": [
        {"id": "broker", "type": "BrokerNode", "config": {...}},
        {
            "id": "myCondition",
            "type": "ConditionNode",
            "plugin": "MySMACondition",
            "fields": {"short_period": 5, "long_period": 20}
        },
        ...
    ],
    "edges": [...]
})
```

---

## 7. 코드 기여 및 PR 제출

버그 수정이나 기능 추가를 위해 코드를 기여하려면:

1. 이슈를 확인하거나 새 이슈를 만듭니다.
2. 브랜치를 생성합니다: `git checkout -b feature/your-feature-name`
3. 코드를 수정합니다.
4. 테스트를 실행합니다.
5. 커밋하고 푸시합니다.
6. GitHub에서 PR을 생성합니다.
   - 제목과 설명을 명확히 작성합니다.
   - 관련 이슈를 링크합니다.
   - 변경 사항을 요약합니다.

PR은 검토 후 병합됩니다. 피드백이 있을 수 있으니 적극적으로 응답 부탁드립니다.

---

## 8. 이슈 보고 및 토론

### 8.1. 이슈 및 토론 참여

* 버그, 기능 요청, 질문 등이 있으면 GitHub Issues를 사용하세요.
* Github Discussions 탭에서 일반적인 토론에 참여하세요.
* 커뮤니티와 소통하며 아이디어를 공유하세요.

---

## 9. 라이선스 및 윤리적 고려사항

* ProgramGarden은 AGPL-3.0 라이선스를 사용합니다. 기여 시 이 라이선스를 준수하세요.
* 저작권이 있는 코드를 복사하지 마세요.
* 플러그인이 시장 조작이나 불공정 거래를 유발하지 않도록 하세요.

질문이 있으면 네이버카페(https://cafe.naver.com/programgarden)나 카카오톡 오픈톡방(https://open.kakao.com/o/gKVObqUh) 또는 GitHub Discussions를 이용하세요.

---

### 시스템 트레이딩 발전에 기여해주셔서 감사합니다!
