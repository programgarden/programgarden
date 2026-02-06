# WorkflowPnLEvent 데이터 스키마

`on_workflow_pnl_update` 콜백으로 전달되는 실시간 수익률 이벤트 형식입니다.

## 기본 이벤트 구조

```python
{
    # ========== 기본 정보 ==========
    "job_id": "workflow-pnl-stock-test",       # 워크플로우 실행 ID
    "broker_node_id": "broker",                 # BrokerNode ID
    "product": "overseas_stock",                # "overseas_stock" | "overseas_futures"
    "paper_trading": false,                     # true: 모의투자, false: 실전투자
    "timestamp": "2026-01-27T10:30:45.123456",  # 이벤트 발생 시간 (ISO 8601)
    "currency": "USD",                          # 통화 단위

    # ========== 워크플로우 P&L (이 워크플로우가 실행한 주문만) ==========
    "workflow_pnl_rate": 2.35,          # 워크플로우 수익률 (%)
    "workflow_eval_amount": 10235.00,   # 워크플로우 평가금액 ($)
    "workflow_buy_amount": 10000.00,    # 워크플로우 매수금액 ($)
    "workflow_pnl_amount": 235.00,      # 워크플로우 손익금액 ($)

    # ========== 그 외 P&L (수동 주문 등 워크플로우 외 포지션) ==========
    "other_pnl_rate": -1.20,            # 그 외 수익률 (%)
    "other_eval_amount": 4940.00,       # 그 외 평가금액 ($)
    "other_buy_amount": 5000.00,        # 그 외 매수금액 ($)
    "other_pnl_amount": -60.00,         # 그 외 손익금액 ($)

    # ========== 전체 P&L (워크플로우 + 그 외) ==========
    "total_pnl_rate": 1.17,             # 전체 수익률 (%)
    "total_eval_amount": 15175.00,      # 전체 평가금액 ($)
    "total_buy_amount": 15000.00,       # 전체 매수금액 ($)
    "total_pnl_amount": 175.00,         # 전체 손익금액 ($)

    # ========== 신뢰도 지표 ==========
    "trust_score": 100,                 # 신뢰도 점수 (0-100, FIFO 매칭 정확도)
    "anomaly_count": 0,                 # 이상 탐지 횟수

    # ========== 포지션 카운트 ==========
    "total_position_count": 5,          # 전체 보유 종목 수

    # ========== 포지션 상세 리스트 ==========
    "workflow_positions": [             # 워크플로우가 보유한 포지션
        {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "quantity": 10,             # 보유 수량
            "avg_price": 180.50,        # 평균 매수가
            "current_price": 185.20,    # 현재가
            "pnl_amount": 47.00,        # 손익금액
            "pnl_rate": 2.60            # 수익률 (%)
        }
    ],
    "other_positions": [                # 그 외 포지션
        {
            "symbol": "TSLA",
            "exchange": "NASDAQ",
            "quantity": 5,
            "avg_price": 250.00,
            "current_price": 247.00,
            "pnl_amount": -15.00,
            "pnl_rate": -1.20
        }
    ],

    # ========== v2.0 상품별 P&L (Optional) ==========
    "workflow_stock_pnl_rate": 2.35,          # 워크플로우 주식 수익률
    "workflow_stock_pnl_amount": 235.00,      # 워크플로우 주식 손익금액
    "workflow_futures_pnl_rate": null,        # 워크플로우 선물 수익률
    "workflow_futures_pnl_amount": null,      # 워크플로우 선물 손익금액

    # ========== v2.0 계좌 전체 P&L (Optional) ==========
    "account_total_pnl_rate": 1.50,           # 계좌 전체 수익률
    "account_total_pnl_amount": 750.00,       # 계좌 전체 손익금액
    "account_total_eval_amount": 50750.00,    # 계좌 전체 평가금액
    "account_total_buy_amount": 50000.00,     # 계좌 전체 매수금액

    # ========== v2.0 계좌 상품별 P&L (Optional) ==========
    "account_stock_pnl_rate": 1.50,           # 계좌 주식 수익률
    "account_stock_pnl_amount": 750.00,       # 계좌 주식 손익금액
    "account_futures_pnl_rate": null,         # 계좌 선물 수익률
    "account_futures_pnl_amount": null,       # 계좌 선물 손익금액

    # ========== 워크플로우 메타데이터 (Optional) ==========
    "workflow_start_datetime": "2026-01-20T09:00:00",  # 워크플로우 시작 시간
    "workflow_elapsed_days": 7,                         # 워크플로우 경과 일수

    # ========== 대회 관련 (start_date 설정 시에만) ==========
    "competition_start_date": "20260115",                    # 대회 시작일
    "competition_workflow_pnl_rate": 3.50,                   # 대회 시작 이후 워크플로우 수익률
    "competition_workflow_pnl_amount": 350.00,               # 대회 시작 이후 워크플로우 손익
    "competition_workflow_stock_pnl_rate": 3.50,             # 대회 시작 이후 워크플로우 주식 수익률
    "competition_workflow_stock_pnl_amount": 350.00,
    "competition_workflow_futures_pnl_rate": null,
    "competition_workflow_futures_pnl_amount": null,
    "competition_account_pnl_rate": 2.00,                    # 대회 시작 이후 계좌 전체 수익률
    "competition_account_pnl_amount": 1000.00,
    "competition_account_stock_pnl_rate": 2.00,
    "competition_account_stock_pnl_amount": 1000.00,
    "competition_account_futures_pnl_rate": null,
    "competition_account_futures_pnl_amount": null
}
```

---

## 필드 설명 요약표

| 구분 | 필드 | 타입 | 설명 |
|------|------|------|------|
| **기본** | `job_id` | string | 워크플로우 실행 ID |
| | `broker_node_id` | string | BrokerNode ID |
| | `product` | string | `overseas_stock` 또는 `overseas_futures` |
| | `paper_trading` | bool | `true`: 모의투자, `false`: 실전투자 |
| | `timestamp` | datetime | 이벤트 발생 시간 |
| | `currency` | string | 통화 단위 (기본: USD) |
| **워크플로우** | `workflow_pnl_rate` | Decimal | **핵심** - 이 워크플로우가 실행한 주문의 수익률 (%) |
| | `workflow_eval_amount` | Decimal | 워크플로우 평가금액 |
| | `workflow_buy_amount` | Decimal | 워크플로우 매수금액 |
| | `workflow_pnl_amount` | Decimal | 워크플로우 손익금액 |
| **그 외** | `other_pnl_rate` | Decimal | 수동 주문 등 워크플로우 외 포지션 수익률 (%) |
| | `other_eval_amount` | Decimal | 그 외 평가금액 |
| | `other_buy_amount` | Decimal | 그 외 매수금액 |
| | `other_pnl_amount` | Decimal | 그 외 손익금액 |
| **전체** | `total_pnl_rate` | Decimal | 워크플로우 + 그 외 합산 수익률 (%) |
| | `total_eval_amount` | Decimal | 전체 평가금액 |
| | `total_buy_amount` | Decimal | 전체 매수금액 |
| | `total_pnl_amount` | Decimal | 전체 손익금액 |
| **신뢰도** | `trust_score` | int | FIFO 매칭 신뢰도 (0-100, 높을수록 정확) |
| | `anomaly_count` | int | 이상 탐지 횟수 |
| **포지션** | `total_position_count` | int | 전체 보유 종목 수 |
| | `workflow_positions` | list | 워크플로우 보유 종목 상세 리스트 |
| | `other_positions` | list | 그 외 보유 종목 상세 리스트 |
| **v2.0 상품별** | `workflow_stock_pnl_rate` | Decimal? | 워크플로우 주식 수익률 |
| | `workflow_futures_pnl_rate` | Decimal? | 워크플로우 선물 수익률 |
| **v2.0 계좌** | `account_total_pnl_rate` | Decimal? | 계좌 전체 수익률 |
| | `account_stock_pnl_rate` | Decimal? | 계좌 주식 수익률 |
| | `account_futures_pnl_rate` | Decimal? | 계좌 선물 수익률 |
| **메타데이터** | `workflow_start_datetime` | datetime? | 워크플로우 시작 시간 |
| | `workflow_elapsed_days` | int? | 워크플로우 경과 일수 |
| **대회** | `competition_start_date` | string? | 대회 시작일 (YYYYMMDD) |
| | `competition_workflow_pnl_rate` | Decimal? | 대회 시작일 이후 워크플로우 수익률 |
| | `competition_account_pnl_rate` | Decimal? | 대회 시작일 이후 계좌 수익률 |

---

## PositionDetail 구조

`workflow_positions`와 `other_positions` 배열의 각 항목 형식:

```python
{
    "symbol": "AAPL",           # 종목 코드
    "exchange": "NASDAQ",       # 거래소 코드
    "quantity": 10,             # 보유 수량
    "avg_price": 180.50,        # 평균 매수가
    "current_price": 185.20,    # 현재가
    "pnl_amount": 47.00,        # 손익금액 (current - avg) * quantity
    "pnl_rate": 2.60            # 수익률 (%)
}
```

---

## 사용 예시

### 1. 기본 리스너 구현

```python
from programgarden_core.bases import BaseExecutionListener, WorkflowPnLEvent

class MyListener(BaseExecutionListener):
    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
        print(f"워크플로우 수익률: {float(event.workflow_pnl_rate):+.2f}%")
        print(f"전체 수익률: {float(event.total_pnl_rate):+.2f}%")
```

### 2. WebSocket으로 전송

```python
from dataclasses import asdict

class WebSocketListener(BaseExecutionListener):
    def __init__(self, websocket):
        super().__init__()
        self.ws = websocket

    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
        # dataclass → dict 변환
        data = asdict(event)

        # datetime → ISO string 변환
        data["timestamp"] = event.timestamp.isoformat()
        if event.workflow_start_datetime:
            data["workflow_start_datetime"] = event.workflow_start_datetime.isoformat()

        # WebSocket으로 전송
        await self.ws.send_json({
            "type": "workflow_pnl_update",
            "data": data
        })
```

### 3. 대회 모드 (특정 날짜 이후 수익률만 계산)

```python
class CompetitionListener(BaseExecutionListener):
    def __init__(self):
        super().__init__(start_date="20260115")  # 대회 시작일 설정

    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
        # 대회 시작일 이후 수익률 사용
        if event.competition_workflow_pnl_rate is not None:
            print(f"대회 수익률: {float(event.competition_workflow_pnl_rate):+.2f}%")
```

---

## 모의투자 vs 실전투자 (trading_mode 분리)

`paper_trading` 필드로 모의/실전 모드를 구분하며, 각 모드별로 **독립적으로** 수익률을 추적합니다.

| 항목 | 모의투자 (`paper_trading: true`) | 실전투자 (`paper_trading: false`) |
|------|------|------|
| DB 저장 | `trading_mode = 'paper'`로 분리 저장 | `trading_mode = 'live'`로 분리 저장 |
| 수익률 추적 | 모의 전용 데이터로 독립 계산 | 실전 전용 데이터로 독립 계산 |
| `trust_score` | 모의 거래 기준으로 독립 산정 | 실전 거래 기준으로 독립 산정 |
| 모드 전환 시 | 기존 데이터 유지 (삭제 안 함) | 기존 데이터 유지 (삭제 안 함) |
| 해외주식 | LS증권 모의투자 **미지원** | 지원 |
| 해외선물 | 지원 | 지원 |

### 모의투자 응답 예시 (해외선물)

```python
{
    "job_id": "workflow-pnl-futures-paper",
    "broker_node_id": "broker",
    "product": "overseas_futures",
    "paper_trading": true,                     # 모의투자
    "timestamp": "2026-01-27T10:30:45.123456",
    "currency": "USD",

    "workflow_pnl_rate": -0.85,
    "workflow_eval_amount": 9915.00,
    "workflow_buy_amount": 10000.00,
    "workflow_pnl_amount": -85.00,

    "other_pnl_rate": 0.00,
    "other_eval_amount": 0.00,
    "other_buy_amount": 0.00,
    "other_pnl_amount": 0.00,

    "total_pnl_rate": -0.85,
    "total_eval_amount": 9915.00,
    "total_buy_amount": 10000.00,
    "total_pnl_amount": -85.00,

    "trust_score": 100,
    "anomaly_count": 0,
    "total_position_count": 2,

    "workflow_positions": [
        {
            "symbol": "HMCEG26",
            "exchange": "CME",
            "quantity": 2,
            "avg_price": 5000.00,
            "current_price": 4957.50,
            "pnl_amount": -85.00,
            "pnl_rate": -0.85
        }
    ],
    "other_positions": []
}
```

### 모드 설정 방법

```python
# credential에 paper_trading 설정
"credentials": [
    {
        "credential_id": "broker-cred",
        "type": "broker_ls_futures",
        "data": [
            {"key": "appkey", "value": "...", "type": "password"},
            {"key": "appsecret", "value": "...", "type": "password"},
            {"key": "paper_trading", "value": true, "type": "boolean", "label": "모의투자"}
        ]
    }
]

# 노드에도 paper_trading 설정 (credential + 노드 양쪽 모두 필요)
{
    "id": "broker",
    "type": "OverseasFuturesBrokerNode",
    "credential_id": "broker-cred",
    "paper_trading": true
}
```

> **주의**: `paper_trading`은 credential 뿐만 아니라 **노드 설정에도 반드시 포함**해야 합니다.

---

## 핵심 포인트

1. **워크플로우 vs 그 외 분리**: FIFO 방식으로 워크플로우가 실행한 주문만 추적하여 `workflow_*` 필드에 별도 계산
2. **모의/실전 독립 추적**: `paper_trading` 값에 따라 별도 DB 레코드로 수익률 독립 계산 (모드 전환해도 기존 데이터 유지)
3. **실시간 업데이트**: 틱 데이터가 변할 때마다 콜백 호출
4. **대회 모드**: `BaseExecutionListener(start_date="20260115")`로 생성 시 `competition_*` 필드 활성화
5. **Decimal 타입**: 금액/수익률은 `Decimal` 또는 `float`로 전달됨 (정밀도 유지 위해 Decimal 권장)
6. **신뢰도 점수**: `trust_score`가 낮으면 FIFO 매칭이 불완전할 수 있음 (80 이상 권장)

---

## 관련 파일

- 이벤트 정의: `src/core/programgarden_core/bases/listener.py`
- 예제 코드: `src/programgarden/examples/programmer_example/workflow_pnl_stock.py`
