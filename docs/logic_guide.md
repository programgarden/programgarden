# 자동화매매 Logic 가이드

> 📌 **이 문서는 코딩을 몰라도 이해할 수 있도록 작성되었습니다.**

## 1. logic이란?

### 쉽게 말하면

자동매매에서 **"언제 주식을 살까?"**를 결정할 때, 여러 가지 조건을 확인합니다.

예를 들어:
- RSI가 30 이하인가? ✅
- 거래량이 평소보다 많은가? ✅
- MACD가 상승 신호인가? ❌

이렇게 3가지 조건이 있을 때, **"3개 다 만족해야 사자"**인지, **"1개만 만족해도 사자"**인지를 정하는 것이 바로 **`logic`**입니다.

### 일상생활 비유

| logic | 일상생활 예시 |
|-------|-------------|
| `all` | 면접에서 **모든 질문**에 잘 대답해야 합격 |
| `any` | 복권에서 **하나라도** 번호가 맞으면 당첨 |
| `weighted` | 학교 성적에서 중간고사 40% + 기말고사 60%로 **점수 합산** |

---

## 2. LogicNode 사용하기

노드 기반 DSL에서는 **LogicNode**를 사용해 여러 조건을 조합합니다.

### 기본 구조

```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "all",
    "threshold": 2
  }
}
```

여러 ConditionNode의 결과를 LogicNode에 연결합니다:

```json
"edges": [
  {"from": "rsi.result", "to": "logic.input"},
  {"from": "macd.result", "to": "logic.input"},
  {"from": "volume.result", "to": "logic.input"},
  {"from": "logic.passed_symbols", "to": "order.symbols"}
]
```

---

## 3. 지원되는 논리 연산자

### 한눈에 보기

| 연산자 | 한글 의미 | 설명 | 기준값(threshold) 필요? |
|--------|----------|------|:----------------------:|
| `all` | 모두 만족 | 모든 조건을 통과해야 함 | ✗ |
| `any` | 하나라도 | 하나 이상 통과하면 됨 | ✗ |
| `not` | 모두 불만족 | 모든 조건이 실패해야 함 | ✗ |
| `xor` | 딱 하나만 | 정확히 1개만 통과해야 함 | ✗ |
| `at_least` | N개 이상 | N개 이상 통과해야 함 | ✓ |
| `at_most` | N개 이하 | N개 이하만 통과해야 함 | ✓ |
| `exactly` | 정확히 N개 | 딱 N개만 통과해야 함 | ✓ |
| `weighted` | 가중치 합산 | 점수 합계가 기준 이상이면 통과 | ✓ |

---

### all (모두 만족)

**의미**: 설정한 **모든 조건**이 통과해야 최종 통과입니다.

**실생활 비유**: 대학 입시에서 수능 **그리고** 내신 **그리고** 면접 모두 통과해야 합격

**투자 예시**: RSI가 과매도 **그리고** 거래량 급증 **그리고** MACD 골든크로스 → 3개 다 만족하면 매수

| 조건1 | 조건2 | 조건3 | 결과 |
|:-----:|:-----:|:-----:|:----:|
| ✅ | ✅ | ✅ | ✅ 통과 |
| ✅ | ✅ | ❌ | ❌ 실패 |
| ✅ | ❌ | ❌ | ❌ 실패 |

**DSL 작성 예시**:
```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "all"
  }
}
```

---

### any (하나라도)

**의미**: 설정한 조건 중 **하나 이상**만 통과하면 최종 통과입니다.

**실생활 비유**: 취업할 때 A회사 **또는** B회사 **또는** C회사 중 하나만 붙어도 성공

**투자 예시**: RSI 과매도 **또는** 볼린저밴드 하단 터치 **또는** 스토캐스틱 과매도 → 하나만 만족해도 매수

| 조건1 | 조건2 | 조건3 | 결과 |
|:-----:|:-----:|:-----:|:----:|
| ❌ | ❌ | ✅ | ✅ 통과 |
| ✅ | ❌ | ❌ | ✅ 통과 |
| ❌ | ❌ | ❌ | ❌ 실패 |

**DSL 작성 예시**:
```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "any"
  }
}
```

---

### not (모두 불만족)

**의미**: 설정한 **모든 조건이 실패**해야 최종 통과입니다. (반대로 하나라도 통과하면 실패)

**실생활 비유**: 알레르기 검사에서 **어떤 알레르기도 없어야** 건강 판정

**투자 예시**: 급락 신호 **없고** 과열 신호 **없고** 악재 뉴스 **없으면** → 안전하다고 판단

| 조건1 | 조건2 | 조건3 | 결과 |
|:-----:|:-----:|:-----:|:----:|
| ❌ | ❌ | ❌ | ✅ 통과 (모두 실패) |
| ❌ | ✅ | ❌ | ❌ 실패 (하나 통과) |
| ✅ | ✅ | ✅ | ❌ 실패 |

**DSL 작성 예시**:
```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "not"
  }
}
```

---

### xor (딱 하나만)

**의미**: **정확히 1개**의 조건만 통과해야 합니다. 0개나 2개 이상이면 실패입니다.

**실생활 비유**: 점심 메뉴 선택에서 짜장면 **또는** 짬뽕 중 **딱 하나만** 골라야 함 (둘 다 고르면 안 됨)

**투자 예시**: 상승 신호 **또는** 하락 신호 중 **딱 하나만** 있어야 방향이 명확하다고 판단

| 조건1 | 조건2 | 조건3 | 결과 |
|:-----:|:-----:|:-----:|:----:|
| ✅ | ❌ | ❌ | ✅ 통과 (1개만 통과) |
| ✅ | ✅ | ❌ | ❌ 실패 (2개 통과) |
| ❌ | ❌ | ❌ | ❌ 실패 (0개 통과) |

**DSL 작성 예시**:
```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "xor"
  }
}
```

---

### at_least (N개 이상)

**의미**: 통과한 조건의 개수가 **N개 이상**이면 최종 통과입니다.

**실생활 비유**: 시험에서 10문제 중 **6문제 이상** 맞으면 합격

**투자 예시**: 5개 기술지표 중 **3개 이상** 매수 신호면 진입

| 조건1 | 조건2 | 조건3 | threshold=2 | 결과 |
|:-----:|:-----:|:-----:|:-----------:|:----:|
| ✅ | ✅ | ❌ | 2개 이상 필요 | ✅ 통과 (2개 ≥ 2) |
| ✅ | ❌ | ❌ | 2개 이상 필요 | ❌ 실패 (1개 < 2) |
| ✅ | ✅ | ✅ | 2개 이상 필요 | ✅ 통과 (3개 ≥ 2) |

**DSL 작성 예시**:
```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "at_least",
    "threshold": 2
  }
}
```

---

### at_most (N개 이하)

**의미**: 통과한 조건의 개수가 **N개 이하**여야 최종 통과입니다.

**실생활 비유**: 다이어트 중 하루에 **2끼 이하**만 먹어야 함

**투자 예시**: 위험 신호가 **1개 이하**일 때만 매수 (위험 신호가 많으면 진입 안 함)

| 조건1 | 조건2 | 조건3 | threshold=1 | 결과 |
|:-----:|:-----:|:-----:|:-----------:|:----:|
| ✅ | ❌ | ❌ | 1개 이하 필요 | ✅ 통과 (1개 ≤ 1) |
| ✅ | ✅ | ❌ | 1개 이하 필요 | ❌ 실패 (2개 > 1) |
| ❌ | ❌ | ❌ | 1개 이하 필요 | ✅ 통과 (0개 ≤ 1) |

**DSL 작성 예시**:
```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "at_most",
    "threshold": 1
  }
}
```

---

### exactly (정확히 N개)

**의미**: 통과한 조건의 개수가 **정확히 N개**여야 최종 통과입니다.

**실생활 비유**: 복권에서 **정확히 3개** 번호가 일치해야 3등 당첨

**투자 예시**: 매수 신호가 **정확히 2개**일 때 (너무 적으면 확신 부족, 너무 많으면 이미 늦음)

| 조건1 | 조건2 | 조건3 | threshold=2 | 결과 |
|:-----:|:-----:|:-----:|:-----------:|:----:|
| ✅ | ✅ | ❌ | 정확히 2개 | ✅ 통과 (2개 = 2) |
| ✅ | ❌ | ❌ | 정확히 2개 | ❌ 실패 (1개 ≠ 2) |
| ✅ | ✅ | ✅ | 정확히 2개 | ❌ 실패 (3개 ≠ 2) |

**DSL 작성 예시**:
```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "exactly",
    "threshold": 2
  }
}
```

---

### weighted (가중치 합산)

**의미**: 각 조건에 **중요도(가중치)**를 부여하고, 통과한 조건들의 **점수 합계**가 기준 이상이면 통과입니다.

**실생활 비유**: 학교 성적 계산
- 중간고사(30%) + 기말고사(40%) + 과제(30%) = 총점
- 총점이 60점 이상이면 통과

**투자 예시**: 
- RSI 신호(30점) + MACD 신호(30점) + 거래량(20점) + 추세(20점)
- 합계가 60점 이상이면 매수

| 조건 | 가중치 | 결과 | 획득 점수 |
|------|:------:|:----:|:---------:|
| RSI | 0.3 (30%) | ✅ | 0.3 |
| MACD | 0.3 (30%) | ✅ | 0.3 |
| 거래량 | 0.2 (20%) | ❌ | 0 |
| 추세 | 0.2 (20%) | ❌ | 0 |
| **합계** | | | **0.6** |

→ threshold가 0.6이면 **통과** (0.6 ≥ 0.6)
→ threshold가 0.7이면 **실패** (0.6 < 0.7)

**DSL 작성 예시**:

먼저 각 ConditionNode에서 weight를 설정합니다:

```json
{
  "nodes": [
    {
      "id": "rsi",
      "type": "ConditionNode",
      "plugin": "RSI",
      "params": {"period": 14, "oversold": 30},
      "config": {"weight": 0.3}
    },
    {
      "id": "macd",
      "type": "ConditionNode",
      "plugin": "MACD",
      "params": {},
      "config": {"weight": 0.3}
    },
    {
      "id": "volume",
      "type": "ConditionNode",
      "plugin": "VolumeSpike",
      "params": {},
      "config": {"weight": 0.2}
    },
    {
      "id": "trend",
      "type": "ConditionNode",
      "plugin": "ADX",
      "params": {},
      "config": {"weight": 0.2}
    },
    {
      "id": "logic",
      "type": "LogicNode",
      "config": {
        "operator": "weighted",
        "threshold": 0.6
      }
    }
  ],
  "edges": [
    {"from": "rsi.result", "to": "logic.input"},
    {"from": "macd.result", "to": "logic.input"},
    {"from": "volume.result", "to": "logic.input"},
    {"from": "trend.result", "to": "logic.input"}
  ]
}
```

> ⚠️ **주의**: weight를 지정하지 않으면 기본값이 **0**이므로, 조건이 통과해도 점수에 반영되지 않습니다.

---

## 4. 중첩 조건 (조건 안에 조건 넣기)

### 중첩이란?

조건을 **그룹으로 묶어서** 더 복잡한 로직을 만드는 것입니다.

**실생활 비유**: 대학 입시 조건
- (수능 1등급 **또는** 내신 1등급) **그리고** (면접 통과)

이것을 분해하면:
1. 그룹 A: 수능 1등급 **또는** 내신 1등급 → `any`
2. 최종: 그룹 A **그리고** 면접 통과 → `all`

### 4.1 노드 기반 중첩 구조

노드 기반 DSL에서는 **여러 LogicNode를 연결**하여 중첩을 구현합니다.

**그림으로 보기**:
```
┌────────────────────────────────────┐
│         LogicNode (all)            │ ← 최종 결과
│  ┌──────────────┐  ┌────────────┐  │
│  │ LogicNode    │  │ Condition  │  │
│  │ (any)        │  │ 면접       │  │
│  │ ┌─────┐┌────┐│  │            │  │
│  │ │수능 ││내신││  │            │  │
│  │ └─────┘└────┘│  │            │  │
│  └──────────────┘  └────────────┘  │
└────────────────────────────────────┘
```

**DSL 예시**:
```json
{
  "nodes": [
    {"id": "suneung", "type": "ConditionNode", "plugin": "Test1"},
    {"id": "naesin", "type": "ConditionNode", "plugin": "Test2"},
    {"id": "interview", "type": "ConditionNode", "plugin": "Interview"},
    {
      "id": "groupA",
      "type": "LogicNode",
      "config": {"operator": "any"}
    },
    {
      "id": "finalLogic",
      "type": "LogicNode",
      "config": {"operator": "all"}
    }
  ],
  "edges": [
    {"from": "suneung.result", "to": "groupA.input"},
    {"from": "naesin.result", "to": "groupA.input"},
    {"from": "groupA.result", "to": "finalLogic.input"},
    {"from": "interview.result", "to": "finalLogic.input"}
  ]
}
```

### 4.2 실전 예시: 복합 조건 만들기

**목표**: "추세가 강할 때, 과매도 신호가 있으면 매수"

**분해**:
1. 추세 강도 확인: ADX가 25 이상
2. 과매도 신호: RSI **또는** 스토캐스틱 중 하나

**그림으로 보기**:
```
최종 결과 = 추세 확인 AND 과매도 신호
            │
            ├── 추세: ADX ≥ 25
            │
            └── 과매도 (OR 그룹)
                  ├── RSI ≤ 30
                  └── Stochastic ≤ 20
```

**DSL 예시**:
```json
{
  "nodes": [
    {"id": "adx", "type": "ConditionNode", "plugin": "ADX", "params": {"min_value": 25}},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "params": {"oversold": 30}},
    {"id": "stochastic", "type": "ConditionNode", "plugin": "Stochastic", "params": {"oversold": 20}},
    {
      "id": "oversoldGroup",
      "type": "LogicNode",
      "config": {"operator": "any"}
    },
    {
      "id": "finalLogic",
      "type": "LogicNode",
      "config": {"operator": "all"}
    }
  ],
  "edges": [
    {"from": "rsi.result", "to": "oversoldGroup.input"},
    {"from": "stochastic.result", "to": "oversoldGroup.input"},
    {"from": "adx.result", "to": "finalLogic.input"},
    {"from": "oversoldGroup.result", "to": "finalLogic.input"},
    {"from": "finalLogic.passed_symbols", "to": "order.symbols"}
  ]
}
```

---

## 5. position_side 합성 (해외선물 전용)

해외선물에서는 **매수(long)할지 매도(short)할지** 방향을 결정해야 합니다.

| 값 | 의미 | 설명 |
|----|------|------|
| `long` | 📈 매수 | 가격 상승에 베팅 |
| `short` | 📉 매도 | 가격 하락에 베팅 |
| `neutral` | ⚖️ 중립 | 방향 판단 없음 (필터 역할) |
| `flat` | 🚫 진입 안 함 | 신호 없음 |

**전파 규칙**:
1. 상위 조건이 방향을 정하면 → 상위 방향 사용
2. 상위가 중립이면 → 하위 조건 중 long/short 사용
3. 전부 neutral이면 → 방향 결정 불가, **주문 실행 안 됨**

---

## 6. 자주 사용하는 패턴 모음

### 패턴 1: 보수적 진입 (모든 조건 만족)

**상황**: 확실할 때만 진입하고 싶음

```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {"operator": "all"}
}
```

✅ 장점: 거짓 신호 감소
❌ 단점: 진입 기회 적음

---

### 패턴 2: 적극적 진입 (하나만 만족해도)

**상황**: 기회를 놓치고 싶지 않음

```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {"operator": "any"}
}
```

✅ 장점: 진입 기회 많음
❌ 단점: 거짓 신호 위험

---

### 패턴 3: 점수제 (가중치 합산)

**상황**: 여러 지표를 종합적으로 판단하고 싶음

각 조건에 weight 설정 후:

```json
{
  "id": "logic",
  "type": "LogicNode",
  "config": {
    "operator": "weighted",
    "threshold": 0.6
  }
}
```

✅ 장점: 균형 잡힌 판단
❌ 단점: 가중치 설정이 어려움

---

### 패턴 4: 필터 + 신호 조합

**상황**: 조건이 맞을 때만, 신호를 기다림

```json
{
  "nodes": [
    {"id": "adxFilter", "type": "ConditionNode", "plugin": "ADX", "params": {"min_value": 25}},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI"},
    {"id": "stochasticRSI", "type": "ConditionNode", "plugin": "StochasticRSI"},
    {"id": "signalGroup", "type": "LogicNode", "config": {"operator": "any"}},
    {"id": "finalLogic", "type": "LogicNode", "config": {"operator": "all"}}
  ],
  "edges": [
    {"from": "rsi.result", "to": "signalGroup.input"},
    {"from": "stochasticRSI.result", "to": "signalGroup.input"},
    {"from": "adxFilter.result", "to": "finalLogic.input"},
    {"from": "signalGroup.result", "to": "finalLogic.input"}
  ]
}
```

✅ 장점: 추세 방향에서만 진입
❌ 단점: 횡보장에서 기회 없음

---

## 7. 주의사항 체크리스트

### ✅ 기본 체크

| 항목 | 확인 |
|------|------|
| `at_least`, `at_most`, `exactly`, `weighted` 사용 시 `threshold` 작성했나요? | ☐ |
| `weighted` 사용 시 모든 조건에 `weight` 지정했나요? | ☐ |
| weight 값들의 합이 threshold보다 큰가요? | ☐ |

### ⚠️ 해외선물 사용자

| 항목 | 확인 |
|------|------|
| 최소 하나의 조건이 `long` 또는 `short`를 반환하나요? | ☐ |
| 모든 조건이 `neutral`이면 주문이 실행되지 않습니다 | ☐ |

### 💡 권장사항

| 항목 | 권장 |
|------|------|
| LogicNode 중첩 깊이 | 3단계 이하 |
| 한 LogicNode에 연결하는 조건 개수 | 5개 이하 |
| 테스트 | paper_trading: true로 먼저 확인 |

---

## 8. 용어 정리

| 용어 | 의미 |
|------|------|
| **LogicNode** | 여러 조건을 조합하는 노드 |
| **operator** | 조건 조합 방식 (all, any, weighted 등) |
| **threshold** | 기준값 (몇 개 이상, 몇 점 이상 등) |
| **weight** | 가중치, 중요도 (0~1 사이 소수로 표현) |
| **edges** | 노드 간 데이터 흐름 연결 |
| **통과/실패** | 조건을 만족하면 통과(True), 만족 못하면 실패(False) |
