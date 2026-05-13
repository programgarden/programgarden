# 소개

[![Python](https://img.shields.io/badge/python-3.12%2B-blue?logo=python\&logoColor=white)](https://www.python.org/) [![Release](https://img.shields.io/github/v/tag/programgarden/programgarden?label=release\&sort=semver\&logo=github)](https://github.com/programgarden/programgarden/releases) [![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_3.0-blue.svg)](LICENSE/) [![Company: LS](https://img.shields.io/badge/%EC%A7%80%EC%9B%90%EB%90%98%EB%8A%94_%EC%A6%9D%EA%B6%8C%EC%82%AC-LS%EC%A6%9D%EA%B6%8C-008FC7.svg)](https://ls-sec.co.kr) [![Product: OverseasStock](https://img.shields.io/badge/%EC%A7%80%EC%9B%90%EB%90%98%EB%8A%94_%EC%9E%90%EB%8F%99%EB%A7%A4%EB%A7%A4-%ED%95%B4%EC%99%B8%EC%A3%BC%EC%8B%9D,%ED%95%B4%EC%99%B8%EC%84%A0%EB%AC%BC,%EA%B5%AD%EB%82%B4%EC%A3%BC%EC%8B%9D-purple.svg)](https://programgarden.gitbook.io/docs)

![programgarden 그리고 ls](docs/images/programgarden_ls.png)

> **⚠️ 주의**: 오픈소스 사용 시 발생하는 문제에 대한 책임은 사용자에게 있으며, 라이선스를 반드시 확인해 주세요. [라이선스 보기](https://github.com/programgarden/programgarden?tab=AGPL-3.0-1-ov-file#readme)

> **⚠️ 모의투자 안내**: 해외선물은 `홍콩거래소 (HKEX)`의 모의투자만 지원되며, `CME`, `EUREX` 등 다른 거래소와 해외주식은 모의투자가 지원되지 않습니다 (실전투자만 가능). 모의투자 시 실제 체결 가격과 차이가 발생하니 유의하시기 바랍니다. [빠른 실행 가이드 보기](https://programgarden.gitbook.io/docs/invest/non_dev_quick_guide)

> **📢 현황**: 국내주식 Finance API(88개 TR) + 워크플로우 노드 13개가 추가되었습니다. 코인은 제작중입니다.

## 소개

**ProgramGarden**은 오픈소스 기반 AI 퀀트 플랫폼입니다. 코딩 없이 노드를 조합하여 자동매매 전략을 구성하고 실행할 수 있습니다.

[**프로그램 동산**](https://programgarden.com)과 [**LS증권**](https://ls-sec.co.kr) 협업으로 개발되었으며, 개인 투자자부터 자동매매 서비스를 원하는 기업까지 활용할 수 있습니다.

자세한 사용법은 [**가이드 문서**](https://programgarden.gitbook.io/docs)를 참고하세요.

## AI 퀀트 앱

오픈소스 기반으로 구축된 웹사이트와 앱에서 이용하세요.

* https://programgarden.com (오픈 예정)

## 커뮤니티

* 카카오톡 단톡방: https://open.kakao.com/o/gKVObqUh
* 프로그램 동산 유튜브: https://youtube.com/@programgarden
* 네이버 카페 커뮤니티: https://cafe.naver.com/programgarden
* 비즈니스 문의: coding@programgarden.com

## 주요 기능

* **노드 기반 워크플로우** — 73개 노드를 조합하여 코딩 없이 전략 구성
* **해외주식 · 해외선물 · 국내주식** — LS증권 OpenAPI 기반 실시간 시세 조회 및 자동 주문
* **AI Agent** — LLM 기반 분석 및 의사결정을 워크플로우에 통합
* **전략 플러그인** — RSI, MACD 등 커뮤니티 기여 전략을 조합하여 활용
* **위험 관리** — 포트폴리오 추적, HWM/Drawdown, 위험 이벤트 감사 기록
* **동적 노드 주입** — 외부 개발자가 런타임에 커스텀 노드를 추가 가능

## 패키지 구조

```
src/
├── programgarden/          # 워크플로우 실행 엔진 (메인 패키지)
│   └── examples/           # 워크플로우 예제 (workflows JSON, dynamic_plugins, programmer_example)
├── core/                   # 노드 타입, 베이스 클래스, 레지스트리, i18n
├── finance/                # LS증권 OpenAPI 래퍼 (해외주식, 해외선물, 국내주식)
│   └── example/            # LS증권 데이터 API 호출 예제 (TR 단위)
└── community/              # 전략 플러그인 (RSI, MACD 등)
```

## 예제

- **워크플로우(자동매매)**: [`src/programgarden/examples/`](src/programgarden/examples/)
  - `workflows/` — 77개 실행 가능한 워크플로우 JSON + 동반 `.md` 문서
  - `dynamic_plugins/`, `dynamic_nodes/` — 런타임 동적 주입 예시
  - `programmer_example/` — AI Agent · quant 통합 스크립트
- **LS증권 데이터 API**: [`src/finance/example/`](src/finance/example/)
  - 해외주식 · 해외선물 · 국내주식 TR 호출 샘플

## 설치

**워크플로우 엔진 전체** (노드 + 전략 플러그인 + finance + core 포함):

```bash
pip install programgarden
# 또는 Poetry
poetry add programgarden
```

**LS증권 OpenAPI 만 단독 사용** (워크플로우 엔진 없이 TR 호출 스크립트만 필요할 때):

```bash
pip install programgarden-finance
# 또는 Poetry
poetry add programgarden-finance
```

## AI 코딩 에이전트와 함께 사용하기 (Claude · Codex)

ProgramGarden 은 두 종류의 사용 인터페이스를 제공합니다. 자신이 하려는 작업에 해당하는 섹션을 펼친 뒤, 안쪽 코드 블록(우상단 복사 버튼)을 통째로 복사해 AI 에이전트의 시스템 프롬프트 또는 첫 메시지에 붙여 넣으세요. 도메인 특화 코드베이스(워크플로우 DSL + LS증권 OpenAPI)라 콜드 리딩만으로는 정확한 추론이 어렵기 때문에, 앞단에 컨텍스트를 주는 것이 출력 품질을 크게 좌우합니다.

<details>
<summary><b>워크플로우 사용자용 (<code>programgarden</code> — 노드 기반 자동화)</b></summary>

`WorkflowExecutor` 로 실행할 워크플로우 JSON 을 작성하거나 디버깅할 때 사용합니다. 아래 블록을 통째로 복사해 에이전트에게 붙여 넣으세요.

````markdown
# ProgramGarden — Workflow User Context

You are helping a user of the ProgramGarden automated-trading library
(https://github.com/programgarden/programgarden). They are building or debugging
workflow JSON that runs through `WorkflowExecutor`. Follow this context strictly.

## What this library is

- Node-based automation DSL. A workflow is a JSON document with `nodes`,
  `edges`, `credentials`, and `notes`.
- 73 nodes across 12 categories: `infra` / `account` / `market` / `condition` /
  `order` / `risk` / `schedule` / `data` / `display` / `analysis` / `ai` /
  `messaging`. Full schema lives in `CLAUDE.md` and
  `src/core/programgarden_core/nodes/`.
- 77 community plugins, referenced via the `plugin` field in `ConditionNode`,
  `NewOrderNode`, etc. See `src/community/programgarden_community/plugins/`.
- Expression binding: `{{ nodes.<id>.<port> }}` flows data between nodes.
  Auto-iterate (`item` / `index` / `total`) when an upstream node emits an
  array. Function namespaces: `date.*`, `finance.*`, `stats.*`, `format.*`,
  `lst.*`.
- Edge types: `main` (default DAG execution), `ai_model` (connects
  `LLMModelNode` → `AIAgentNode`), `tool` (registers a node as an AI Agent
  tool). `IfNode` branches use `from_port: "true"` / `"false"` (or dot
  notation `"from": "if1.true"`).
- i18n keys live in `src/core/programgarden_core/i18n/locales/{ko,en}.json`
  under the patterns `nodes.{Type}.name|description`,
  `fields.{Type}.{field}`, `outputs.{Type}.{port}`.
- Two execution entry points:
  (1) `WorkflowExecutor` — run an entire JSON workflow.
  (2) `NodeRunner` — run a single node standalone.

## Prompt templates

### Build a new workflow

```
First read `CLAUDE.md` to learn the node / edge / expression rules, then study
`src/programgarden/examples/workflows/01-account-stock-balance.json` plus one
or two strategy workflows in the same directory.
Then build the following workflow JSON:

- Goal: buy at market for 5 NASDAQ tickers whose RSI is <= 30
- Constraint: must pass `WorkflowExecutor.validate()`
```

### Debug a failing workflow

```
Running this workflow JSON raises `Node X failed: ...`.
Run it in dry-run mode by passing
`context_params={"dry_run": True, "max_cycles": 1}` to
`WorkflowExecutor.execute()`. Order, messaging, and real-time nodes will
return mock results so you can locate where the actual error happens.
Wire up an `ExecutionListener`
(see `src/core/programgarden_core/bases/listener.py`) to print node and edge
state transitions while it runs.
```

### Contribute a new plugin

```
Add a new strategy plugin `IchimokuCloud` to ProgramGarden. The plugin layout
is a single `__init__.py` inside
`src/community/programgarden_community/plugins/<plugin_name>/` plus an
optional `README.md`. See `plugins/rsi/__init__.py` for the canonical
example. Plugins are registered through `plugins/__init__.py`. Write all i18n
keys in English only.
```

## Gotchas — call these out up front, they trip agents constantly

1. Symbols are arrays, never dict keys:
   `[{"symbol": "AAPL", "exchange": "NASDAQ"}]`
2. Broker connection is auto-injected by Executor via DAG traversal — never
   bind `connection` manually.
3. Method chaining inside `{{ }}` is supported:
   `{{ nodes.account.filter('pnl > 0').count() }}`
4. Retry is disabled by default for order nodes (`*NewOrderNode`,
   `*ModifyOrderNode`, `*CancelOrderNode`) to prevent duplicate submissions.
   Enabling `resilience.retry.enabled = True` needs explicit justification.
5. Auto-iterate: when the upstream node emits an array, the downstream node
   runs once per item — no explicit loop needed.
6. There is **no** `WorkflowExecutor.dry_run()` method. Dry-run is enabled
   via `execute(..., context_params={"dry_run": True})`.

## Reference files to read before answering

- `CLAUDE.md` — node catalog, architecture, examples (read first)
- `PROJECT_MAP.md` — repo index
- `src/programgarden/programgarden/executor.py` — `WorkflowExecutor`,
  `execute()`, `validate()`, dry-run behavior
- `src/core/programgarden_core/bases/listener.py` — `ExecutionListener`
  callback contract
- `src/programgarden/examples/workflows/` — 77 runnable workflow JSON files
  (start with `01-account-stock-balance.json`)
- `src/community/programgarden_community/plugins/rsi/__init__.py` — canonical
  plugin shape
````

</details>

<details>
<summary><b>LS증권 API 직접 사용자용 (<code>programgarden-finance</code> 단독)</b></summary>

워크플로우 엔진 없이 LS증권 OpenAPI 래퍼만 사용해 자신의 스크립트에서 TR(거래코드)을 직접 호출할 때 사용합니다. 아래 블록을 통째로 복사해 에이전트에게 붙여 넣으세요.

````markdown
# ProgramGarden Finance — Direct LS Securities API Context

You are helping a user of the `programgarden-finance` library
(https://pypi.org/project/programgarden-finance/). They are calling LS Securities
OpenAPI TRs directly through their own scripts, without the workflow engine.
Follow this context strictly.

## What this library is

- A typed sync/async wrapper over LS Securities OpenAPI. Each TR (e.g.
  `t1410`, `t8407`) is a Pydantic `blocks.py` module exposing
  `InBlock` / `OutBlock` types. The TR class itself exposes both `.req()`
  (sync) and `.req_async()` (async) callers.
- Coverage: ~150 TR blocks across Overseas Stock / Overseas Futures / Korea
  Stock REST, plus ~28 real-time WebSocket TR blocks (7 overseas stock +
  7 overseas futures + 13 Korea stock + 1 shared).
- TR layout:
  `src/finance/programgarden_finance/ls/{market_segment}/{kind}/t####/` —
  every TR has its own folder; `blocks.py` defines all fields with
  `Field(title=..., description=..., examples=[...])`.
- Authentication: `appkey` + `appsecret` from the LS Securities developer
  portal. Token refresh and rate-limit handling are built in.
- Source-of-truth rule: the library never asserts LS-undocumented formulas,
  sign conventions, units, or time-series ordering. If LS spec doesn't say it,
  the field description literally says `"Not declared in available source."`
  Respect this — do not infer.

## Prompt templates

### Call a single TR

```
Using `programgarden_finance`, write a script that calls Korea Stock TR
`t1410` (초저유동성조회 / ultra-low-liquidity query).
See `src/finance/example/korea_stock/run_t1410.py` for the canonical calling
convention (both `.req()` and `.req_async()` patterns).
Read `appkey` / `appsecret` from env vars `LS_APPKEY` / `LS_APPSECRET`.
```

### Find the right TR

```
I need to fetch minute-bar OHLCV for a Korea stock. Browse
`src/finance/programgarden_finance/ls/korea_stock/` to find the right TR,
read its `blocks.py` to understand the InBlock / OutBlock fields
(`src/finance/programgarden_finance/ls/korea_stock/market/t1410/blocks.py` is
a canonical reference for field metadata structure), then write a runnable
example modeled after the matching
`src/finance/example/korea_stock/run_t####.py`.
```

### Real-time subscription

```
Subscribe to Korea Stock real-time price ticks using `programgarden_finance`.
Use the singleton WebSocket pattern from
`src/finance/programgarden_finance/ls/real_base.py`. See
`src/finance/example/korea_stock/real_S3_.py` for a complete subscription
example. Print each tick as it arrives and handle reconnect cleanly.
```

## Gotchas — call these out up front, they trip agents constantly

1. Don't invent field semantics. If the description says
   `"Not declared in available source"`, do not derive a formula or unit —
   ask the user instead.
2. Rate limits are per-TR and enforced by the library. Don't hand-roll your
   own throttling on top.
3. WebSocket is a singleton per credential — don't open multiple connections;
   add subscriptions to the existing session.
4. Field `title` / `description` / `examples` are AI-chatbot ground truth for
   every TR. When editing `blocks.py`, preserve all three.
5. Korean stock uses `shcode` (6 digits); overseas stock uses
   `symbol` + `exchange`. They are not interchangeable.

## Reference files to read before answering

- `src/finance/example/` — runnable per-TR samples (overseas stock / futures /
  Korea stock)
- `src/finance/programgarden_finance/ls/real_base.py` — singleton WebSocket
  pattern for all real-time subscriptions
- `src/finance/programgarden_finance/ls/korea_stock/market/t1410/blocks.py` —
  canonical TR `blocks.py` to mirror when adding or studying a TR
- LS Securities OpenAPI portal: https://openapi.ls-sec.co.kr/apiservice
````

</details>
