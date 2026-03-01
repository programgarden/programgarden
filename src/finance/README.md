# Programgarden Finance

Programgarden Finance는 AI 시대에 맞춰 파이썬을 모르는 투자자도 개인화된 시스템 트레이딩을 자동으로 수행할 수 있게 돕는 오픈소스입니다. 본 라이브러리는 LS증권 OpenAPI를 간소화하여 국내 주식, 해외 주식, 해외 선물옵션 거래를 쉽게 자동화할 수 있도록 설계되었습니다.

비전공 투자자도 사용하기 쉽도록 설계되었으며, 동시성, 증권 데이터 업데이트 등의 백그라운드 작업은 Program Garden에서 관리하고 있으므로 투자자는 손쉽게 사용만 하면 됩니다.

- 문서(비개발자 빠른 시작): https://programgarden.gitbook.io/docs/invest/non_dev_quick_guide
- 문서(Finance 가이드): https://programgarden.gitbook.io/docs/develop/finance_guide
- 문서(개발자 구조 안내): https://programgarden.gitbook.io/docs/develop/structure
- 유튜브: https://www.youtube.com/@programgarden
- 실시간소통 오픈톡방: https://open.kakao.com/o/gKVObqUh

## 주요 특징

- **간편한 LS증권 API 통합**: LS증권 OpenAPI의 복잡한 스펙을 간소화하여 몇 줄의 코드로 시작 가능
- **국내 주식 · 해외 주식 · 선물옵션 지원**: 국내 주식(69 TR), 해외 주식, 해외 선물옵션 시장의 실시간 데이터 조회, 주문, 잔고 관리 등 통합 지원
- **실시간 WebSocket 스트리밍**: 실시간 시세, 체결, 호가 데이터를 WebSocket으로 간편하게 구독 가능
- **비동기 처리**: 모든 API 요청은 비동기와 동기로 분리하여 처리해서 높은 성능과 동시성 제공
- **토큰 자동 관리**: OAuth 토큰 발급 및 갱신을 자동으로 처리하여 인증 관리 부담 최소화
- **타입 안전성**: Pydantic 기반의 타입 검증으로 IDE 친화적이고 안전한 코드 작성 지원
- **풍부한 예제**: `example/` 폴더에 국내 주식, 해외 주식, 선물옵션 각 기능별 실행 가능한 예제 제공

## 설치

```bash
# PyPI에 게시된 경우
pip install programgarden-finance

# Poetry 사용 시 (개발 환경)
poetry add programgarden-finance
```

요구 사항: Python 3.12+

## 빠른 시작

### 1. 토큰 발급

LS증권 API를 사용하려면 먼저 OAuth 토큰을 발급받아야 합니다.

```python
import asyncio
from programgarden_finance import LS
from programgarden_finance.ls.oauth.generate_token import GenerateToken
from programgarden_finance.ls.oauth.generate_token.token.blocks import TokenInBlock

async def get_token():
    response = GenerateToken().token(
        TokenInBlock(
            appkey="YOUR_APPKEY",
            appsecretkey="YOUR_APPSECRET",
        )
    )
    result = await response.req_async()
    print(f"Access Token: {result.block.access_token}")

asyncio.run(get_token())
```

### 2. 해외 주식 현재가 조회

```python
import asyncio
from programgarden_finance import LS, g3101

async def get_stock_price():
    ls = LS()

    # 로그인 (발급받은 App Key / App Secret 입력)
    if not ls.login(
        appkey="발급받은 App Key",
        appsecretkey="발급받은 App Secret"
    ):
        print("로그인 실패")
        return

    # TSLA 현재가 조회
    result = ls.overseas_stock().market().현재가조회(
        g3101.G3101InBlock(
            delaygb="R",
            keysymbol="82TSLA",
            exchcd="82",
            symbol="TSLA"
        )
    )

    response = await result.req_async()
    print(f"TSLA 현재가: {response}")

asyncio.run(get_stock_price())
```

### 3. 실시간 시세 구독 (WebSocket)

```python
import asyncio
from programgarden_finance import LS

async def subscribe_realtime():
    ls = LS()

    if not ls.login(
        appkey="발급받은 App Key",
        appsecretkey="발급받은 App Secret"
    ):
        print("로그인 실패")
        return

    # 실시간 데이터 콜백
    def on_message(resp):
        print(f"실시간 데이터: {resp}")

    # WebSocket 연결
    client = ls.overseas_stock().real()
    await client.connect()

    # GSC(해외주식 실시간 시세) 구독
    gsc = client.GSC()
    gsc.add_gsc_symbols(symbols=["81SOXL", "82TSLA"])
    gsc.on_gsc_message(on_message)

asyncio.run(subscribe_realtime())
```

### 4. 해외 선물옵션 마스터 조회

```python
import asyncio
from programgarden_finance import LS, o3101

async def get_futures_master():
    ls = LS()

    if not ls.login(
        appkey="발급받은 App Key (선물용)",
        appsecretkey="발급받은 App Secret (선물용)"
    ):
        print("로그인 실패")
        return

    # 해외선물 마스터 조회
    result = ls.overseas_futureoption().market().해외선물마스터조회(
        body=o3101.O3101InBlock(gubun="1")
    )

    response = await result.req_async()
    print(response)

asyncio.run(get_futures_master())
```

### 5. 국내 주식 현재가 조회

```python
import asyncio
from programgarden_finance import LS, t1102

async def get_korea_stock_price():
    ls = LS()

    if not ls.login(
        appkey="발급받은 App Key",
        appsecretkey="발급받은 App Secret"
    ):
        print("로그인 실패")
        return

    # 삼성전자 현재가 조회
    result = ls.korea_stock().market().주식현재가(
        t1102.T1102InBlock(shcode="005930")
    )

    response = await result.req_async()
    print(f"삼성전자 현재가: {response}")

asyncio.run(get_korea_stock_price())
```

## 주요 모듈 구조

### LS 클래스
LS증권 API의 진입점이 되는 메인 클래스입니다.

```python
from programgarden_finance import LS

ls = LS()
ls.login(appkey="...", appsecretkey="...")

# 국내 주식 API
korea = ls.korea_stock()
korea.market()    # 시장 정보 조회
korea.chart()     # 차트 데이터 조회
korea.accno()     # 계좌 정보 조회
korea.order()     # 주문 처리
korea.real()      # 실시간 데이터

# 해외 주식 API
stock = ls.overseas_stock()
stock.market()    # 시장 정보 조회
stock.chart()     # 차트 데이터 조회
stock.accno()     # 계좌 정보 조회
stock.order()     # 주문 처리
stock.real()      # 실시간 데이터

# 해외 선물옵션 API
futures = ls.overseas_futureoption()
futures.market()  # 시장 정보 조회
futures.chart()   # 차트 데이터 조회
futures.accno()   # 계좌 정보 조회
futures.order()   # 주문 처리
futures.real()    # 실시간 데이터
```

### 제공되는 주요 TR 코드

#### 국내 주식 (69 TR)
- **시장 정보**: `t9945`(마스터), `t8450`(호가), `t1101`(호가), `t1102`(현재가), `t1301`(체결), `t1471`(시간별체결), `t1475`(체결), `t8407`(복수종목시세), `t8454`(멀티현재가), `t1404`/`t1405`(프로그램매매), `t1422`/`t1442`(관리/이상종목)
- **계좌**: `CSPAQ22200`(예수금), `CSPAQ12200`(잔고), `CSPAQ12300`(잔고상세), `CSPAQ13700`(미체결), `CDPCQ04700`(투자가능금액), `FOCCQ33600`(증거금), `CSPAQ00600`(체결내역), `CSPBQ00200`(평가손익), `t0424`(잔고2), `t0425`(종목별잔고)
- **주문**: `CSPAT00601`(현물주문), `CSPAT00701`(정정), `CSPAT00801`(취소)
- **랭킹**: `t1441`(등락률), `t1444`(시가총액), `t1452`(거래량), `t1463`(거래대금), `t1466`(전일동시간비), `t1481`(급등락), `t1482`(신고/신저)
- **차트**: `t8451`(일주월년봉), `t8452`(분봉), `t8453`(틱봉), `t1665`(종합차트)
- **업종/테마**: `t1511`(업종현재가), `t1516`(업종종목), `t1531`(테마종목), `t1532`(테마그룹), `t1537`(테마별종목)
- **투자자**: `t1601`~`t1621`(투자자매매동향), `t1664`(투자자매매추이), `t1702`(외인/기관)
- **ETF**: `t1901`(ETF시세), `t1903`(구성종목), `t1904`(ETF일별)
- **기타**: `t1403`(신규상장), `t1638`(신용거래), `t1927`(공매도), `t1941`(종목별프로그램)
- **실시간**: `S3_`(체결), `K3_`(KOSDAQ체결), `H1_`(호가), `HA_`(KOSDAQ호가), `NH1`(NXT호가), `IJ_`(업종지수), `DVI`/`NVI`(VI발동해제), `SC0`~`SC4`(주문접수/체결/정정/취소/거부)

#### 해외 주식
- **시장 정보**: `g3101`(현재가), `g3102`(해외지수), `g3104`(거래소마스터), `g3106`(환율), `g3190`(뉴스)
- **차트**: `g3103`(일별), `g3202`(분봉), `g3203`(틱봉), `g3204`(시간외)
- **계좌**: `COSAQ00102`(예수금), `COSAQ01400`(해외잔고), `COSOQ00201`(체결내역), `COSOQ02701`(미체결)
- **주문**: `COSAT00301`(정정주문), `COSAT00311`(신규주문), `COSMT00300`(취소주문), `COSAT00400`(예약주문)
- **실시간**: `GSC`(체결), `GSH`(호가), `AS0`~`AS4`(각종 실시간 시세)

#### 해외 선물옵션
- **시장 정보**: `o3101`(선물마스터), `o3104`~`o3107`(거래소/통화/가격단위/정산환율), `o3116`(옵션마스터), `o3121`~`o3128`(각종 시장 정보), `o3136`, `o3137`(추가 시장 정보)
- **차트**: `o3103`(일별), `o3108`(분봉), `o3117`(틱봉), `o3139`(시간외)
- **계좌**: `CIDBQ01400`(예수금), `CIDBQ01500`(잔고), `CIDBQ01800`(체결내역), `CIDBQ02400`(미체결), `CIDBQ03000`(일별손익), `CIDBQ05300`(청산가능수량), `CIDEQ00800`(예탁증거금)
- **주문**: `CIDBT00100`(신규), `CIDBT00900`(정정), `CIDBT01000`(취소)
- **실시간**: `OVC`(체결), `OVH`(호가), `TC1`~`TC3`, `WOC`, `WOH`(각종 실시간 데이터)

## 예제 코드

`example/` 폴더에 다양한 실행 가능한 예제가 포함되어 있습니다.

### 예제 폴더 구조

```
example/
├── token/                      # OAuth 토큰 발급 예제
│   └── run_token.py
├── korea_stock/                # 국내 주식 예제
│   ├── run_t1102.py           # 현재가 조회
│   ├── run_CSPAT00601.py      # 현물 주문
│   ├── run_CSPAQ12200.py      # 잔고 조회
│   ├── real_S3_.py            # 실시간 체결 (KOSPI)
│   ├── real_SC1.py            # 실시간 주문 체결
│   ├── run_account_tracker.py # 계좌 추적 통합
│   └── ...                    # 총 74개 예제
├── overseas_stock/             # 해외 주식 예제
│   ├── run_g3101.py           # 현재가 조회
│   ├── run_g3102.py           # 해외지수 조회
│   ├── run_COSAT00311.py      # 신규주문
│   ├── real_GSC.py            # 실시간 체결 구독
│   ├── real_GSH.py            # 실시간 호가 구독
│   └── ...
└── overseas_futureoption/      # 해외 선물옵션 예제
    ├── run_o3101.py           # 선물마스터 조회
    ├── run_CIDBT00100.py      # 신규주문
    ├── real_OVC.py            # 실시간 체결 구독
    ├── real_OVH.py            # 실시간 호가 구독
    └── ...
```

### 예제 실행 방법

1. LS증권에서 API 키(App Key, App Secret)를 발급받습니다.
2. 각 예제 파일의 `appkey`, `appsecretkey` 부분에 발급받은 키를 입력합니다.
3. 예제를 실행합니다:

```bash
# 국내 주식 현재가 조회
python example/korea_stock/run_t1102.py

# 해외 주식 현재가 조회
python example/overseas_stock/run_g3101.py

# 해외 선물 마스터 조회
python example/overseas_futureoption/run_o3101.py

# 실시간 시세 구독
python example/overseas_stock/real_GSC.py
```

## API 참조

패키지 루트에서 주요 심볼들을 재노출합니다:

```python
from programgarden_finance import (
    # 메인 클래스
    LS,

    # 모듈
    oauth,
    TokenManager,
    overseas_stock,
    overseas_futureoption,
    korea_stock,

    # 국내 주식 TR
    t9945, t8450, t1101, t1102, t1301,         # 시장 정보
    t1471, t1475, t8407, t8454,                 # 시장 정보
    t1403, t1404, t1405, t1422, t1442,         # 시장 정보
    CSPAQ22200, CSPAQ12200, CSPAQ12300,        # 계좌
    CSPAQ13700, CDPCQ04700, FOCCQ33600,        # 계좌
    CSPAQ00600, CSPBQ00200, t0424, t0425,      # 계좌
    CSPAT00601, CSPAT00701, CSPAT00801,        # 주문
    t1441, t1444, t1452, t1463, t1466,         # 랭킹
    t1481, t1482,                               # 랭킹
    t8451, t8452, t8453, t1665,                 # 차트
    t1511, t1516, t1531, t1532, t1537,         # 업종/테마
    t1601, t1602, t1603, t1617, t1621, t1664,  # 투자자
    t1702,                                      # 외인/기관
    t1901, t1903, t1904,                        # ETF
    t1638, t1927, t1941,                        # 기타
    S3_, K3_, H1_, HA_, NH1, IJ_,              # 실시간 시세
    DVI, NVI,                                   # 실시간 VI
    SC0, SC1, SC2, SC3, SC4,                   # 실시간 주문

    # 해외 주식 TR
    g3101, g3102, g3103, g3104, g3106, g3190,  # 시장/차트
    g3202, g3203, g3204,                        # 차트
    COSAQ00102, COSAQ01400,                     # 계좌 조회
    COSOQ00201, COSOQ02701,                     # 체결/미체결
    COSAT00301, COSAT00311,                     # 주문
    COSMT00300, COSAT00400,                     # 취소/예약
    GSC, GSH, AS0, AS1, AS2, AS3, AS4,         # 실시간

    # 해외 선물옵션 TR
    o3101, o3104, o3105, o3106, o3107,         # 시장 정보
    o3116, o3121, o3123, o3125, o3126,         # 시장 정보
    o3127, o3128, o3136, o3137,                # 시장 정보
    o3103, o3108, o3117, o3139,                # 차트
    CIDBQ01400, CIDBQ01500, CIDBQ01800,        # 계좌
    CIDBQ02400, CIDBQ03000, CIDBQ05300,        # 계좌
    CIDEQ00800,                                 # 계좌
    CIDBT00100, CIDBT00900, CIDBT01000,        # 주문
    OVC, OVH, TC1, TC2, TC3, WOC, WOH,         # 실시간

    # 예외 처리
    exceptions,
)
```
