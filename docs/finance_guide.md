# Programgarden Finance 사용 가이드

Programgarden Finance는 LS증권 OpenAPI를 Python 친화적으로 감싸 해외 주식과 해외 선물·옵션 거래를 손쉽게 자동화할 수 있게 돕는 라이브러리입니다. 이 문서는 라이브러리의 특징과 설치 방법부터 실전 활용 시나리오, TR 코드 참고, 실시간 스트리밍까지 한 번에 정리한 확장 설명서입니다. 문서를 읽다가 헷갈리는 부분은 이슈 페이지나 사용자 커뮤니티를 통해 언제든지 피드백 주세요.

- 사용자 커뮤니티: https://cafe.naver.com/programgarden
- 카카오톡 오픈채팅: https://open.kakao.com/o/gKVObqUh

---

## 주요 특징

- 간편한 LS증권 API 통합: 복잡한 LS증권 OpenAPI 스펙을 상황별 클래스로 추상화해 몇 줄의 코드로 호출 가능
- 해외 주식 & 선물옵션 지원: 시세, 주문, 잔고, 차트 등 주요 기능을 단일 인터페이스에서 처리
- 실시간 WebSocket 스트리밍: 실시간 체결, 호가, 시세를 Async WebSocket으로 구독
- 비동기·동기 동시 지원: 모든 API 요청에 대해 동기(`req`)와 비동기(`req_async`) 호출을 구분 제공
- 토큰 자동 관리: OAuth 토큰 발급 및 만료 시 자동 갱신을 라이브러리 내부에서 전담하여 사용자 관리 불필요
- 타입 안전성: Pydantic 기반 요청/응답 모델로 타입 힌트와 IDE 자동완성 강화
- 풍부한 예제: `src/finance/example/` 폴더에 TR별 실행 스크립트 포함

---

## 요구 사항 및 설치

- Python 3.9 이상
- LS증권 자동화매매 API 사용 권한 및 발급 받은 `appkey`, `appsecret`

```bash
# PyPI 배포본 사용
pip install programgarden-finance

# Poetry 기반 개발 환경
poetry add programgarden-finance
```

---

## 사전 준비

- **계좌 및 API 키 발급**: 투혼앱에서 글로벌 상품 거래 계좌를 비대면 개설 후 `전체 메뉴 → 투자정보 → 투자 파트너 → API` 메뉴에서 자동화매매용 Appkey/Appsecret을 발급받습니다. 분실 방지를 위해 키는 절대 외부에 노출하지 마세요.
- **Postman 사전 테스트**: OpenAPI 호출이 처음이라면 [Programgarden Postman Workspace](https://www.postman.com/programgarden-team/programgarden/overview)를 통해 REST 스펙과 응답 구조를 먼저 확인해 보세요.
- **환경 변수 구성**: 프로젝트 루트에 `.env` 파일을 만들고 다음과 같이 키를 저장합니다.

```bash
APPKEY=your_stock_appkey
APPSECRET=your_stock_appsecret
APPKEY_FUTURE=your_futures_appkey
APPSECRET_FUTURE=your_futures_appsecret
```

---

## 라이브러리 구조 한눈에 보기

```python
from programgarden_finance import LS

ls = LS()
ls.login(appkey="...", appsecretkey="...")

# 해외 주식 도메인
stock = ls.overseas_stock()
stock.market()    # 시장 정보
stock.chart()     # 차트 데이터
stock.accno()     # 계좌/잔고
stock.order()     # 주문
stock.real()      # 실시간 스트림

# 해외 선물·옵션 도메인
futures = ls.overseas_futureoption()
futures.market()
futures.chart()
futures.accno()
futures.order()
futures.real()
```

- **동기/비동기 세션**: `ls.login`은 동기, `await ls.async_login(...)`은 비동기 로그인입니다. 싱글톤 인스턴스가 필요하면 `LS.get_instance()`를 사용할 수 있습니다.
- **토큰 발급**: `programgarden_finance.ls.oauth.generate_token` 모듈은 OAuth 토큰 발급·갱신을 지원합니다.
- **로깅**: `programgarden_core.pg_logger`와 `pg_log`를 활용하면 디버깅 로그를 일관되게 출력할 수 있습니다.

---

## 빠른 시작 튜토리얼

### 1. OAuth 토큰 발급 (토큰만 필요한 경우)

```python
import asyncio
from programgarden_finance.ls.oauth.generate_token import GenerateToken
from programgarden_finance.ls.oauth.generate_token.token.blocks import TokenInBlock

async def get_token():
    response = GenerateToken().token(
        TokenInBlock(appkey="YOUR_APPKEY", appsecretkey="YOUR_APPSECRET"),
    )
    result = await response.req_async()
    print(f"Access Token: {result.block.access_token}")

asyncio.run(get_token())
```

토큰은 일정 시간이 지나면 만료되지만, 라이브러리 내부에서 요청 시 만료 여부를 확인하고 자동으로 갱신하므로 별도의 관리가 필요하지 않습니다.

### 2. 로그인 및 세션 준비 (로그인시 토큰 관리 자동으로 됨)

```python
import asyncio
import os
from dotenv import load_dotenv
from programgarden_finance import LS
from programgarden_core import pg_logger

load_dotenv()

async def ensure_login():
    ls = LS.get_instance()
    success = await ls.async_login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET"),
    )
    if not success:
        pg_logger.error("로그인 실패")
        return None
    return ls

ls = asyncio.run(ensure_login())
```

### 3. 해외 주식 현재가 조회 (동기/비동기 모두 지원)

```python
import asyncio
import os
from dotenv import load_dotenv
from programgarden_finance import LS, g3101
from programgarden_core import pg_logger

load_dotenv()

async def get_stock_price():
    ls = LS()
    if not ls.login(appkey=os.getenv("APPKEY"), appsecretkey=os.getenv("APPSECRET")):
        pg_logger.error("로그인 실패")
        return

    response = ls.overseas_stock().market().현재가조회(
        g3101.G3101InBlock(
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA",
        )
    )
    result = await response.req_async()
    pg_logger.debug(f"TSLA 현재가: {result}")

asyncio.run(get_stock_price())
```

### 4. 실시간 시세(WebSocket) 구독

```python
import asyncio
import os
from dotenv import load_dotenv
from programgarden_finance import LS
from programgarden_core import pg_logger

load_dotenv()

async def subscribe_realtime():
    ls = LS()
    if not ls.login(appkey=os.getenv("APPKEY"), appsecretkey=os.getenv("APPSECRET")):
        pg_logger.error("로그인 실패")
        return

    def on_message(resp):
        print(f"실시간 데이터: {resp}")

    client = ls.overseas_stock().real()
    await client.connect()

    gsc = client.GSC()
    gsc.add_gsc_symbols(symbols=["81SOXL", "82TSLA"])
    gsc.on_gsc_message(on_message)

asyncio.run(subscribe_realtime())
```

구독 해지 시에는 `gsc.on_remove_gsc_message()` 또는 연결 종료 로직을 호출합니다. 대량 구독 시에는 연결 유지용 `asyncio.create_task`와 종료 신호를 조합해 관리하세요.

### 5. 해외 선물·옵션 마스터 조회

```python
import asyncio
import os
from dotenv import load_dotenv
from programgarden_finance import LS, o3101
from programgarden_core import pg_logger

load_dotenv()

async def get_futures_master():
    ls = LS()
    if not ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE"),
    ):
        pg_logger.error("로그인 실패")
        return

    result = ls.overseas_futureoption().market().해외선물마스터조회(
        body=o3101.O3101InBlock(gubun="1"),
    )
    response = await result.req_async()
    print(response)

asyncio.run(get_futures_master())
```

---

## 활용 예시

### 차트 데이터 수집

```python
import asyncio
import logging
import os
from dotenv import load_dotenv
from programgarden_finance import LS, g3204
from programgarden_core import pg_logger, pg_log

load_dotenv()

async def fetch_tsla_chart():
    pg_log(logging.DEBUG)
    ls = LS.get_instance()
    if not await ls.async_login(os.getenv("APPKEY"), os.getenv("APPSECRET")):
        pg_logger.error("로그인 실패")
        return

    chart = ls.overseas_stock().차트().차트일주월년별조회(
        g3204.G3204InBlock(
            sujung="Y",
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA",
            gubun="2",
            qrycnt=500,
            comp_yn="N",
            sdate="20230203",
            edate="20250505",
        )
    )

    asyncio.create_task(chart.req_async())
    await chart.occurs_req_async(
        callback=lambda resp, status: pg_logger.debug(
            f"응답 상태: {status}, 건수: {len(resp.block1) if resp and hasattr(resp, 'block1') else 0}",
        ),
    )

asyncio.run(fetch_tsla_chart())
```

### 실시간 데이터 유지

```python
import asyncio
import os
from dotenv import load_dotenv
from programgarden_finance import LS, AS0
from programgarden_core import pg_logger

load_dotenv()

async def stream_real_time():
    ls = LS.get_instance()
    if not ls.login(os.getenv("APPKEY"), os.getenv("APPSECRET")):
        pg_logger.error("로그인 실패")
        return

    def on_message(resp: AS0.AS0RealResponse):
        print(f"받은 데이터: {resp}")

    client = ls.overseas_stock().real()
    await client.connect()

    as0 = client.AS0()
    as0.on_as0_message(on_message)
    try:
        await asyncio.sleep(3600)
    finally:
        as0.on_remove_as0_message()
        await client.close()

asyncio.run(stream_real_time())
```

---

### 요청 속도 직접 조절(Rate Limiting)

각 데이터 요청에는 `SetupOptions`가 정의돼 있어 초당 전송 횟수 제한을 자동으로 준수합니다. 필요 시 인스턴스를 직접 생성해 옵션을 요청시 Header의 options에 추가하여 변경할 수 있습니다.

```python
from programgarden_finance.ls.tr_base import SetupOptions

options = SetupOptions(
    rate_limit_count=3,
    rate_limit_seconds=1,
    on_rate_limit="wait",
    rate_limit_key="g3102",
)
```

- `on_rate_limit="stop"`으로 설정하면 제한 초과 시 즉시 예외가 발생합니다.
- 여러 프로세스에서 같은 TR을 호출할 때 `rate_limit_key`를 공유하면 Redis 등 외부 저장소로 속도 제한 상태를 공유할 수 있습니다.

---

## TR 코드 참조

### 해외 주식
- 시장 정보: `g3101`(현재가), `g3102`(해외지수), `g3104`(거래소마스터), `g3106`(환율), `g3190`(뉴스)
- 차트: `g3103`(일별), `g3202`(분봉), `g3203`(틱봉), `g3204`(시간외)
- 계좌: `COSAQ00102`(예수금), `COSAQ01400`(해외잔고), `COSOQ00201`(체결내역), `COSOQ02701`(미체결)
- 주문: `COSAT00301`(정정), `COSAT00311`(신규), `COSMT00300`(취소), `COSAT00400`(예약)
- 실시간: `GSC`(체결), `GSH`(호가), `AS0`~`AS4`(각종 실시간 시세)

### 해외 선물·옵션
- 시장 정보: `o3101`(선물마스터), `o3104`~`o3107`(거래소/통화/가격단위/정산환율), `o3116`(옵션마스터), `o3121`~`o3128`, `o3136`, `o3137`
- 차트: `o3103`(일별), `o3108`(분봉), `o3117`(틱봉), `o3139`(시간외)
- 계좌: `CIDBQ01400`(예수금), `CIDBQ01500`(잔고), `CIDBQ01800`(체결), `CIDBQ02400`(미체결), `CIDBQ03000`(일별손익), `CIDBQ05300`(청산가능수량), `CIDEQ00800`(예탁증거금)
- 주문: `CIDBT00100`(신규), `CIDBT00900`(정정), `CIDBT01000`(취소)
- 실시간: `OVC`(체결), `OVH`(호가), `TC1`~`TC3`, `WOC`, `WOH`

패키지 루트에서는 주요 심볼을 재노출해 손쉽게 가져올 수 있습니다.

```python
from programgarden_finance import (
    LS,
    oauth,
    TokenManager,
    overseas_stock,
    overseas_futureoption,
    g3101, g3102, g3103, g3104, g3106, g3190,
    g3202, g3203, g3204,
    COSAQ00102, COSAQ01400, COSOQ00201, COSOQ02701,
    COSAT00301, COSAT00311, COSMT00300, COSAT00400,
    GSC, GSH, AS0, AS1, AS2, AS3, AS4,
    o3101, o3104, o3105, o3106, o3107,
    o3116, o3121, o3123, o3125, o3126,
    o3127, o3128, o3136, o3137,
    o3103, o3108, o3117, o3139,
    CIDBQ01400, CIDBQ01500, CIDBQ01800, CIDBQ02400,
    CIDBQ03000, CIDBQ05300, CIDEQ00800,
    CIDBT00100, CIDBT00900, CIDBT01000,
    OVC, OVH, TC1, TC2, TC3, WOC, WOH,
    exceptions,
)
```

---

## 예제 실행 안내

```text
src/finance/example/
├── token/                      # OAuth 토큰 발급 예제
│   └── run_token.py
├── overseas_stock/             # 해외 주식 예제
│   ├── run_g3101.py            # 현재가 조회
│   ├── run_g3102.py            # 해외지수 조회
│   ├── run_COSAT00311.py       # 신규주문
│   ├── real_GSC.py             # 실시간 체결
│   └── real_GSH.py             # 실시간 호가
└── overseas_futureoption/      # 해외 선물·옵션 예제
    ├── run_o3101.py            # 선물마스터
    ├── run_CIDBT00100.py       # 신규주문
    ├── real_OVC.py             # 실시간 체결
    └── real_OVH.py             # 실시간 호가
```

```bash
# .env 구성 후 예제 실행
python src/finance/example/token/run_token.py
python src/finance/example/overseas_stock/run_g3101.py
python src/finance/example/overseas_futureoption/run_o3101.py
python src/finance/example/overseas_stock/real_GSC.py
```

실행 전 `pg_log(logging.DEBUG)`로 로그 레벨을 조정하면 요청과 응답을 쉽게 추적할 수 있습니다.

---

## 추가 팁

- **문제 해결**: 인증 오류는 토큰 만료, 허용 IP 미등록, 키 불일치가 대부분입니다. 로그를 확인하고 Postman으로 동일 요청을 재현해 보세요.
- **테스트 전략**: 실계좌 호출 전 모의계좌 API로 로직을 검증하고, WebSocket은 연결 유지와 재접속 시나리오로 충분하게 테스트하세요.
- **커뮤니티 제안**: 신규 TR 추가나 기능 개선 아이디어는 커뮤니티 게시판이나 GitHub Issue로 공유해 주세요.

이 문서를 바탕으로 Programgarden Finance 라이브러리를 활용해 LS증권 해외 상품 자동화를 안정적으로 구축할 수 있습니다.
