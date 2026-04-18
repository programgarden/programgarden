# live_bot (개발자 본인 운영용)

해외주식 실전계좌에서 **연속형 트레일링스탑 위험관리 + 나스닥 추세 필터 매수**를 자동으로 돌리는 봇.

## 파일

```
scripts/live_bot/
├── workflow.json                  # 워크플로우 정의
├── runner.py                      # 실행 엔트리포인트
├── plugins/
│   ├── __init__.py                # register_all() — 동적 플러그인 등록
│   └── scalable_trailing_stop.py  # 연속형 트레일링스탑 (Dynamic_ScalableTrailingStop)
├── data/                          # DB/로그 저장소 (자동 생성, gitignore)
└── README.md
```

## 필수 환경변수

`.env` 파일 또는 shell 환경변수로 주입:

```bash
# 프로젝트 루트의 .env 사용 (자동 로드됨)
LS_APPKEY=<LS증권 App Key>
LS_APPSECRET=<LS증권 App Secret>
TELEGRAM_TOKEN=<텔레그램 봇 토큰>
TELEGRAM_CHAT_ID=<텔레그램 채팅 ID>
```

키 이름은 `LS_APPKEY` / `APPKEY`, `TELEGRAM_TOKEN` / `TELEGRAM-TOKEN` 둘 다 인식.

## 실행

```bash
cd src/programgarden
poetry run python ../../scripts/live_bot/runner.py
```

Ctrl+C로 우아하게 종료됩니다.

## 전략 요약

### 실시간 위험관리 (WebSocket)
`OverseasStockRealAccountNode` → `scalable_trailing_stop` → 매도 주문 → 텔레그램

**연속형 트레일링스탑 공식** (HWM 기준 수익률 → 손절 라인):

| HWM 수익률 | trail_distance | stop (진입가 대비) |
|---:|---:|---:|
| 0% | — | -5% (고정) |
| 5% | 4% | +1% |
| 10% | 4% | +6% |
| 15% | 5.25% | +9.75% |
| 20% | 7% | +13% |
| 30% | 10.5% | +19.5% |
| 50% | 17.5% | +32.5% |

```
HWM ≤ 0%: stop = -initial_stop_pct (기본 5%)
HWM > 0%: trail = max(min_trail_pct, HWM × trail_factor)
          stop = HWM - trail
```

### 30분 주기 매수 (평일 미국장, KST 22:30~05:00)
1. 나스닥 ETF(QQQ) 90일 추세 양수 확인
2. ScreenerNode: NASDAQ / 시총 50억$+ / 거래량 100만주+
3. 보유 종목 제외
4. 각 종목 TSMOM 90일 추세 양수 + 변동성 조정
5. PER 5~30 필터
6. 예수금 `orderable_amount`의 10%씩 시장가 매수 (5종목 분산 = 50% 사용)
7. 텔레그램 알림

## 파라미터 튜닝

`workflow.json`에서 다음 값 조정:

- `scalable_trailing_stop.fields.initial_stop_pct`: 초기 손절 (기본 5)
- `scalable_trailing_stop.fields.min_trail_pct`: 최소 trail (기본 4)
- `scalable_trailing_stop.fields.trail_factor`: HWM 스케일 (기본 0.35)
- `schedule_buy.cron`: 매수 주기 (기본 `*/30 * * * 1-5`)
- `position_sizing.max_percent`: 종목당 매수 비중 (기본 10)
- `if_per_ok_upper.right`: PER 상한 (기본 30)

## 주의사항

- **실전계좌 실행 전 반드시 소액 검증**을 권장합니다.
- 해외주식 모의투자는 LS증권 미지원 — `paper_trading: false` 고정.
- 프로세스 중단 시 실시간 WebSocket 연결이 끊기므로 매도 기회를 놓칠 수 있습니다. 안정적인 서버에서 상시 실행하는 것을 권장합니다.
- `data/` 디렉토리에 워크플로우 상태/체크포인트가 저장됩니다. 이 폴더는 gitignore 되어 있으니 백업이 필요하면 별도 관리하세요.
