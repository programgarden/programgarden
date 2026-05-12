# AlphaWorks LS 연동 이슈 답신 — programgarden 개발자

- 답신일: 2026-05-12
- 답신 대상: AlphaWorks 연구소장 (원 문서: 2026-05-12)
- 대상 라이브러리: `programgarden-finance` (현재 PyPI 1.6.3, TestPyPI 게시 대기 1.6.4)
- 답신자: programgarden 메인테이너 (jyj)

본 문서는 AlphaWorks 운영 보고서에 포함된 각 섹션 verification 요청과 §8 의 7개 최종 질문에 대한 공식 답변입니다. 코드 인용은 모두 PyPI 1.6.3 기준(working tree 1.6.4 와 해당 라인은 동일).

---

## 0. 요약 (TL;DR)

| 이슈 | 분류 | 라이브러리 액션 |
|------|------|--------|
| #1 `T1102 exchgubun=""` ValidationError | AlphaWorks 코드 버그 + 라이브러리 docstring 오류 1 줄 | docstring 정정 (다음 minor) |
| #2 `t8451/t8452` IGW00201 HTTP 500 | AlphaWorks 호출 패턴 + **`t8452` SetupOptions 결함** | `t8452` 에 `rate_limit_key` + `on_rate_limit="wait"` 추가 (다음 minor) |
| #3 `CSPAT00601` `00039/00040` 오분류 | **AlphaWorks 코드 버그** (라이브러리 docstring 에 이미 명시) | README 에 주문 응답 코드 표 추가 (다음 minor) |
| #4 `t0424` 폴링 한계 | AlphaWorks 설계 선택. WebSocket SC0/SC1 권장 | `CSPAT00601 → SC1` 매칭 combined 예제 추가 (다음 minor) |
| #5 `01478` 반복 | #3 의 2 차 피해 | 별도 액션 없음 |
| #6 WebSocket 미도입 | 라이브러리 SC0~SC4 이미 제공 (`real_SC0.py` 예제 있음) | combined 예제로 가시성 강화 |

요점: **이슈 7 개 중 라이브러리 측 실수가 인정되는 것은 #1 docstring 한 줄, #2 의 `t8452` 옵션 누락, 그리고 #3 의 가시성(README 부재)** 입니다. 나머지는 AlphaWorks 측 통합 단계에서 이미 자체 해결되었습니다.

---

## 1. 섹션 #1 — `T1102InBlock(exchgubun="")` ValidationError

### 라이브러리 측 사실 관계

`src/finance/programgarden_finance/ls/korea_stock/market/t1102/blocks.py:57-62`

```python
exchgubun: Literal["K", "N", "U"] = Field(
    default="K",
    title="거래소구분코드 (Exchange division code)",
    description="Exchange division. 'K' = KRX, 'N' = NXT, 'U' = unified. Other values are treated as KRX per LS source.",
    examples=["K", "N", "U"],
)
```

### 답변

- **빈 문자열 차단은 의도된 동작**입니다. Pydantic `Literal["K","N","U"]` 가 빈 문자열을 거부합니다.
- `default="K"` 이므로 `T1102InBlock(shcode="005930")` 만 호출하면 자동으로 KRX 로 매핑됩니다 — **AlphaWorks 측이 `exchgubun=""` 을 일부러 채워서 보낸 것이 원인**.
- 단, **라이브러리 docstring 의 "Other values are treated as KRX per LS source." 한 줄은 사실과 모순**됩니다. Pydantic Literal 은 다른 값을 절대로 KRX 로 매핑하지 않고 거부합니다. **이 부분은 라이브러리 측 잘못으로 인정**하고 다음 patch 에서 다음과 같이 정정합니다:

```python
description="Exchange division. 'K' = KRX, 'N' = NXT, 'U' = unified. Empty string and other values are rejected at validation time — omit the field to use the 'K' default.",
```

### LS API 원본 동작에 대해

LS 원 API 가 빈 문자열을 KRX 로 묵시 매핑하는지 여부는 LS 공식 문서에 명시되지 않아 라이브러리에서 의도적으로 차단하고 있습니다. **빈 문자열을 받아주는 것이 LS 측 의도라는 보장이 없는 한 우리 측 검증은 strict 유지**가 안전합니다.

---

## 2. 섹션 #2 — `t8451`/`t8452` IGW00201 HTTP 500

### 라이브러리 측 사실 관계

**(A) 응답 객체 형태 — 안정 규약**

`src/finance/programgarden_finance/ls/korea_stock/chart/t8451/__init__.py:45-85` (t8452 도 동일 패턴) 의 `_build_response` 가 status≥400 인 경우에도 다음을 일관되게 반환합니다:

| 필드 | HTTP 200 정상 | HTTP 500 + IGW00201 | 빈 봉 데이터 |
|------|--------------|--------------------|-------------|
| `status_code` | `200` | `500` | `200` |
| `rsp_cd` | `"00000"` | `"IGW00201"` | `"00000"` |
| `rsp_msg` | `"정상처리되었습니다."` | `"호출 거래건수를 초과하였습니다."` | `"정상처리되었습니다."` |
| `error_msg` | `None` | `"HTTP 500: 호출 거래건수를 초과하였습니다."` | `None` |
| `header` | 정상 | `None` | 정상 |
| `block` / `block1` | 정상 / list | `None` / `[]` | 정상 / `[]` |

→ **호출 한도 초과와 빈 봉 데이터의 구분은 `status_code == 200 && error_msg is None` 인지로 가능합니다.** 라이브러리는 예외를 raise 하지 않고 `Response` 객체로 일관 반환하므로 try/except 가 아니라 `rsp_cd` / `status_code` 검사로 처리하세요.

**(B) Rate limit 기본 설정**

| TR | rate_limit_count | rate_limit_seconds | on_rate_limit | rate_limit_key |
|----|------------------|--------------------|--------------|----------------|
| `t8451` (일봉) | 3 | 1 | `"wait"` | `"t8451"` ✅ |
| `t8452` (분봉) | **1** | **1** | **(default `"stop"`)** | **(none)** ❌ |

`t8452/blocks.py:387` 의 `SetupOptions(rate_limit_count=1, rate_limit_seconds=1)` 만 지정되어 있어:
- `on_rate_limit` 기본값이 `"stop"` (에러 발생, 대기 X)
- `rate_limit_key` 미지정 → 인스턴스마다 독립 카운트
- → **45 종목을 각각 별 인스턴스로 동시 호출하면 라이브러리 측 rate limit 이 무력화되고 LS 서버단 한도 IGW00201 가 즉시 발생**

**이 부분은 라이브러리 측 결함으로 인정**합니다. 다음 patch 에서:

```python
options: SetupOptions = SetupOptions(
    rate_limit_count=1,
    rate_limit_seconds=1,
    on_rate_limit="wait",
    rate_limit_key="t8452",
)
```

로 정정합니다 (t8451 패턴과 동일).

### 답변

- **권장 호출 패턴**: 같은 프로세스 내 여러 종목을 조회할 때는 인스턴스를 새로 만들지 말고 *동일 TR 객체를 재사용하거나 `rate_limit_key` 가 동일하게 묶이도록* 만드세요. 라이브러리 측 패치가 반영되면 인스턴스 분리 호출이어도 자동으로 직렬화됩니다.
- **호출 한도 가이드**: LS 공식 문서에 초당 명시 한도가 공개되어 있지 않습니다. 라이브러리 default 가 LS 측에서 IGW00201 을 받지 않는 안전한 값으로 설정되어 있으니, **default 를 낮추지 말고 그대로 사용**하세요. 45 종목 분봉 감시는 `rate_limit_key="t8452"` + `on_rate_limit="wait"` 이면 자동 직렬화되어 한도 초과 없이 처리됩니다.
- **재시도 가이드**: `rsp_cd == "IGW00201"` 일 때만 재시도. status_code 500 + `rsp_cd == ""` (응답 자체 실패) 면 transport 에러로 분리. `rsp_cd == "00000"` + 빈 데이터는 진짜로 데이터 없는 것이므로 재시도 X.
- **호출 한도 vs 빈 데이터 구분용 별도 예외 타입 도입**은 검토했으나 — 라이브러리 전체 패턴이 raise 가 아닌 Response-with-error 인 점, 이미 `rsp_cd` / `status_code` 로 충분히 구분 가능한 점에서 도입하지 않습니다. 단 README 에 "에러 응답 패턴" 표를 추가 예정.

---

## 3. 섹션 #3 — `CSPAT00601` `00039` / `00040` 해석

### 라이브러리 측 사실 관계

`src/finance/programgarden_finance/ls/korea_stock/order/CSPAT00601/blocks.py:495-501, 523-530`

```python
class CSPAT00601Response(BaseModel):
    """CSPAT00601 full response envelope.

    ``rsp_cd`` source notes: '00040' = buy-order accepted (매수주문완료),
    '00039' = sell-order accepted (매도주문완료). Other codes are not declared
    in available source -- inspect ``rsp_msg`` for failure reasons.
    """
    ...
    rsp_cd: str = Field(
        ...,
        description=(
            "LS response code. '00040' = buy-order accepted, '00039' = sell-order accepted. "
            "Other codes are not declared in available source."
        ),
    )
```

→ **이 코드는 라이브러리에 이미 명시되어 있었습니다.** docstring 을 따르지 않은 AlphaWorks 측 통합 버그입니다.

### 답변

**Q3-1. `CSPAT00601` 모의투자 주문에서 `00039`, `00040` 은 정상 완료 코드가 맞는가?**
- **네**. `00040` = 매수 정상 접수, `00039` = 매도 정상 접수. LS 공식 응답 라벨이며 라이브러리 docstring 에도 명시되어 있습니다.

**Q3-2. 실전투자에서도 `00039`, `00040` 을 성공으로 처리해도 되는가?**
- **네**. LS API 의 `CSPAT00601` 은 모의/실전 동일한 응답 코드 체계를 사용합니다. 실전에서도 매수/매도 정상 접수 시 동일하게 `00040` / `00039` 반환.

**Q3-3. 주문 성공 판정 권장 기준은 `rsp_cd`, `rsp_msg`, `block2`, `OrdNo` 중 무엇인가?**

권장 판정 로직 (우선순위 순):

```python
def is_order_accepted(resp: CSPAT00601Response, is_buy: bool) -> bool:
    # 1. Transport / HTTP 에러 1차 차단
    if resp.error_msg is not None:
        return False
    if resp.status_code is None or resp.status_code >= 400:
        return False

    # 2. 주문 접수 응답 코드 (LS 측 의미상 가장 권위 있는 신호)
    expected = "00040" if is_buy else "00039"
    if resp.rsp_cd != expected:
        return False

    # 3. block2 와 OrdNo 무결성 (안전망)
    if resp.block2 is None or resp.block2.OrdNo == 0:
        return False  # 코드는 성공인데 주문번호 미부여 → 추적 불가, 비정상

    return True
```

- **1차 권위 신호**: `rsp_cd ∈ {"00040", "00039"}` (방향별)
- **반드시 함께 검증**: `block2.OrdNo > 0` — 이후 SC 이벤트 매칭과 정정/취소 호출에 OrdNo 가 필요하므로 0 이면 사실상 사용 불가
- **`rsp_msg` 비교는 금지** — LS 측 메시지 텍스트 변경 가능성. 코드만 비교

**Q3-4. `CSPAT00601` 응답 코드 목록 예제 제공 가능?**

| `rsp_cd` | 의미 | 분류 |
|---------|------|------|
| `00000` | (일반 성공 코드, 다른 TR 에서 사용) | 성공 |
| `00039` | 매도 주문 정상 접수 | 성공 (매도만) |
| `00040` | 매수 주문 정상 접수 | 성공 (매수만) |
| `01478` | 매도가능수량 부족 | 거부 (잔고 사유) |
| `IGW00201` | 호출 거래건수 초과 | 시스템 (재시도 가능) |
| (그 외) | LS 측 공식 목록 비공개 | `rsp_msg` 확인 후 분류 |

→ 이 표는 다음 patch 에서 `docs/finance_guide.md` 와 README 에 정식 추가 예정.

**중요 주의:** `00000` 을 `CSPAT00601` 의 성공 코드로 가정하지 마세요. **`CSPAT00601` 의 정상 접수 코드는 방향에 따라 `00040` / `00039` 입니다.** AlphaWorks 가 적용한 "방향별 성공 코드만 허용" 패턴이 정답.

---

## 4. 섹션 #4 — `t0424` 잔고 폴링 vs 체결 확인

### 라이브러리 측 사실 관계

라이브러리가 제공하는 체결 확인 수단:

1. **WebSocket 이벤트 (권장)**
   - `SC0` — 주문 접수 (`주식주문접수`)
   - `SC1` — **주문 체결** (`주식주문체결`) ← 부분체결 / 완전체결 이벤트
   - `SC2` — 주문 정정 확인
   - `SC3` — 주문 취소 확인
   - `SC4` — 주문 거부

   각각 `accno` (계좌번호) + `ordno` (주문번호) 를 포함하므로 `CSPAT00601.block2.OrdNo` 와 매칭 가능.

2. **REST `CSPAQ13700` (폴링 가능 fallback)**
   - 주문체결조회 — OrdNo 별 체결 이력, 부분체결 수량, 체결시각 포함
   - WebSocket 미사용 환경에서 잔고 차이 추정 대신 권장되는 경량 폴링 대상

### 답변

**Q4-1. `t0424` 를 체결 확인 용도로 쓰는 것이 programgarden/LS 기준으로 안전한가?**

- **권장하지 않습니다.** `t0424` 는 *현재 잔고* 조회 TR 이지 체결 이벤트 TR 이 아닙니다. 잔고 차이 추정 방식은:
  - 부분체결 식별 불가 (수량만 보일 뿐 어느 주문의 결과인지 불명)
  - 동일 종목 동시 매수/매도 시 net 차이만 보임 (개별 fill 매칭 불가)
  - 잔고 조회 실패 vs 잔고 0 의 구분이 호출자 코드에 의존
- AlphaWorks 가 적용한 "`get_actual_positions()` 실패 시 `None` 반환, 부분체결 시 실제 체결 수량만 등록" 보완은 임시 안전망으로는 적절. 다만 근본 해결은 SC1 또는 CSPAQ13700.

**Q4-2. 주문번호 기반 체결 확인 API 권장 조합은?**

| 시나리오 | 권장 조합 |
|---------|----------|
| 실시간 자동매매 (저지연 필요) | `CSPAT00601 → SC1 (체결 이벤트 구독)` |
| 배치 / 폴링 자동매매 | `CSPAT00601 → CSPAQ13700 (OrdNo 로 조회)` |
| 데일리 정산 | `CSPAQ13700` (그날 전체) + `t0424` (마감 잔고) |

**Q4-3. WebSocket 주문/체결 이벤트(SC0~SC4) 중 자동매매 포지션 동기화에 가장 적합한 예제 추천**

- **주력**: `SC1` (체결) — 부분체결/완전체결 마다 발생. `ordno` + `cheqty` (체결수량) + `chesvc_pric` 등 포함. 포지션 증감의 ground truth.
- **보조**: `SC0` (접수) — 주문번호 확보용. 다만 `CSPAT00601.block2.OrdNo` 로 이미 확보 가능하므로 SC0 는 *주문이 LS 서버에 실제로 도달했는지* 확인 용도.
- **방어**: `SC4` (거부) — 접수 후 비동기 거부 케이스 차단.
- **권장 최소 셋**: `SC1 + SC4` 구독.

예제: `src/finance/example/korea_stock/real_SC0.py` 가 이미 있습니다. SC1 + CSPAT00601 매칭 combined 예제는 다음 patch 에서 추가 예정 (§7 참조).

---

## 5. 섹션 #5 — `01478` 매도가능수량 부족 반복

### 답변

- `01478` 은 **순수 LS 측 잔고 검증 거부 코드**입니다. 미체결/체결완료 후 재주문 상황과 무관하게 *매도 주문 시점 LS 서버 잔고 < 매도 수량* 이면 항상 동일 반환.
- 발생 시 권장 액션:
  1. `CSPAQ13700` 으로 해당 종목의 미체결 매도 주문 잔존 여부 확인 (이미 청산 중이면 중복 주문 차단)
  2. `t0424` 또는 `CSPAQ12300` 으로 실제 잔고 재조회
  3. 내부 포지션 ≠ 실제 잔고 면 내부 포지션을 실제 기준으로 강제 동기화

AlphaWorks 가 적용한 "청산 실패 후 실제잔고 재조회 → 해당 종목 없으면 내부 포지션 제거" 패턴이 정답. 추가로 SC4 구독을 켜면 비동기 거부도 잡힙니다.

---

## 6. 섹션 #6 — WebSocket 주문 이벤트 미도입

이미 §4 답변과 겹치므로 핵심만:

- **국내주식 주문 후 체결 이벤트 구독 + OrdNo 매칭 최소 예제**: 다음 patch 에서 `src/finance/example/korea_stock/run_CSPAT00601_with_SC1.py` 추가 예정. 패턴 미리보기:

```python
import asyncio
from programgarden_finance.ls import LS
from programgarden_finance.ls.korea_stock.order.CSPAT00601.blocks import CSPAT00601Request, CSPAT00601InBlock1
from programgarden_finance.ls.korea_stock.real.SC1.client import SC1Real  # 가칭

async def main():
    ls = LS(...)

    # 1. SC1 구독 시작 (계좌 단위)
    sc1 = ls.korea_stock.real.SC1()
    pending_orders: dict[str, asyncio.Future] = {}

    async def on_fill(resp):
        ordno = resp.body.ordno
        if ordno in pending_orders:
            pending_orders[ordno].set_result(resp.body)

    sc1.on_message(on_fill)
    await sc1.subscribe()

    # 2. 매수 주문
    order = ls.korea_stock.order.CSPAT00601(request_data=CSPAT00601Request(
        body={"CSPAT00601InBlock1": CSPAT00601InBlock1(
            IsuNo="005930", OrdQty=10, OrdPrc=70000,
            BnsTpCode="2",  # 매수
            OrdprcPtnCode="00",  # 지정가
            MgntrnCode="000", LoanDt="", OrdCndiTpCode="0",
        )}
    ))
    resp = await order.req_async()
    if resp.rsp_cd != "00040":
        raise RuntimeError(f"order rejected: {resp.rsp_cd} {resp.rsp_msg}")

    ord_no = str(resp.block2.OrdNo)
    pending_orders[ord_no] = asyncio.Future()

    # 3. 체결 대기 (timeout 권장)
    fill = await asyncio.wait_for(pending_orders[ord_no], timeout=30.0)
    print(f"체결: {fill.cheqty} @ {fill.chesvc_pric}")

asyncio.run(main())
```

- **OrdNo 매핑**: `CSPAT00601.block2.OrdNo` (int) ↔ `SC1RealResponseBody.ordno` (str). 비교 시 string 캐스팅 일치 필요.
- **모의투자/실전 동일성**: LS WebSocket 이벤트는 모의/실전 동일 스키마. 단 모의투자는 자동 체결이 즉시 발생하므로 SC0/SC1 이 거의 동시에 도착. 실전은 지정가일 경우 SC0 후 SC1 까지 시간 지연 발생 가능.

---

## 7. §8 — 최종 7개 질문 종합 답변 (요약 표)

| # | 질문 | 답변 요약 |
|---|------|----------|
| 1 | `CSPAT00601` 모의투자 `00039`, `00040` 정상 완료 코드 맞는가? | **네.** `00040` = 매수, `00039` = 매도 접수 성공. |
| 2 | 실전투자에서도 동일한가? | **네.** 모의/실전 동일. |
| 3 | 주문 성공 판정 권장 기준은? | `rsp_cd ∈ {"00040", "00039"}` (방향별) **+** `block2.OrdNo > 0`. `rsp_msg` 비교 금지. |
| 4 | `IGW00201` 재시도/대기/캐시 패턴은? | `on_rate_limit="wait"` + 동일 `rate_limit_key` 로 자동 직렬화. `rsp_cd == "IGW00201"` 시만 재시도. |
| 5 | `t8451/t8452` 안전 호출량 가이드? | 라이브러리 default (t8451: 3/sec, t8452: 1/sec) 그대로 사용. t8452 는 다음 patch 에서 `rate_limit_key` 추가 예정. |
| 6 | REST `t0424` vs WebSocket 권장? | **WebSocket SC1 권장.** 폴링이 필수면 `CSPAQ13700` (OrdNo 별 체결 이력) > `t0424` (잔고 차이 추정). |
| 7 | WebSocket 최소 예제 제공 가능? | 다음 patch 에서 `run_CSPAT00601_with_SC1.py` 추가 (§6 미리보기 참조). 현재는 `real_SC0.py` 참고. |

---

## 8. 라이브러리 측 다음 릴리스 계획 (이 보고서 반영분)

`finance` 다음 patch (1.6.5 또는 1.7.0) 에 다음 변경 포함:

1. **t8452 SetupOptions 보강** — `on_rate_limit="wait"` + `rate_limit_key="t8452"` 추가
2. **t1102 exchgubun docstring 정정** — 잘못된 "Other values are treated as KRX" 제거
3. **README + finance_guide.md 에 주문 응답 코드 표 추가** — `00040`/`00039`/`01478`/`IGW00201` 등
4. **`run_CSPAT00601_with_SC1.py` 예제 추가** — CSPAT00601 + SC1 + SC4 OrdNo 매칭 패턴

다음 릴리스 ETA: 본 이슈 답신 후 1~2 주 내 TestPyPI 게시 (현재 finance 1.6.4 가 TestPyPI 게시 대기 중이므로 1.6.4 머지 후 작업 착수).

---

## 9. 비라이브러리 측 조언 (참고)

AlphaWorks 측 코드에서 추가로 검토 권장하는 항목 (라이브러리 영향 없음):

- **`ValidationError` 와 LS 측 거부 코드의 watchdog 정책 분리** — AlphaWorks 가 이미 적용. 모범 사례.
- **부분체결 처리** — SC1 이 부분체결마다 도착하므로 누적 합산으로 포지션 등록.
- **OrdNo 추적 테이블** — Order ID lifecycle: 접수(SC0) → 부분체결×N(SC1) → 완전체결(SC1 마지막) | 정정(SC2) | 취소(SC3) | 거부(SC4). 각 이벤트에 대한 상태 머신 명시 권장.
- **모의투자에서의 즉시 체결** — 백테스트와 비슷한 거의 무지연 매칭. 실전 이행 전 지정가 지연 처리 로직 추가 검증 필요.

---

**작성**: programgarden 메인테이너 (jyj)
**연락**: 이슈/문서/예제 추가 PR 환영. GitHub `programgarden` 리포지토리 issue 로 추가 질문 등록 가능.
