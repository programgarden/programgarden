# ProgramGarden

ProgramGarden은 AI 시대에 맞춰 파이썬을 모르는 투자자도 개인화된 시스템 트레이딩을 자동으로 수행할 수 있게 돕는 노드 기반 자동매매 DSL(Domain Specific Language) 오픈소스입니다.

노드를 조합하여 워크플로우를 정의하고, 실행 엔진이 이를 자동으로 처리합니다. LS증권 OpenAPI를 메인으로 해외 주식/선물 거래 자동화를 지원합니다.

## 공식 문서 및 커뮤니티

- 비개발자 빠른 시작: https://programgarden.gitbook.io/docs/invest/non_dev_quick_guide
- 개발자 커스텀 가이드: https://programgarden.gitbook.io/docs/develop/custom_dsl
- 유튜브: https://www.youtube.com/@programgarden
- 실시간 오픈톡방: https://open.kakao.com/o/gKVObqUh

## 설치

```bash
pip install programgarden

# Poetry 사용 시 (개발 환경)
poetry add programgarden
```

요구 사항: Python 3.12+

## 빠른 시작

### 동기 실행

```python
from programgarden import ProgramGarden

pg = ProgramGarden()

# 워크플로우 검증
result = pg.validate(workflow_definition)

# 워크플로우 실행 (완료 대기)
job_state = pg.run(
    definition=workflow_definition,
    context={"param": "value"},
    secrets={"appkey": "...", "appsecret": "..."},
    wait=True,
    timeout=60.0,
)
```

### 비동기 실행

```python
from programgarden import ProgramGarden

pg = ProgramGarden()

# 워크플로우 비동기 실행 (리스너 연결)
job = await pg.run_async(
    definition=workflow_definition,
    context={"param": "value"},
    listeners=[MyExecutionListener()],
)

# 실행 중 제어
await job.stop()
```

### Dry Run (워크플로우 검증용 모의 실행)

실제 주문/알림/Realtime WebSocket 연결 없이 워크플로우를 검증합니다.

- ScheduleNode / TradingHoursFilterNode → 1 cycle 후 즉시 종료
- 주문 노드 → LS API 미호출, `{"order_id": "DRYRUN-<uuid>", "status": "simulated", ...}` 반환
- Realtime 노드 → WebSocket 미개방, `{"status": "skipped_dry_run"}` 반환
- Messaging 노드(Telegram 등) → no-op, `{"status": "simulated"}` 반환
- 조회/백테스트 노드 → 기존 동작 유지 (실제 API 경로)

```python
job = await pg.run_async(
    definition=workflow_definition,
    context={"dry_run": True},
    secrets={...},
)
```

### 워크플로우 정의 (JSON)

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "cred-1"},
    {"id": "account", "type": "OverseasStockAccountNode"},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "data": "{{ nodes.historical.values }}"}
  ],
  "edges": [
    {"from": "broker", "to": "account"},
    {"from": "account", "to": "rsi"}
  ],
  "credentials": [
    {
      "credential_id": "cred-1",
      "type": "broker_ls_overseas_stock",
      "data": [
        {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}
      ]
    }
  ]
}
```

## 주요 특징

- **노드 기반 DSL**: 72개 내장 노드를 조합하여 코딩 없이 자동매매 전략 구성
- **실시간 처리**: WebSocket 기반 실시간 시세, 계좌, 체결 이벤트 수신
- **AI Agent 통합**: LLMModelNode + AIAgentNode로 LLM 기반 분석/의사결정
- **플러그인 확장**: 67개 내장 전략 플러그인 (RSI, MACD, 볼린저밴드, 이치모쿠, 듀얼모멘텀, 터틀브레이크아웃 등)
- **ExecutionListener**: 10개 이상의 콜백으로 실행 상태 실시간 모니터링
- **위험 관리**: WorkflowRiskTracker로 HWM/drawdown 추적, 포지션 사이징
- **동적 노드 주입**: 런타임에 커스텀 노드 등록 및 실행

## 아키텍처

```
5-Layer Architecture:
1. Registry Layer   - 노드/플러그인 메타데이터 (72개 노드, 67개 플러그인)
2. Credential Layer - 인증 정보 관리
3. Definition Layer - JSON 워크플로우 정의 (노드, 엣지, 크레덴셜)
4. Job Layer        - 상태 유지 실행 인스턴스 (최대 24시간 장기 실행)
5. Event Layer      - ExecutionListener 콜백 이벤트
```

## ExecutionListener 콜백

| 콜백 | 설명 |
|------|------|
| `on_node_state_change` | 노드 실행 상태 변경 |
| `on_edge_state_change` | 엣지 실행 상태 변경 |
| `on_log` | 로그 이벤트 |
| `on_job_state_change` | Job 생명주기 |
| `on_display_data` | 차트/테이블 출력 데이터 |
| `on_workflow_pnl_update` | 실시간 수익률 (FIFO 기반) |
| `on_retry` | 노드 재시도 이벤트 |
| `on_token_usage` | AI 토큰 사용량 |
| `on_ai_tool_call` | AI Agent 도구 호출 |
| `on_llm_stream` | LLM 스트리밍 출력 |
| `on_risk_event` | 위험 임계값 이벤트 |
| `on_notification` | 투자자 알림 (시그널, 리스크, 워크플로우 상태, 스케줄, 재시도 소진) |

## 변경 로그

자세한 변경 사항은 `CHANGELOG.md`를 참고하세요.
