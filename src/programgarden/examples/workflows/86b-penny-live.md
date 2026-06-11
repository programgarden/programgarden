# [86b] 동전주($1~2) 추세매수 + 5% 트레일링스탑 (소액 라이브검증 변종)

`86-trend-trailing-live` 의 **소액 예수금 변종**. 실계좌 예수금이 소액($11.27)일
때 86의 대형주($20+)는 종목당 45% 사이징으로도 0주가 되어 실매수가 불가능하다.
86b는 검증된 유동 동전주($1~2)로 유니버스를 교체해 **실제 체결**이 결정적으로
일어나도록 한 라이브 매수경로 검증 변종이다.

> ⚠️ 동전주는 변동성·유동성·상장폐지 리스크가 크다. 5% 트레일링스탑이 자주
> 트리거될 수 있다. 소액 실증·매수경로 검증 목적의 변종이다.

## 86 대비 변경점

| 항목 | 86 (대형주) | 86b (동전주) | 이유 |
|------|-------------|--------------|------|
| 유니버스 | g3190 NASDAQ 500 마스터 | **WatchlistNode 큐레이션 5종** (AEHL/ALLO/ALDX/AUTL/ALXO) | LS g3190 당일거래량 0·스캔캡 한계 회피, 검증된 유동 동전주 |
| `screener1.data_source` | `ls` | **`yfinance`** | LS 동전주 가격/거래량 신뢰도 한계 → yfinance 스냅샷 |
| `screener1` 가격대 | $20+ | **$1 ~ $2** | 소액 예수금으로 1~수주 매수 가능 |
| `screener1.volume_min` | (없음) | **50만** | 동전주 유동성 가드 (저유동 종목 배제) |
| **60일 TSMOM 추세필터** | 있음 | **제거** | 동전주는 비추세 → TSMOM 유지 시 매수 0건. 매수경로 결정적 검증을 위해 제거 |
| `cash_guard.right` | $100 | **$5** | 소액 예수금($11.27)이 게이트 통과 |

나머지(최대 2종목 슬롯 가드, 종목당 45% 지정가, TrailingStop v2.1
`trail_percent: 5.0`, 매수/매도 텔레그램, 09:30–16:30 KST 게이트)는 86과 동일.

> **추세 필터 트레이드오프**: 86b는 사용자 요구의 "추세 좋은 종목" 선별(TSMOM)을
> **포기**한다. 동전주는 추세성이 약해 TSMOM 필터를 걸면 매수가 0건이 되기
> 때문이다. 86b는 "소액으로 매수~매도~트레일링 전체 경로가 실계좌에서 도는지"를
> 결정적으로 검증하는 용도다. 추세 품질이 중요하면 예수금을 채우고 원본 86을
> 쓰는 것이 맞다.

## 사이징 (왜 체결되나 — 실측)

```
종목당 투자금 = orderable × 45% = $11.27 × 0.45 ≈ $5.07
ALLO @ $1.82 → int($5.07 / $1.82) = 2주 = $3.64   ← 실키 --read 실측
2종목 합계 ≈ $7~10 < $11.27 ✓
```

지정가(limit) 주문이라 체결가가 한도를 넘지 않아 초과 지출 위험 없음.

## 실행 (host-only, 거래시간 09:30–16:30 KST)

```bash
cd src/programgarden
poetry run python examples/programmer_example/test_86_trend_trailing_live.py --workflow 86b-penny-live.json --validate
poetry run python examples/programmer_example/test_86_trend_trailing_live.py --workflow 86b-penny-live.json --read
poetry run python examples/programmer_example/test_86_trend_trailing_live.py --workflow 86b-penny-live.json --live --confirm --cycles 3 --minutes 30
```

HWM DB 는 변종별로 분리된다: `examples/programmer_example/.runtime_data_86b-penny-live/`.

## 검증 상태

- L1 static `validate()`: PASS (is_valid=True)
- 실키 `--read`: PASS — screener1 5종 통과(errors=0), top2 = ALLO/AUTL,
  sizing ALLO 2주 @ $1.82 = $3.64 결정적 산출 (호스트 실계좌 검증)
- 심볼 바인딩 fix(commit 676b498/308facd) 적용 — market data 노드 실 종목코드 수신
- L4 실주문 라이브: 거래시간 내 호스트 러너로 수행 (사용자 승인 게이트)

## 알려진 한계

- **추세 필터 없음** (위 트레이드오프 참조) — 동전주 5종 중 가격/유동성/슬롯
  통과분을 시총 무관 매수. "추세 좋은 종목" 요건은 원본 86이 충족
- 큐레이션 동전주 5종은 고정 — 상폐/거래정지 시 수동 갱신 필요
- 슬롯 가드가 계좌 전체 보유 수 기준 (기존 보유 + 신규 합계 ≤2)
- 저유동 구간 지정가 미체결 가능 — 자동 재호가 없음 (다음 사이클 dedup)
- 5% 고정 트레일링이 동전주 변동성에 자주 트리거 → 잦은 회전 가능
