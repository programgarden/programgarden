# 자동화매매 Logic 가이드

## 1. 개요
조건들이 모여서 하나의 전략이 됩니다. 자동화 매매를 위해 여러 가지 조건(`condition`)을 조합하여 조건에 부합하는 종목들을 추출합니다. 그리고 조건 조합의 계산 방법은 `logic`에 작성합니다.

## 2. 지원되는 논리 연산자

### all
- 모든 조건이 True입니다.
- 예: 
```python
[True, True, True] -> True
[True, False] -> False
```

### any
- 하나 이상이 True입니다
- 예:
```python
[False, True, False] -> True
[False, False] -> False
```

### not
- 모든 조건이 만족하면 안 됩니다. 하나도 만족하지 않아야 합니다.

### xor
- 정확히 하나의 조건만 True인 경우입니다.
- 예: 
```python
[True, False, False] -> True
[True, True] -> False
```

### at_least 
- `threshold`가 필요합니다. 
- True인 조건의 개수가 threshold 이상이면 True입니다.
- 예:
```python
conditions = [True, False, True]
threshold = 2 -> True # (2 >= 2)
```

### at_most
- `threshold`가 필요합니다. 
- True인 조건의 개수가 threshold 이하이면 True입니다.
- 예:
```python
conditions = [True, False, False]
threshold = 1 -> True # (1 <= 1)
```

### exactly
- `threshold`가 필요합니다. 
- True인 조건의 개수가 threshold와 정확히 같아야 True입니다.
- 예:
```python
conditions = [True, True, False]
threshold = 2 -> True
```

### weighted
- `threshold`가 필요합니다. 
- 각 조건에 가중치(weight)를 붙여, True인 조건들의 가중치 합이 threshold 이상이면 True입니다.
- 가중치가 없으면 기본값은 0으로 처리되어서 조건이 통과되지 않습니다.
- DSL에서 조건 딕셔너리에 `"weight"` 값을 작성하면 해당 값이 플러그인이 반환하는 기본 weight보다 우선 적용됩니다.
- 예: 
```python
conditions = [True, True, False]
weights = [0.2, 0.1, 0.7]

threshold = 0.3 -> True (0.2 + 0.1 >= 0.3)
```
