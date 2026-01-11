# 🕸️ Spider Chart (Radar) 포트폴리오 분석 예제

종목별 기술적 지표를 **레이더(스파이더) 차트**로 비교 분석하는 예제입니다.

## 개요

5종목(AAPL, MSFT, GOOGL, NVDA, TSLA)의 주요 기술적 지표를 다차원으로 비교합니다.

### 분석 지표
| 지표 | 설명 | 범위 |
|------|------|------|
| RSI | 상대강도지수 | 0-100 |
| MA 괴리율 | 20일 이동평균 대비 괴리율 | % |
| 거래량 비율 | 20일 평균 거래량 대비 | 배수 |
| 변동성 | 연환산 변동성 | % |
| 모멘텀 | 20일 모멘텀 | % |

## 워크플로우 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Spider Chart 포트폴리오 분석                                                │
│                                                                              │
│  StartNode → BrokerNode → WatchlistNode → HistoricalDataNode                 │
│                                                    │                         │
│                           ┌─────────────┬─────────┼─────────┬─────────┐     │
│                           ▼             ▼         ▼         ▼         ▼     │
│                      RSI조건      MA괴리율    거래량     변동성    모멘텀    │
│                           │             │         │         │         │     │
│                           └─────────────┴─────────┼─────────┴─────────┘     │
│                                                   ▼                          │
│                                            DisplayNode                       │
│                                         (radar chart)                        │
│                                                   │                          │
│                                                   ▼                          │
│                                            DisplayNode                       │
│                                            (table)                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 노드 구성

### 1. 인프라 계층 (Infra Layer)
- **StartNode**: 워크플로우 시작점
- **BrokerNode**: LS증권 해외주식 API 연결

### 2. 종목 계층 (Symbol Layer)
- **WatchlistNode**: 분석 대상 종목 정의 (AAPL, MSFT, GOOGL, NVDA, TSLA)

### 3. 데이터 계층 (Data Layer)
- **HistoricalDataNode**: 과거 3개월 일봉 데이터 조회

### 4. 조건 계층 (Condition Layer)
- **RSI ConditionNode**: RSI(14) 계산
- **MA ConditionNode**: 20일 이동평균 괴리율 계산
- **Volume ConditionNode**: 20일 평균 대비 거래량 비율
- **Volatility ConditionNode**: 연환산 변동성
- **Momentum ConditionNode**: 20일 모멘텀

### 5. 디스플레이 계층 (Display Layer)
- **Spider Chart DisplayNode**: 5종목의 5개 지표를 레이더 차트로 시각화
- **Summary Table DisplayNode**: 상세 지표 값 테이블

## 실행 방법

### 방법 1: 독립 실행
```bash
cd src/programgarden
poetry run python examples/workflow_editor/02_spider_chart/run.py
```

### 방법 2: 웹 UI (01_flow_visualizer 서버 활용)
```bash
cd src/programgarden/examples/workflow_editor/01_flow_visualizer
poetry run python server.py
# 브라우저에서 http://localhost:8000 접속
```

## DisplayNode radar 차트 설정

```python
{
    "id": "spiderChart",
    "type": "DisplayNode",
    "category": "display",
    "chart_type": "radar",  # 레이더 차트 타입
    "title": "🕸️ 종목별 기술적 지표 비교",
    "options": {
        "labels": ["RSI", "MA괴리율", "거래량", "변동성", "모멘텀"],
        "normalize": True,  # 0-100 정규화
        "colors": ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444"],
    },
}
```

## 데이터 포맷

### 입력 데이터 (ConditionNode → DisplayNode)
```json
[
    {"symbol": "AAPL", "values": [65.2, 2.1, 1.15, 18.5, 5.3]},
    {"symbol": "MSFT", "values": [58.7, -1.2, 0.92, 15.2, 3.1]},
    {"symbol": "GOOGL", "values": [71.3, 3.5, 1.45, 21.3, 8.2]},
    {"symbol": "NVDA", "values": [45.2, -5.3, 2.10, 35.6, -2.1]},
    {"symbol": "TSLA", "values": [52.8, 1.8, 1.78, 42.1, 4.5]}
]
```

### 정규화 후 (normalize: true)
각 지표별로 최대값을 100으로 정규화하여 비교 가능한 형태로 변환

## Chart.js 레이더 차트

프론트엔드에서 Chart.js 라이브러리를 사용하여 렌더링합니다.

```javascript
new Chart(canvas, {
    type: 'radar',
    data: {
        labels: ['RSI', 'MA괴리율', '거래량', '변동성', '모멘텀'],
        datasets: [
            {
                label: 'AAPL',
                data: [65.2, 52.5, 54.8, 52.0, 64.6],
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                borderColor: '#3b82f6',
            },
            // ... 다른 종목들
        ]
    },
    options: {
        scales: {
            r: { beginAtZero: true, max: 100 }
        }
    }
});
```

## 활용 시나리오

### 1. 포트폴리오 균형 분석
- 5종목의 지표 분포를 한눈에 파악
- 특정 지표에 치우친 종목 식별

### 2. 종목 선정 기준 시각화
- RSI가 낮으면서 모멘텀이 높은 종목
- 변동성이 낮으면서 거래량이 안정적인 종목

### 3. 리스크 분산 확인
- 각 종목의 특성이 다양하게 분포되어 있는지 확인
- 상관관계가 낮은 종목 조합 파악

## 확장 가능성

- **지표 추가**: Bollinger Band Width, ATR, ADX 등
- **종목 그룹 비교**: 섹터별, 시가총액별 그룹 비교
- **시계열 애니메이션**: 시간에 따른 레이더 차트 변화 추적

## 참고

- [Chart.js Radar Chart 문서](https://www.chartjs.org/docs/latest/charts/radar.html)
- [DisplayNode 정의](../../../../core/programgarden_core/nodes/display.py)
