# Time Stop (시간 초과 취소) 플러그인

## 플러그인 ID
`TimeStop`

## 설명
지정 시간이 초과된 미체결 주문을 취소합니다.

## 파라미터

| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `timeout_minutes` | int | 30 | 타임아웃 시간 (분) |

## DSL 예시

```json
{
  "id": "timeCancel",
  "type": "CancelOrderNode",
  "plugin": "TimeStop",
  "fields": {
    "timeout_minutes": 30
  }
}
```
