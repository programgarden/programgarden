# 수익률 추적 가이드

워크플로우를 실행하면 **수익률이 자동으로 추적**됩니다. 별도 설정 없이 실시간으로 수익률을 확인할 수 있습니다.

---

## 1. 수익률의 3가지 구분

ProgramGarden은 수익률을 **3가지로 구분**하여 보여줍니다.

| 구분 | 설명 | 예시 |
|------|------|------|
| **워크플로우 수익률** | 이 워크플로우가 실행한 주문만의 수익률 | 워크플로우가 매수한 AAPL, NVDA의 수익률 |
| **그 외 수익률** | 수동 주문 등 워크플로우 외 포지션의 수익률 | 직접 앱에서 매수한 TSLA의 수익률 |
| **전체 수익률** | 워크플로우 + 그 외를 합산한 수익률 | 계좌 전체의 수익률 |

### 왜 분리하나요?

같은 증권 계좌에서 워크플로우 자동매매와 수동 매매를 동시에 할 수 있습니다. 이때 **"내 전략이 실제로 얼마나 벌었는지"**를 정확히 알려면 워크플로우가 실행한 주문만 따로 추적해야 합니다.

예를 들어:
- 워크플로우가 AAPL을 매수하여 +5% 수익 중
- 내가 직접 TSLA를 매수했는데 -3% 손실 중
- **전체** 계좌는 +1%로 보이지만, **워크플로우 전략**은 +5%로 잘 작동하고 있음

---

## 2. 수익률 데이터 항목

### 기본 정보

| 항목 | 설명 |
|------|------|
| `product` | 상품 유형 (`overseas_stock`: 해외주식, `overseas_futures`: 해외선물, `korea_stock`: 국내주식) |
| `paper_trading` | 모의투자 여부 (`true`: 모의투자, `false`: 실전투자) |
| `timestamp` | 수익률 업데이트 시간 |
| `currency` | 통화 단위 (기본: USD) |

### 워크플로우 수익률

이 워크플로우가 실행한 주문에 대한 수익률입니다.

| 항목 | 설명 |
|------|------|
| `workflow_pnl_rate` | 워크플로우 수익률 (%) |
| `workflow_eval_amount` | 워크플로우 평가금액 |
| `workflow_buy_amount` | 워크플로우 매수금액 |
| `workflow_pnl_amount` | 워크플로우 손익금액 |

### 그 외 수익률

수동 주문 등 워크플로우 외 포지션에 대한 수익률입니다.

| 항목 | 설명 |
|------|------|
| `other_pnl_rate` | 그 외 수익률 (%) |
| `other_eval_amount` | 그 외 평가금액 |
| `other_buy_amount` | 그 외 매수금액 |
| `other_pnl_amount` | 그 외 손익금액 |

### 전체 수익률

워크플로우 + 그 외를 합산한 수익률입니다.

| 항목 | 설명 |
|------|------|
| `total_pnl_rate` | 전체 수익률 (%) |
| `total_eval_amount` | 전체 평가금액 |
| `total_buy_amount` | 전체 매수금액 |
| `total_pnl_amount` | 전체 손익금액 |

### 상품별 수익률

해외주식과 해외선물을 동시에 거래할 경우, 상품별로 분리된 수익률도 제공됩니다.

| 항목 | 설명 |
|------|------|
| `workflow_stock_pnl_rate` | 워크플로우 주식 수익률 |
| `workflow_stock_pnl_amount` | 워크플로우 주식 손익금액 |
| `workflow_futures_pnl_rate` | 워크플로우 선물 수익률 |
| `workflow_futures_pnl_amount` | 워크플로우 선물 손익금액 |

### 계좌 전체 수익률

증권 계좌 전체의 수익률 정보입니다.

| 항목 | 설명 |
|------|------|
| `account_total_pnl_rate` | 계좌 전체 수익률 |
| `account_total_pnl_amount` | 계좌 전체 손익금액 |
| `account_total_eval_amount` | 계좌 전체 평가금액 |
| `account_total_buy_amount` | 계좌 전체 매수금액 |
| `account_stock_pnl_rate` | 계좌 주식 수익률 |
| `account_futures_pnl_rate` | 계좌 선물 수익률 |

---

## 3. 보유 종목 상세

수익률과 함께 **종목별 상세 정보**도 제공됩니다.

### 워크플로우 보유 종목 (`workflow_positions`)

워크플로우가 매수한 종목의 상세 정보입니다.

```json
[
  {
    "symbol": "AAPL",
    "exchange": "NASDAQ",
    "quantity": 10,
    "avg_price": 180.50,
    "current_price": 185.20,
    "pnl_amount": 47.00,
    "pnl_rate": 2.60
  }
]
```

| 항목 | 설명 |
|------|------|
| `symbol` | 종목 코드 |
| `exchange` | 거래소 코드 |
| `quantity` | 보유 수량 |
| `avg_price` | 평균 매수가 |
| `current_price` | 현재가 |
| `pnl_amount` | 손익금액 |
| `pnl_rate` | 수익률 (%) |

### 그 외 보유 종목 (`other_positions`)

워크플로우 외 포지션(수동 매매 등)의 상세 정보입니다. 형식은 `workflow_positions`와 동일합니다.

---

## 4. 모의투자 vs 실전투자

수익률은 **모의투자와 실전투자를 완전히 분리**하여 추적합니다.

| 항목 | 모의투자 | 실전투자 |
|------|---------|---------|
| `paper_trading` 값 | `true` | `false` |
| 수익률 추적 | 모의 데이터로 독립 계산 | 실전 데이터로 독립 계산 |
| 모드 전환 시 | 기존 데이터 유지 (삭제 안 함) | 기존 데이터 유지 (삭제 안 함) |
| 해외주식 | LS증권 모의투자 **미지원** | 지원 |
| 해외선물 | 지원 | 지원 |

### 모의투자 설정 방법

모의투자를 사용하려면 **credential과 노드 양쪽 모두** `paper_trading`을 설정해야 합니다.

```json
{
  "credentials": [
    {
      "credential_id": "broker-cred",
      "type": "broker_ls_overseas_futures",
      "data": [
        {"key": "appkey", "value": "...", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "...", "type": "password", "label": "App Secret"},
        {"key": "paper_trading", "value": true, "type": "boolean", "label": "모의투자"}
      ]
    }
  ],
  "nodes": [
    {
      "id": "broker",
      "type": "OverseasFuturesBrokerNode",
      "credential_id": "broker-cred",
      "paper_trading": true
    }
  ]
}
```

> **주의**: `paper_trading`은 credential 뿐만 아니라 **노드 설정에도 반드시 포함**해야 합니다. 한쪽만 설정하면 정상 동작하지 않습니다.

> **주의**: 해외주식(`OverseasStockBrokerNode`)은 LS증권 모의투자를 **지원하지 않습니다**. 모의투자는 해외선물(`OverseasFuturesBrokerNode`)에서만 사용 가능합니다.

---

## 5. 특정 날짜 기준 수익률 계산

특정 날짜 이후의 수익률만 따로 계산하는 기능을 지원합니다. 리스너 생성 시 `start_date`를 설정하면 해당 날짜 이후 체결된 거래만으로 수익률을 별도 계산합니다.

`start_date`가 설정되면 아래 항목들이 추가로 제공됩니다:

| 항목 | 설명 |
|------|------|
| `competition_start_date` | 기준 시작일 (YYYYMMDD 형식) |
| `competition_workflow_pnl_rate` | 시작일 이후 워크플로우 수익률 |
| `competition_workflow_pnl_amount` | 시작일 이후 워크플로우 손익금액 |
| `competition_account_pnl_rate` | 시작일 이후 계좌 전체 수익률 |
| `competition_account_pnl_amount` | 시작일 이후 계좌 전체 손익금액 |

상품별 수익률도 제공됩니다:

| 항목 | 설명 |
|------|------|
| `competition_workflow_stock_pnl_rate` | 기준일 이후 워크플로우 주식 수익률 |
| `competition_workflow_futures_pnl_rate` | 기준일 이후 워크플로우 선물 수익률 |
| `competition_account_stock_pnl_rate` | 기준일 이후 계좌 주식 수익률 |
| `competition_account_futures_pnl_rate` | 기준일 이후 계좌 선물 수익률 |

### 예시: 1월 15일부터의 수익률 추적

`start_date`를 `20260115`로 설정하면, 1월 15일 이전 매매 내역은 해당 기간 수익률 계산에서 제외됩니다.

- 1월 10일에 매수한 AAPL (+10%) → **기간 수익률에 미포함**
- 1월 20일에 매수한 NVDA (+3%) → **기간 수익률에 포함**

### 주요 동작

- **워크플로우 중지 후 재실행**: 같은 `start_date`로 리스너를 생성하면 이전 거래 기록을 포함하여 이어서 계산됩니다. (DB에 체결 내역이 영구 저장되므로 메모리 상태에 의존하지 않음)
- **기준 날짜 변경**: 새로운 `start_date`로 리스너를 생성하면 변경된 날짜 기준으로 재계산됩니다.
- **기간 수익률 해제**: `start_date` 없이 리스너를 생성하면 `competition_*` 필드가 모두 `None`으로 내려갑니다. 기존 거래 기록은 삭제되지 않으므로 나중에 다시 같은 날짜로 설정하면 이어서 계산됩니다.

---

## 6. 신뢰도 점수 (Trust Score)

| 항목 | 설명 |
|------|------|
| `trust_score` | 수익률 계산의 정확도 (0~100) |
| `anomaly_count` | 이상 탐지 횟수 |

**`trust_score`**는 워크플로우 수익률 계산이 얼마나 정확한지를 나타내는 점수입니다.

- **100점**: 모든 주문이 정확히 추적됨
- **80점 이상**: 신뢰할 수 있는 수준
- **80점 미만**: 일부 주문 매칭이 불완전할 수 있음

> **팁**: 신뢰도가 낮아지는 경우는 드뭅니다. 워크플로우 실행 중에 수동으로 같은 종목을 매매하면 추적이 어려워져 점수가 내려갈 수 있습니다.

---

## 7. 워크플로우 메타데이터

워크플로우 실행에 대한 부가 정보입니다.

| 항목 | 설명 |
|------|------|
| `workflow_start_datetime` | 워크플로우 최초 시작 시간 |
| `workflow_elapsed_days` | 워크플로우 경과 일수 |
| `total_position_count` | 전체 보유 종목 수 |

---

## 8. 수익률 데이터 예시

### 해외주식 실전투자

```json
{
  "product": "overseas_stock",
  "paper_trading": false,
  "currency": "USD",

  "workflow_pnl_rate": 2.35,
  "workflow_eval_amount": 10235.00,
  "workflow_buy_amount": 10000.00,
  "workflow_pnl_amount": 235.00,

  "other_pnl_rate": -1.20,
  "other_eval_amount": 4940.00,
  "other_buy_amount": 5000.00,
  "other_pnl_amount": -60.00,

  "total_pnl_rate": 1.17,
  "total_eval_amount": 15175.00,
  "total_buy_amount": 15000.00,
  "total_pnl_amount": 175.00,

  "trust_score": 100,
  "total_position_count": 5,

  "workflow_positions": [
    {
      "symbol": "AAPL",
      "exchange": "NASDAQ",
      "quantity": 10,
      "avg_price": 180.50,
      "current_price": 185.20,
      "pnl_amount": 47.00,
      "pnl_rate": 2.60
    }
  ],
  "other_positions": [
    {
      "symbol": "TSLA",
      "exchange": "NASDAQ",
      "quantity": 5,
      "avg_price": 250.00,
      "current_price": 247.00,
      "pnl_amount": -15.00,
      "pnl_rate": -1.20
    }
  ]
}
```

### 해외선물 모의투자

```json
{
  "product": "overseas_futures",
  "paper_trading": true,
  "currency": "USD",

  "workflow_pnl_rate": -0.85,
  "workflow_eval_amount": 9915.00,
  "workflow_buy_amount": 10000.00,
  "workflow_pnl_amount": -85.00,

  "trust_score": 100,
  "total_position_count": 1,

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
  ]
}
```

> **팁**: `workflow_pnl_rate`(워크플로우 수익률)가 전략의 실제 성과를 나타냅니다. `total_pnl_rate`(전체 수익률)에는 수동 매매 결과도 포함되어 있으므로, 전략 평가에는 `workflow_pnl_rate`를 기준으로 삼으세요.
