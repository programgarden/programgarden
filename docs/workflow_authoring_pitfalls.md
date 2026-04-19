# 워크플로우 JSON 작성 시 자주 놓치는 것

실전 봇(`scripts/live_bot/`) 실행하면서 확인된 구성 실수와 해결책.
새 워크플로우 작성 전 체크리스트로 사용 권장.

## 1. Edge 참조 노드가 실제로 정의되어 있는지

### 증상
```
❌ 워크플로우 검증 실패:
  - Edge 'to' references non-existent node: nasdaq_watch
  - Edge 'from' references non-existent node: nasdaq_watch
```

### 원인
`edges[]`에 node id가 있지만 `nodes[]`에 해당 id 정의가 없음.

### 해결
- `nodes[]`에 누락된 id 추가, 또는
- 해당 edge를 제거하고 상·하류 edge를 합치기
  ```json
  // Before (오류)
  { "from": "trading_hours", "to": "nasdaq_watch" },
  { "from": "nasdaq_watch", "to": "nasdaq_historical" },

  // After (정상)
  { "from": "trading_hours", "to": "nasdaq_historical" },
  ```

### 예방 체크
- JSON 작성 후 `pg.validate(workflow)` 호출 → `warnings/errors` 전체 확인
- Runner에서 `is_valid=False`면 즉시 중단 (실전계좌 사고 방지)

---

## 2. `credentials[].data[].value` 빈 문자열 → Credential 주입 실패

### 증상
```
[debug] After inject_credentials: appkey=False, appsecret=False
[warning] No credentials found - some features may not work
[error] Credential not found in secrets
```

### 원인
`workflow.json`의 credentials 섹션 데이터가 빈 값:
```json
"credentials": [
  {
    "credential_id": "broker_cred",
    "type": "broker_ls_overseas_stock",
    "data": [
      { "key": "appkey", "value": "", ... },      // ← 빈 값
      { "key": "appsecret", "value": "", ... }    // ← 빈 값
    ]
  }
]
```

`context.get_workflow_credential()`은 **이 `data` 배열**에서 값을 읽음.
`pg.run_async(secrets={...})` 파라미터만으로는 **broker 노드의
`_inject_credentials()` 경로에 반영되지 않음**.

### 해결: Runner에서 직접 주입

`scripts/live_bot/runner.py::_inject_credentials_into_workflow()` 참고:

```python
def _inject_credentials_into_workflow(workflow: dict, secrets: dict) -> dict:
    """credentials[].data[].value 가 비어있으면 secrets 값을 주입."""
    for cred in workflow.get("credentials", []):
        cred_id = cred.get("credential_id", "")
        values = secrets.get(cred_id)
        if not values:
            continue
        data = cred.get("data", [])
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "key" in item:
                    key = item["key"]
                    if key in values and not item.get("value"):
                        item["value"] = values[key]
        elif isinstance(data, dict):
            for k, v in values.items():
                if not data.get(k):
                    data[k] = v
    return workflow
```

Secrets 구조(실제 API 키는 외부 주입):
```python
secrets = {
    "broker_cred":   {"appkey": "...", "appsecret": "..."},
    "telegram_cred": {"bot_token": "...", "chat_id": "..."},
}
workflow = _inject_credentials_into_workflow(workflow, secrets)
```

### 서버 프로덕션 환경
서버가 DB에서 암호화된 credential을 복호화하여 `workflow.credentials[].data[].value`에
직접 주입한 뒤 실행하는 것이 표준 경로
(`context.get_workflow_credential()` docstring 참고).

---

## 3. ConditionNode `items` config 누락

### 증상
```
[debug] items config present: False
[error] ConditionNode 'scalable_trailing_stop': items가 설정되지 않았습니다.
         items { from, extract } 형태로 추가하세요.
```

### 원인
`positions` 배열처럼 여러 종목 각각에 대해 조건 판정을 돌리는 플러그인을
사용할 때, 어떤 노드의 어떤 필드에서 종목 리스트를 꺼내올지 알려줘야 함.

### 해결
`ConditionNode`의 config에 `items` 블록 추가:
```json
{
  "id": "scalable_trailing_stop",
  "type": "ConditionNode",
  "plugin": "Dynamic_ScalableTrailingStop",
  "items": {
    "from": "real_account",
    "extract": "positions"
  },
  "fields": { ... }
}
```

### auto-iterate와 차이
- `items`: ConditionNode가 자체적으로 리스트를 돌며 플러그인을 N회 호출
  (플러그인이 "positions-based"일 때)
- auto-iterate: 이전 노드가 배열 출력 → 다음 노드가 `{{ item.xxx }}`로 매 요소 처리

---

## 4. `{{ item.xxx }}` 표현식은 auto-iterate 컨텍스트에서만 정의됨

### 증상
```
[warning] Expression evaluation failed: {{ item.symbol }} - 정의되지 않은 변수: item
[warning] OverseasStockNewOrderNode: 주문할 종목이 없습니다
```

### 원인
`{{ item }}`, `{{ index }}`, `{{ total }}` 은 **auto-iterate가 발동한 노드
내부에서만** 해석됨. 발동 조건:
1. 이전 노드가 **비어있지 않은 배열** 출력
2. 현재 노드가 그 배열을 input으로 받음

상류가 빈 배열(`[]`)이면 auto-iterate 스킵 → `item` 미정의.

### 해결
- 상류 ConditionNode/Filter에서 빈 배열이 나오지 않도록 기본값 확인
- 혹은 IfNode로 `is_not_empty` 가드 후 분기

### 특히 ConditionNode → OrderNode 연결 시 주의

positions-based ConditionNode 출력 구조:
```python
{
  "symbols":         ["AUID"],                  # 문자열 배열 (ALL positions)
  "passed_symbols":  [{symbol, exchange, quantity}, ...],  # dict 배열 (TRIGGERED only)
  "failed_symbols":  [...],
  ...
}
```

Auto-iterate는 **`symbols` 포트를 우선 픽업** → 문자열 배열이면 `item`이 문자열.
`{{ item.symbol }}`은 문자열에 `.symbol` 접근 불가 → 전부 미해석.

**결과**: OrderNode가 `{{ item.symbol }}` 바인딩 실패 → 주문은 안 나가지만,
**TelegramNode는 미해석 리터럴 템플릿을 그대로 발송**. 사용자는 `{{ item.symbol }}`
가 적힌 메시지를 받음.

**해결**: 중간에 `FieldMappingNode`를 끼워 `passed_symbols`를 재출력하면
auto-iterate가 dict 배열을 소스로 픽업.
```json
{
  "id": "sell_items",
  "type": "FieldMappingNode",
  "data": "{{ nodes.scalable_trailing_stop.passed_symbols }}",
  "mappings": [],
  "preserve_unmapped": true
}
```

### 대안 — aggregate 노드 참조 `{{ nodes.X.Y }}`

per-item 상세 정보가 필요 없고 **요약성 메시지**로 충분하면, 템플릿에서
`{{ item.xxx }}` 대신 `{{ nodes.X.Y }}` 로 업스트림 노드의 **리스트 출력을 통째로**
참조. iteration context 의존성이 없어 빈 리스트든 N개든 **항상 해석**됨.

**AS-IS (취약):**
```json
{
  "id": "telegram_exit",
  "template": "📉 종목: {{ item.symbol }} 수익률: {{ item.pnl_rate }}%"
}
```

**TO-BE (안전):**
```json
{
  "id": "telegram_exit",
  "template": "📋 청산 대상: {{ nodes.exit_account.held_symbols }}"
}
```

이 패턴은 auto-iterate가 N번 실행될 때 **동일한 요약 메시지가 N번 발송**되지만
(워크플로우 59 `trend_trailing_bot` 의 정적 템플릿 패턴과 동일한 트레이드오프),
미해석 리터럴 원문이 나가는 것보다는 낫습니다. 68-77 예제의 `telegram_*` 노드가
이 스타일을 따릅니다.

### ⚠️ IfNode는 per-item 평가가 불가능함 — 알려진 제약

`IfNode` 는 실행 엔진의 `NO_AUTO_ITERATE_NODE_TYPES` 에 포함되어 있어 **단일 평가**
만 수행합니다. 따라서 `left: "{{ item.pnl_rate }}"` 로 **포지션별 손절 게이트**를
만들려는 패턴은 **원하는대로 동작하지 않음**:

```json
{
  "id": "if_stop_loss",
  "type": "IfNode",
  "left": "{{ item.pnl_rate }}",   // ⚠️ 절대 해석 안됨 — item 미정의
  "operator": "<=",
  "right": -5
}
```

**실제 동작**: `{{ item.pnl_rate }}` 가 항상 미해석 → IfNode는 항상 false 분기 →
다운스트림 sell_order/telegram은 cascading skip. 결과적으로 **포지션에 실제 큰
손실이 있어도 손절이 실행되지 않음**.

**올바른 패턴**:
1. **계좌 전체 수익률 기준**: `{{ nodes.account.balance.total_pnl_rate }}` 로 전체 평가
   (포지션별이 아니라 계좌 합산). 예제 #72 참고.
2. **per-position 자동 손절이 필요하면 전용 플러그인 사용**:
   - `stop_loss`, `profit_target`, `trailing_stop`, `dynamic_stop_loss`
   - ConditionNode 기반이라 per-item iteration 정상 작동
3. **리스크 모니터링만 원하면** `PortfolioNode.drawdown_percent` + IfNode 조합
   (포트폴리오 집계 스칼라 비교).

**기존 예제에도 동일 제약 존재**: 워크플로우 59/62/74/77 등이 `{{ item.pnl_rate }}`
패턴을 사용하지만, 위 이유로 실제 per-position 손절 로직은 작동하지 않습니다
(dry_run 테스트는 terminal state 도달만 확인하므로 통과). 실전 리스크 관리는
반드시 `stop_loss` 계열 플러그인으로 이관 권장.

---

## 5. TradingHoursFilterNode는 "분기 노드"가 아니라 "차단-대기 노드"

### 증상
```
[debug] Outside trading hours, waiting... (next check in 60s)
```
→ 봇이 주말/휴장 중 **60초마다 체크하며 블로킹 대기**. UI 응답 없이 멈춘 것처럼 보임.

### 오해
`TradingHoursFilterNode._outputs`에 `passed`/`blocked` 포트가 정의되어 있어
`from_port: "passed"` / `from_port: "blocked"`로 IfNode처럼 분기할 수 있을 것 같지만,
**실제로는 IfNode 전용 스킵 로직(`_compute_if_skip_nodes`)이 여기엔 적용 안 됨**.
TradingHours는 단일 출력 dict `{"passed": true/false}`만 반환하고, 하류 노드는
이 값과 무관하게 전부 실행됨.

### 동작
- 거래시간 내: 즉시 통과 → 하류 실행
- 거래시간 외: `check_interval=60s`로 반복 대기 (`asyncio.sleep(60)`)
- `max_wait_hours` 초과 시 timeout으로 `{passed: false, reason: "timeout"}` 반환,
  그러나 **하류는 그대로 전부 실행됨** (분기 아님)

### 올바른 사용
- **스케줄 트리거의 게이트**로만 사용 (e.g., `ScheduleNode → TradingHoursFilterNode → 실행 노드`)
- 실시간 WebSocket 경로에서는 **쓰지 말 것**: 60초 block-wait이 WebSocket
  이벤트 처리를 지연시킬 수 있음
- **"주말엔 주문 스킵 + Telegram 알림"** 같은 실시간 분기는 **MarketStatusNode + IfNode** 로 직접 구현

### 주말/휴장 분기 패턴 (권장) — MarketStatusNode 기반

**⚠️ 비권장 (레거시)**: 플러그인 내부에 `pytz + datetime` 으로 NYSE 장 시간을
하드코딩하던 방식은 **공휴일 미반영 + 프리마켓/에프터마켓 미구분 + 서킷브레이커
감지 불가** 로 운영 안정성이 떨어집니다. 대신 JIF 실시간 스트림을 사용하는
MarketStatusNode 를 쓰세요.

**권장 패턴**

```json
{
  "nodes": [
    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred"},
    {"id": "market_status", "type": "MarketStatusNode",
     "markets": ["US"], "stay_connected": true},
    {"id": "scalable_trailing_stop", "type": "ConditionNode",
     "plugin": "Dynamic_ScalableTrailingStop",
     "positions": "{{ nodes.real_account.positions }}"},
    {"id": "if_trigger", "type": "IfNode",
     "left": "{{ nodes.scalable_trailing_stop.passed_symbols }}",
     "operator": "is_not_empty"},
    {"id": "if_us_open", "type": "IfNode",
     "left": "{{ nodes.market_status.us_is_open }}",
     "operator": "==", "right": true}
  ],
  "edges": [
    {"from": "broker", "to": "market_status"},
    {"from": "scalable_trailing_stop", "to": "if_trigger"},
    {"from": "if_trigger", "to": "if_us_open", "from_port": "true"},
    {"from": "if_us_open", "to": "sell_order", "from_port": "true"},
    {"from": "if_us_open", "to": "telegram_market_closed", "from_port": "false"}
  ]
}
```

**장점**
- JIF 실시간 스트림 → 공휴일 휴장/서킷브레이커/사이드카 자동 반영
- 초기 이벤트 미수신 시 `us_is_open=False` → 보수적 skip (오주문 방지)
- 플러그인은 순수 트레일링스탑 계산만 담당 — 시장 시간 책임 분리

### ⚠️ 해외선물 시장 상태는 MarketStatusNode 로 확인 불가

JIF 는 **해외주식(US/CN/HK/JP) + 국내주식/파생** 만 지원하며,
**해외선물(CME, HKEX Futures, SGX, EUREX) 은 범위 밖**입니다.
`markets=["CME"]` 등 해외선물 키를 지정하면 Pydantic `ValidationError` 가
발생합니다.

해외선물 시장 시간 판단이 필요하면 `ScheduleNode` + `TradingHoursFilterNode` 조합으로 심볼별 정규거래시간을 하드코딩하세요 (공휴일 미반영 한계 인지).

---

## 6. 시간/타임존 처리 원칙

### 표현식 날짜 네임스페이스 한계
`date.today()`, `date.ago()`, `date.now()` 등만 제공.
- **weekday, hour, minute 추출 없음**
- **타임존 변환 없음** (모두 로컬 시스템 기준)

→ 복잡한 시간 조건(장중/장외, 거래일 판정)은 **플러그인/Python 코드**에서 처리.

### 타임존 하드코딩 금지
- 서버가 어디에 배포되든 동일하게 동작해야 함
- `datetime.now()` 대신 `datetime.now(pytz.timezone("America/New_York"))`
- KST↔ET↔UTC 변환은 반드시 tz-aware datetime으로

### 미국장 시간 판정 체크리스트
- 주말 제외 (`weekday() >= 5` 차단)
- 9:30~16:00 ET (일반장). 프리/애프터 포함 여부 명시
- **미국 공휴일**: `pandas_market_calendars` 또는 하드코딩 (Thanksgiving 반일장, Christmas Eve 등)
- **서머타임 전환일**: pytz가 자동 처리하지만 테스트 필요

### 스케줄 노드 vs 필터 노드
| 용도 | 권장 노드 | 이유 |
|------|-----------|------|
| N분마다 실행 | `ScheduleNode` (cron) | 정확한 타이밍, 불필요한 루프 없음 |
| 거래시간만 실행 허용 | `ScheduleNode` + `TradingHoursFilterNode` | 스케줄 게이트 |
| 이벤트 발생 시 분기 | `IfNode` + 플러그인 `market_open` 필드 | 즉시 분기, block-wait 없음 |
| 실시간 WebSocket 경로 | **TradingHours 쓰지 말 것** | 60초 block-wait이 tick 처리 막음 |

---

## 실행 전 최종 체크리스트

1. `pg.validate(workflow)` → `is_valid=True` 확인
2. 모든 `edges[].from/to` 가 `nodes[].id` 에 존재
3. `credentials[].data[].value` 가 주입되어 있거나 runner에서 주입 경로 확보
4. 배열-기반 ConditionNode(`positions_based`, screener_based 등)는
   `items: { from, extract }` 추가 (또는 플러그인 SCHEMA의
   `required_data=["positions"]` 명시)
5. `{{ item.xxx }}` 바인딩한 하류 노드는 **상류가 항상 비어있지 않은 dict 배열**
   출력하는지 확인 (ConditionNode → OrderNode 사이에 FieldMappingNode 필수)
6. **TelegramNode 앞에 IfNode 가드** 두기: 바인딩 실패해도 리터럴 템플릿이
   텔레그램으로 발송되는 것 방지
7. 실시간 경로에 TradingHoursFilterNode 금지 (block-wait), 분기는 IfNode 사용
8. 타임존은 반드시 tz-aware datetime + 플러그인에서 계산
9. 실전계좌(`paper_trading=False`)는 **소액 종목 1개로 최소 1 cycle 검증 후**
   본격 가동

---

## 참고 파일

- `/src/programgarden/programgarden/executor.py::_inject_credentials`
- `/src/programgarden/programgarden/context.py::get_workflow_credential`
- `/scripts/live_bot/runner.py::_inject_credentials_into_workflow`
- `/docs/expression_guide.md` (표현식 문법)
- `/docs/auto_iterate_guide.md` (auto-iterate 규칙)
