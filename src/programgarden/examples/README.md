# ProgramGarden Examples

노드 기반 DSL 워크플로우 예제 모음 (36개)

> 모든 예제는 `workflow_editor/workflows/`로 이전되었습니다.

## 사용법

```python
from examples.workflow_editor.workflows import (
    get_all_categories,
    get_workflows_by_category,
    get_all_workflows,
    get_workflow_by_id,
)

# 카테고리 목록
categories = get_all_categories()

# 카테고리별 워크플로우
futures_workflows = get_workflows_by_category("futures")

# 전체 워크플로우 (36개)
all_workflows = get_all_workflows()

# ID로 조회
workflow = get_workflow_by_id("futures-01")
```

## 카테고리 (8개)

| 카테고리 | 아이콘 | 워크플로우 | 설명 |
|----------|--------|------------|------|
| infra | 🏗️ | 5개 | 시작, 스케줄, 거래시간, 브로커 연결, 실시간 데이터 |
| condition | ⚡ | 5개 | 단일 조건, 다중 조건, 가중치, at_least, 중첩 논리 |
| order | 🛒 | 6개 | 시장가, 지정가, 포지션사이징, 정정, 취소, 매수매도 |
| advanced | 🔧 | 5개 | 스크리너, 이벤트핸들러, 에러핸들러, 리스크가드, 그룹노드 |
| operation | ⚙️ | 6개 | 거래시간, 일시정지, 스냅샷, 다중시장, 장시간실행, 24h자동 |
| backtest | 📈 | 3개 | 단순백테스트, 자동배포, 주간스케줄 |
| **futures** | 🔥 | 3개 | **해외선물** 브로커, 잔고조회, 주문 |
| custom | ✨ | 3개 | 백테스트비교, 스파이더차트, 포트폴리오 |

## 워크플로우 에디터 실행

```bash
cd src/programgarden/examples/workflow_editor
poetry run python server.py
```

브라우저에서 http://localhost:8000 접속

## API 엔드포인트

| 엔드포인트 | 설명 |
|------------|------|
| `GET /categories` | 카테고리 목록 |
| `GET /categories/{id}/workflows` | 카테고리별 워크플로우 |
| `GET /workflows` | 전체 워크플로우 (카테고리 정보 포함) |
| `GET /workflow/{id}` | 특정 워크플로우 정의 |
| `POST /run/{id}` | 워크플로우 실행 |
| `POST /stop` | 실행 중지 |
| `GET /events` | SSE 이벤트 스트림 |

## 해외선물 (overseas_futures) 지원

해외선물은 모의투자를 지원합니다:

```python
# 해외선물 브로커 연결 (모의투자)
workflow = get_workflow_by_id("futures-01")

# 환경변수 설정 (로컬 개발용)
# APPKEY_FUTURE_FAKE, APPSECRET_FUTURE_FAKE
```

> ⚠️ 해외주식(overseas_stock)은 모의투자를 지원하지 않습니다.
|----------|-----------|------|
| Infra | StartNode, BrokerNode | 01-04 |
| Trigger | ScheduleNode, TradingHoursFilterNode, ExchangeStatusNode | 02-03, 22 |
| Symbol | WatchlistNode, MarketUniverseNode, ScreenerNode, SymbolFilterNode | 05, 17 |
| Realtime | RealMarketDataNode, RealAccountNode, RealOrderEventNode | 05, 14-15 |
| Condition | ConditionNode, LogicNode | 06-10 |
| Risk | PositionSizingNode, RiskGuardNode | 13, 20 |
| Order | NewOrderNode, ModifyOrderNode, CancelOrderNode | 11-15 |
| Event | EventHandlerNode, ErrorHandlerNode, AlertNode | 18-19 |
| Display | DisplayNode | 전체 |
| Group | GroupNode | 21 |
