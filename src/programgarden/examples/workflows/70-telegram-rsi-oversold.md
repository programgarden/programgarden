# 70 - RSI 과매도 종목 텔레그램 알림

> **왕초보 질문**: "과매도 종목 있으면 텔레그램으로 알려줘"

감시 종목 중 RSI(14) 가 30 미만인 과매도 종목이 발견되면 텔레그램 알림을 보냅니다.

## 흐름

```
Start → Broker → Watchlist → Historical → RSI Condition → IfNode → Telegram
 시작    로그인   감시종목4개   60일일봉      RSI계산/필터    게이트    알림
```

## 핵심 아이디어

1. **감시 종목 정의**: `WatchlistNode.symbols` 배열에 4개 종목
2. **과거 데이터 조회**: 각 종목별 60일 일봉 (auto-iterate)
3. **RSI 계산 + 필터링**: `ConditionNode` 의 `RSI` 플러그인, `threshold=30, direction=below`
4. **존재 여부 체크**: `IfNode` 가 `nodes.rsi_condition.is_condition_met` (bool) 체크
5. **알림**: `passed_symbols` 목록을 텔레그램으로 전송

## 파라미터 조정

| 목표 | 설정 |
|------|------|
| 과매도 (기본) | `threshold: 30, direction: "below"` |
| 과매수 | `threshold: 70, direction: "above"` |
| 더 보수적 과매도 | `threshold: 20, direction: "below"` |
| 다른 기간 | `period: 9` (단기), `period: 21` (장기) |

## RSI 해석 가이드

- **RSI < 30**: 과매도 → 반등 가능성
- **RSI > 70**: 과매수 → 조정 가능성
- **RSI 50 근처**: 추세 없음

⚠️ RSI 는 **추세 없는 횡보 장세**에서 효과적이며, 강한 상승/하락 추세에서는 과매수/과매도 영역에 장기간 머무를 수 있습니다.

## passed_symbols 출력 예시

```json
[
  {"symbol": "NVDA", "exchange": "NASDAQ", "rsi": 28.5},
  {"symbol": "TSLA", "exchange": "NASDAQ", "rsi": 26.2}
]
```

텔레그램 메시지에 리스트가 그대로 출력되면 Python 리스트 문자열 형태로 표시됩니다. 더 예쁘게 포맷하려면 `FieldMappingNode` 나 커스텀 템플릿 변환이 필요합니다.

## 확장 아이디어

- **스케줄 실행**: 앞에 `ScheduleNode(cron="0 22 * * 1-5")` 추가 → 장 마감 후 스캔
- **매수 자동화**: IfNode `true` 분기에 `OverseasStockNewOrderNode` 추가
- **다른 조건**: RSI 대신 MACD, BollingerBands 등 다른 플러그인으로 교체
