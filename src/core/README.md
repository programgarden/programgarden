# ProgramGarden Core v2.0.0

노드 기반 DSL 시스템의 핵심 타입 정의 패키지입니다.

## 5-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  1. REGISTRY LAYER (메타데이터)                             │
│     NodeTypeRegistry, PluginRegistry                        │
├─────────────────────────────────────────────────────────────┤
│  2. CREDENTIAL LAYER (인증/보안)                            │
│     BrokerCredential                                        │
├─────────────────────────────────────────────────────────────┤
│  3. DEFINITION LAYER (전략 정의)                            │
│     WorkflowDefinition, Edge                                │
├─────────────────────────────────────────────────────────────┤
│  4. JOB LAYER (실행 인스턴스)                               │
│     WorkflowJob, JobState                                   │
├─────────────────────────────────────────────────────────────┤
│  5. EVENT LAYER (이벤트 히스토리)                           │
│     Event                                                   │
└─────────────────────────────────────────────────────────────┘
```

## 노드 타입 (26개, 11개 카테고리)

| Category | 용도 | 노드 수 |
|----------|------|--------|
| `infra` | 시작점/증권사 연결 | 2 |
| `realtime` | WebSocket 실시간 | 3 |
| `data` | REST API 조회 | 2 |
| `symbol` | 종목 소스/필터 | 4 |
| `trigger` | 스케줄/시간 필터 | 3 |
| `condition` | 조건 평가/조합 | 2 |
| `risk` | 리스크 관리 | 2 |
| `order` | 주문 실행 | 3 |
| `event` | 이벤트/알림 | 3 |
| `display` | 시각화 | 1 |
| `group` | 서브플로우 | 1 |

## 설치

```bash
pip install programgarden-core
```

## 사용 예시

```python
from programgarden_core import (
    WorkflowDefinition,
    Edge,
    NodeTypeRegistry,
    PluginRegistry,
)

# 노드 타입 레지스트리 조회
registry = NodeTypeRegistry()
print(registry.list_categories())

# 워크플로우 정의
workflow = WorkflowDefinition(
    id="my-strategy",
    name="My Trading Strategy",
    nodes=[
        {"id": "start", "type": "StartNode", "category": "infra"},
        {"id": "schedule", "type": "ScheduleNode", "category": "trigger", "cron": "*/5 * * * *"},
    ],
    edges=[
        Edge(from_port="start.start", to_port="schedule"),
    ],
)

# 구조 검증
errors = workflow.validate_structure()
if not errors:
    print("Valid workflow!")
```
