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
  "operator": "all",
  "conditions": [
    {
      "is_condition_met": "{{ nodes.rsi.result }}",
      "passed_symbols": "{{ nodes.rsi.passed_symbols }}"
    },
    {
      "is_condition_met": "{{ nodes.macd.result }}",
      "passed_symbols": "{{ nodes.macd.passed_symbols }}"
    }
  ]
}
```

**conditions 배열 항목 구조:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `is_condition_met` | expression | ✅ | 조건 통과 여부 바인딩 |
| `passed_symbols` | expression | ✅ | 통과한 종목 목록 바인딩 |
| `weight` | number | ❌ | 가중치 (기본: 1.0, weighted 연산자용) |

여러 ConditionNode의 결과를 LogicNode의 `conditions` 배열에서 명시적으로 바인딩합니다.

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
  "operator": "all",
  "conditions": [
    {"is_condition_met": "{{ nodes.condition1.result }}", "passed_symbols": "{{ nodes.condition1.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.condition2.result }}", "passed_symbols": "{{ nodes.condition2.passed_symbols }}"}
  ]
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
  "operator": "any",
  "conditions": [
    {"is_condition_met": "{{ nodes.condition1.result }}", "passed_symbols": "{{ nodes.condition1.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.condition2.result }}", "passed_symbols": "{{ nodes.condition2.passed_symbols }}"}
  ]
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
  "operator": "not",
  "conditions": [
    {"is_condition_met": "{{ nodes.condition1.result }}", "passed_symbols": "{{ nodes.condition1.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.condition2.result }}", "passed_symbols": "{{ nodes.condition2.passed_symbols }}"}
  ]
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
  "operator": "xor",
  "conditions": [
    {"is_condition_met": "{{ nodes.condition1.result }}", "passed_symbols": "{{ nodes.condition1.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.condition2.result }}", "passed_symbols": "{{ nodes.condition2.passed_symbols }}"}
  ]
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
  "operator": "at_least",
  "threshold": 2,
  "conditions": [
    {"is_condition_met": "{{ nodes.condition1.result }}", "passed_symbols": "{{ nodes.condition1.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.condition2.result }}", "passed_symbols": "{{ nodes.condition2.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.condition3.result }}", "passed_symbols": "{{ nodes.condition3.passed_symbols }}"}
  ]
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
  "operator": "at_most",
  "threshold": 1,
  "conditions": [
    {"is_condition_met": "{{ nodes.condition1.result }}", "passed_symbols": "{{ nodes.condition1.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.condition2.result }}", "passed_symbols": "{{ nodes.condition2.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.condition3.result }}", "passed_symbols": "{{ nodes.condition3.passed_symbols }}"}
  ]
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
  "operator": "exactly",
  "threshold": 2,
  "conditions": [
    {"is_condition_met": "{{ nodes.condition1.result }}", "passed_symbols": "{{ nodes.condition1.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.condition2.result }}", "passed_symbols": "{{ nodes.condition2.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.condition3.result }}", "passed_symbols": "{{ nodes.condition3.passed_symbols }}"}
  ]
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

각 조건에 weight를 설정합니다:

```json
{
  "nodes": [
    {
      "id": "rsi",
      "type": "ConditionNode",
      "plugin": "RSI",
      "fields": {"period": 14, "oversold": 30},
      "data": "{{ flatten(nodes.historical.values, 'time_series') }}"
    },
    {
      "id": "macd",
      "type": "ConditionNode",
      "plugin": "MACD",
      "fields": {},
      "data": "{{ flatten(nodes.historical.values, 'time_series') }}"
    },
    {
      "id": "volume",
      "type": "ConditionNode",
      "plugin": "VolumeSpike",
      "fields": {},
      "data": "{{ flatten(nodes.historical.values, 'time_series') }}"
    },
    {
      "id": "trend",
      "type": "ConditionNode",
      "plugin": "ADX",
      "fields": {},
      "data": "{{ flatten(nodes.historical.values, 'time_series') }}"
    },
    {
      "id": "logic",
      "type": "LogicNode",
      "operator": "weighted",
      "threshold": 0.6,
      "conditions": [
        {"is_condition_met": "{{ nodes.rsi.result }}", "passed_symbols": "{{ nodes.rsi.passed_symbols }}", "weight": 0.3},
        {"is_condition_met": "{{ nodes.macd.result }}", "passed_symbols": "{{ nodes.macd.passed_symbols }}", "weight": 0.3},
        {"is_condition_met": "{{ nodes.volume.result }}", "passed_symbols": "{{ nodes.volume.passed_symbols }}", "weight": 0.2},
        {"is_condition_met": "{{ nodes.trend.result }}", "passed_symbols": "{{ nodes.trend.passed_symbols }}", "weight": 0.2}
      ]
    }
  ],
  "edges": [
    {"from": "historical", "to": "rsi"},
    {"from": "historical", "to": "macd"},
    {"from": "historical", "to": "volume"},
    {"from": "historical", "to": "trend"},
    {"from": "rsi", "to": "logic"},
    {"from": "macd", "to": "logic"},
    {"from": "volume", "to": "logic"},
    {"from": "trend", "to": "logic"}
  ]
}
```

> ⚠️ **주의**: weight를 지정하지 않으면 기본값이 **1.0**입니다.

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
    {"id": "suneung", "type": "ConditionNode", "plugin": "Test1", "data": "..."},
    {"id": "naesin", "type": "ConditionNode", "plugin": "Test2", "data": "..."},
    {"id": "interview", "type": "ConditionNode", "plugin": "Interview", "data": "..."},
    {
      "id": "groupA",
      "type": "LogicNode",
      "operator": "any",
      "conditions": [
        {"is_condition_met": "{{ nodes.suneung.result }}", "passed_symbols": "{{ nodes.suneung.passed_symbols }}"},
        {"is_condition_met": "{{ nodes.naesin.result }}", "passed_symbols": "{{ nodes.naesin.passed_symbols }}"}
      ]
    },
    {
      "id": "finalLogic",
      "type": "LogicNode",
      "operator": "all",
      "conditions": [
        {"is_condition_met": "{{ nodes.groupA.result }}", "passed_symbols": "{{ nodes.groupA.passed_symbols }}"},
        {"is_condition_met": "{{ nodes.interview.result }}", "passed_symbols": "{{ nodes.interview.passed_symbols }}"}
      ]
    }
  ],
  "edges": [
    {"from": "suneung", "to": "groupA"},
    {"from": "naesin", "to": "groupA"},
    {"from": "groupA", "to": "finalLogic"},
    {"from": "interview", "to": "finalLogic"}
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
    {"id": "adx", "type": "ConditionNode", "plugin": "ADX", "fields": {"min_value": 25}, "data": "..."},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "fields": {"oversold": 30}, "data": "..."},
    {"id": "stochastic", "type": "ConditionNode", "plugin": "Stochastic", "fields": {"oversold": 20}, "data": "..."},
    {
      "id": "oversoldGroup",
      "type": "LogicNode",
      "operator": "any",
      "conditions": [
        {"is_condition_met": "{{ nodes.rsi.result }}", "passed_symbols": "{{ nodes.rsi.passed_symbols }}"},
        {"is_condition_met": "{{ nodes.stochastic.result }}", "passed_symbols": "{{ nodes.stochastic.passed_symbols }}"}
      ]
    },
    {
      "id": "finalLogic",
      "type": "LogicNode",
      "operator": "all",
      "conditions": [
        {"is_condition_met": "{{ nodes.adx.result }}", "passed_symbols": "{{ nodes.adx.passed_symbols }}"},
        {"is_condition_met": "{{ nodes.oversoldGroup.result }}", "passed_symbols": "{{ nodes.oversoldGroup.passed_symbols }}"}
      ]
    }
  ],
  "edges": [
    {"from": "rsi", "to": "oversoldGroup"},
    {"from": "stochastic", "to": "oversoldGroup"},
    {"from": "adx", "to": "finalLogic"},
    {"from": "oversoldGroup", "to": "finalLogic"}
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
  "operator": "all",
  "conditions": [
    {"is_condition_met": "{{ nodes.cond1.result }}", "passed_symbols": "{{ nodes.cond1.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.cond2.result }}", "passed_symbols": "{{ nodes.cond2.passed_symbols }}"}
  ]
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
  "operator": "any",
  "conditions": [
    {"is_condition_met": "{{ nodes.cond1.result }}", "passed_symbols": "{{ nodes.cond1.passed_symbols }}"},
    {"is_condition_met": "{{ nodes.cond2.result }}", "passed_symbols": "{{ nodes.cond2.passed_symbols }}"}
  ]
}
```

✅ 장점: 진입 기회 많음
❌ 단점: 거짓 신호 위험

---

### 패턴 3: 점수제 (가중치 합산)

**상황**: 여러 지표를 종합적으로 판단하고 싶음

```json
{
  "id": "logic",
  "type": "LogicNode",
  "operator": "weighted",
  "threshold": 0.6,
  "conditions": [
    {"is_condition_met": "{{ nodes.cond1.result }}", "passed_symbols": "{{ nodes.cond1.passed_symbols }}", "weight": 0.4},
    {"is_condition_met": "{{ nodes.cond2.result }}", "passed_symbols": "{{ nodes.cond2.passed_symbols }}", "weight": 0.35},
    {"is_condition_met": "{{ nodes.cond3.result }}", "passed_symbols": "{{ nodes.cond3.passed_symbols }}", "weight": 0.25}
  ]
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
    {"id": "adxFilter", "type": "ConditionNode", "plugin": "ADX", "fields": {"min_value": 25}, "data": "..."},
    {"id": "rsi", "type": "ConditionNode", "plugin": "RSI", "data": "..."},
    {"id": "stochasticRSI", "type": "ConditionNode", "plugin": "StochasticRSI", "data": "..."},
    {
      "id": "signalGroup",
      "type": "LogicNode",
      "operator": "any",
      "conditions": [
        {"is_condition_met": "{{ nodes.rsi.result }}", "passed_symbols": "{{ nodes.rsi.passed_symbols }}"},
        {"is_condition_met": "{{ nodes.stochasticRSI.result }}", "passed_symbols": "{{ nodes.stochasticRSI.passed_symbols }}"}
      ]
    },
    {
      "id": "finalLogic",
      "type": "LogicNode",
      "operator": "all",
      "conditions": [
        {"is_condition_met": "{{ nodes.adxFilter.result }}", "passed_symbols": "{{ nodes.adxFilter.passed_symbols }}"},
        {"is_condition_met": "{{ nodes.signalGroup.result }}", "passed_symbols": "{{ nodes.signalGroup.passed_symbols }}"}
      ]
    }
  ],
  "edges": [
    {"from": "rsi", "to": "signalGroup"},
    {"from": "stochasticRSI", "to": "signalGroup"},
    {"from": "adxFilter", "to": "finalLogic"},
    {"from": "signalGroup", "to": "finalLogic"}
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

## 8. conditions 입력 방법 (weighted 연산자 상세)

> 📌 **이 섹션은 `weighted` 연산자를 처음 사용하는 분을 위한 상세 가이드입니다.**

### 8.1 기본 개념

`weighted` 연산자는 각 조건에 **중요도(가중치)**를 부여합니다.
학교 성적처럼 중간고사 40%, 기말고사 60%로 비중을 다르게 주는 것과 같습니다.

### 8.2 입력 형식

LogicNode의 `conditions` 배열에서 각 항목에 `weight` 필드를 추가합니다:

```json
"conditions": [
  {"is_condition_met": "{{ nodes.rsiCondition.result }}", "passed_symbols": "{{ nodes.rsiCondition.passed_symbols }}", "weight": 0.4},
  {"is_condition_met": "{{ nodes.macdCondition.result }}", "passed_symbols": "{{ nodes.macdCondition.passed_symbols }}", "weight": 0.6}
]
```

| 구성요소 | 설명 | 예시 |
|----------|------|------|
| **is_condition_met** | 조건 통과 여부 바인딩 | `"{{ nodes.rsiCondition.result }}"` |
| **passed_symbols** | 통과 종목 목록 바인딩 | `"{{ nodes.rsiCondition.passed_symbols }}"` |
| **weight** | 0~1 사이의 소수 (0.4 = 40%), 선택사항 (기본: 1.0) | `0.4` |

### 8.3 실전 예시

#### 예시 1: RSI 40% + MACD 60%

RSI보다 MACD를 더 중요하게 보고 싶을 때:

```json
{
  "id": "logic",
  "type": "LogicNode",
  "operator": "weighted",
  "threshold": 0.6,
  "conditions": [
    {"is_condition_met": "{{ nodes.rsiCondition.result }}", "passed_symbols": "{{ nodes.rsiCondition.passed_symbols }}", "weight": 0.4},
    {"is_condition_met": "{{ nodes.macdCondition.result }}", "passed_symbols": "{{ nodes.macdCondition.passed_symbols }}", "weight": 0.6}
  ]
}
```

**결과 해석:**

| 상황 | RSI (0.4) | MACD (0.6) | 합계 | threshold 0.6 | 결과 |
|------|:---------:|:----------:|:----:|:-------------:|:----:|
| 둘 다 통과 | 0.4 | 0.6 | 1.0 | 1.0 ≥ 0.6 | ✅ 통과 |
| RSI만 통과 | 0.4 | 0 | 0.4 | 0.4 < 0.6 | ❌ 실패 |
| MACD만 통과 | 0 | 0.6 | 0.6 | 0.6 ≥ 0.6 | ✅ 통과 |
| 둘 다 실패 | 0 | 0 | 0 | 0 < 0.6 | ❌ 실패 |

> 💡 **해석**: MACD만 통과해도 60%이므로 통과! RSI만 통과하면 40%라 실패.

#### 예시 2: 3개 조건 균등 배분

모든 조건을 동등하게 취급할 때:

```json
{
  "id": "logic",
  "type": "LogicNode",
  "operator": "weighted",
  "threshold": 0.66,
  "conditions": [
    {"is_condition_met": "{{ nodes.rsiCondition.result }}", "passed_symbols": "{{ nodes.rsiCondition.passed_symbols }}", "weight": 0.33},
    {"is_condition_met": "{{ nodes.macdCondition.result }}", "passed_symbols": "{{ nodes.macdCondition.passed_symbols }}", "weight": 0.33},
    {"is_condition_met": "{{ nodes.volumeCondition.result }}", "passed_symbols": "{{ nodes.volumeCondition.passed_symbols }}", "weight": 0.34}
  ]
}
```

> 💡 **해석**: 3개 중 2개 이상 통과해야 66% 이상! (0.33 + 0.33 = 0.66)

#### 예시 3: 핵심 조건 + 보조 조건

핵심 지표는 높은 가중치, 보조 지표는 낮은 가중치:

```json
{
  "conditions": [
    {"is_condition_met": "{{ nodes.rsiCondition.result }}", "passed_symbols": "{{ nodes.rsiCondition.passed_symbols }}", "weight": 0.5},
    {"is_condition_met": "{{ nodes.macdCondition.result }}", "passed_symbols": "{{ nodes.macdCondition.passed_symbols }}", "weight": 0.3},
    {"is_condition_met": "{{ nodes.volumeCondition.result }}", "passed_symbols": "{{ nodes.volumeCondition.passed_symbols }}", "weight": 0.2}
  ],
  "threshold": 0.5
}
```

> 💡 **해석**: RSI만 통과해도 50%로 통과 가능! 보조 지표는 추가 확신용.

### 8.4 자주 하는 실수

#### ❌ 실수 1: is_condition_met 또는 passed_symbols 누락

```json
// 잘못된 예: passed_symbols 누락
"conditions": [
  {"is_condition_met": "{{ nodes.rsi.result }}", "weight": 0.5}
]
```

→ 필수 필드 누락으로 오류 발생

#### ❌ 실수 2: 가중치 합계가 1이 아님

```json
// 주의: 합계가 1.5
"conditions": [
  {"...", "weight": 0.5},
  {"...", "weight": 0.5},
  {"...", "weight": 0.5}
]
```

→ 동작은 하지만 threshold 해석이 어려움

#### ❌ 실수 3: conditions 없이 weighted 사용

```json
{
  "operator": "weighted",
  "threshold": 0.6
  // conditions 누락!
}
```

→ 조건이 없어서 항상 실패

#### ✅ 올바른 예시

```json
{
  "operator": "weighted",
  "threshold": 0.6,
  "conditions": [
    {"is_condition_met": "{{ nodes.rsiCondition.result }}", "passed_symbols": "{{ nodes.rsiCondition.passed_symbols }}", "weight": 0.4},
    {"is_condition_met": "{{ nodes.macdCondition.result }}", "passed_symbols": "{{ nodes.macdCondition.passed_symbols }}", "weight": 0.6}
  ]
}
```

### 8.5 가중치 설계 팁

| 상황 | 권장 설정 |
|------|----------|
| 모든 조건 동등 | 균등 배분 (1/n) |
| 핵심 지표 1개 + 보조 여러개 | 핵심 50~60%, 나머지 분배 |
| 확인용 조건 추가 | 기존 유지 + 새 조건에 10~20% |

**가중치 합계 = 1.0 권장 이유:**
- threshold를 백분율로 직관적 해석 가능
- 0.6 = "60% 이상의 조건이 충족되면"

---

## 9. 용어 정리

| 용어 | 의미 |
|------|------|
| **LogicNode** | 여러 조건을 조합하는 노드 |
| **operator** | 조건 조합 방식 (all, any, weighted 등) |
| **threshold** | 기준값 (몇 개 이상, 몇 점 이상 등) |
| **weight** | 가중치, 중요도 (0~1 사이 소수로 표현) |
| **edges** | 노드 간 데이터 흐름 연결 |
| **통과/실패** | 조건을 만족하면 통과(True), 만족 못하면 실패(False) |
