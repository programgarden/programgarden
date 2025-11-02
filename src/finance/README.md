# Programgarden Finance

Programgarden Finance는 AI 시대에 맞춰 파이썬을 모르는 투자자도 개인화된 시스템 트레이딩을 자동으로 수행할 수 있게 돕는 오픈소스입니다. 본 라이브러리는 LS증권 OpenAPI를 간소화하여 해외 주식 및 해외 선물옵션 거래를 쉽게 자동화할 수 있도록 설계되었습니다.

비전공 투자자도 사용하기 쉽도록 설계되었으며, 동시성, 증권 데이터 업데이트 등의 백그라운드 작업은 Program Garden에서 관리하고 있으므로 투자자는 손쉽게 사용만 하면 됩니다.

- 문서(비개발자 빠른 시작): https://programgarden.gitbook.io/docs/invest/non_dev_quick_guide
- 문서(Finance 가이드): https://programgarden.gitbook.io/docs/develop/finance_guide
- 문서(개발자 구조 안내): https://programgarden.gitbook.io/docs/develop/structure
- 유튜브: https://www.youtube.com/@programgarden
- 실시간소통 오픈톡방: https://open.kakao.com/o/gKVObqUh

## 주요 특징

- **간편한 LS증권 API 통합**: LS증권 OpenAPI의 복잡한 스펙을 간소화하여 몇 줄의 코드로 시작 가능
- **해외 주식 & 선물옵션 지원**: 해외 주식 및 해외 선물옵션 시장의 실시간 데이터 조회, 주문, 잔고 관리 등 통합 지원
- **실시간 WebSocket 스트리밍**: 실시간 시세, 체결, 호가 데이터를 WebSocket으로 간편하게 구독 가능
- **비동기 처리**: 모든 API 요청은 비동기와 동기로 분리하여 처리해서 높은 성능과 동시성 제공
- **토큰 자동 관리**: OAuth 토큰 발급 및 갱신을 자동으로 처리하여 인증 관리 부담 최소화
- **타입 안전성**: Pydantic 기반의 타입 검증으로 IDE 친화적이고 안전한 코드 작성 지원
- **풍부한 예제**: `example/` 폴더에 해외 주식, 선물옵션 각 기능별 실행 가능한 예제 제공

## 설치

```bash
# PyPI에 게시된 경우
pip install programgarden-finance

# Poetry 사용 시 (개발 환경)
poetry add programgarden-finance
```

요구 사항: Python 3.9+

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
import os
from programgarden_finance import LS, g3101
from programgarden_core import pg_logger
from dotenv import load_dotenv

load_dotenv()

async def get_stock_price():
    ls = LS()
    
    # 로그인
    if not ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    ):
        pg_logger.error("로그인 실패")
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
    pg_logger.debug(f"TSLA 현재가: {response}")

asyncio.run(get_stock_price())
```

### 3. 실시간 시세 구독 (WebSocket)

```python
import asyncio
import os
from programgarden_finance import LS
from programgarden_core import pg_logger
from dotenv import load_dotenv

load_dotenv()

async def subscribe_realtime():
    ls = LS()
    
    if not ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    ):
        pg_logger.error("로그인 실패")
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
import os
from programgarden_finance import LS, o3101
from programgarden_core import pg_logger
from dotenv import load_dotenv

load_dotenv()

async def get_futures_master():
    ls = LS()
    
    if not ls.login(
        appkey=os.getenv("APPKEY_FUTURE"),
        appsecretkey=os.getenv("APPSECRET_FUTURE")
    ):
        pg_logger.error("로그인 실패")
        return
    
    # 해외선물 마스터 조회
    result = ls.overseas_futureoption().market().해외선물마스터조회(
        body=o3101.O3101InBlock(gubun="1")
    )
    
    response = await result.req_async()
    print(response)

asyncio.run(get_futures_master())
```

## 주요 모듈 구조

### LS 클래스
LS증권 API의 진입점이 되는 메인 클래스입니다.

```python
from programgarden_finance import LS

ls = LS()
ls.login(appkey="...", appsecretkey="...")

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

1. `.env` 파일 생성:
LS증권에서 API 키를 발급 받아서 `.env` 파일에 다음과 같이 설정합니다.
```bash
APPKEY=your_stock_appkey
APPSECRET=your_stock_appsecret
APPKEY_FUTURE=your_futures_appkey
APPSECRET_FUTURE=your_futures_appsecret
```

2. 예제 실행:
```bash
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
