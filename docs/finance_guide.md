# Programgarden Finance 라이브러리 가이드

## 1. 개요
Programgarden Finance 라이브러리는 LS 증권의 API를 활용하여 해외주식 및 해외선물 등의 금융 데이터를 조회하고 실시간으로 모니터링할 수 있는 Python 라이브러리입니다. 비전공 투자자도 쉽게 사용할 수 있도록 설계되었으며, 차트 데이터 조회, 실시간 데이터 구독 등의 기능을 제공합니다.

문서를 읽다가 헷갈리는 부분은 Issue 페이지 또는 커뮤니티를 통해서 언제든지 피드백주세요. 적극적으로 반영하겠습니다.

- 사용자 커뮤니티: https://cafe.naver.com/programgarden

<br>

## 2. 사용법

### 2.1. 간단 소개
Finance 라이브러리는 크게 3가지 주요 기능을 제공합니다:

- **로그인 및 인증**: LS 증권 API에 로그인하여 세션을 유지합니다.
- **차트 데이터 조회**: 해외주식의 과거 차트 데이터를 가져옵니다.
- **실시간 데이터 구독**: 실시간으로 주식, 주문 데이터를 받아옵니다.

---

### 2.2. 준비 단계

#### 계좌 개설 및 API 키 발급
거래 및 데이터 조회에 필요한 LS 증권 계좌를 개설하고, API 키를 발급받으세요.

> 현재 LS증권을 프로그램 동산 운영진이 메인 증권사로 직접 지원하고 있습니다. 다른 증권사는 추후 지원될 예정입니다.

투혼앱에서 글로벌 상품 거래가 가능한 계좌를 비대면으로 개설해 주세요. 방법을 모르시면 LS증권 고객센터(1588-2428)에 문의해 주세요.

자동화매매 키 발급: 투혼앱에서 API를 신청하고 Appkey와 Appsecretkey를 발급 받으세요. API 신청 위치는 아래와 같습니다.

**투혼앱 열기 -> 전체 메뉴 -> 투자정보 -> 투자 파트너 -> API 메뉴**

발급 받은 키는 절대 외부로 노출하지 마세요.

#### 설명전 예제파일 확인
예제 파일을 확인하여 사용법을 익히세요.
[예제폴더 이동](https://github.com/programgarden/programgarden/tree/main/src/finance/example)

#### 라이브러리 설치
터미널에서 아래 명령어를 실행하여 `programgarden_finance` 패키지를 설치합니다.
```bash
pip install programgarden_finance
```

또한, 필요한 의존성 패키지를 설치하세요:
```bash
pip install python-dotenv programgarden_core
```

---

### 2.3. 주요 기능 사용하기

#### 코딩전에 openAPI 요청 테스트하기
[LS증권 OpenAPI](https://openapi.ls-sec.co.kr/apiservice?group_id=ffd2def7-a118-40f7-a0ab-cd4c6a538a90&api_id=33bd887a-6652-4209-88cd-5324bc7c5e36) 서버에 요청을 보내 응답을 확인하는 간단한 테스트를 준비해두었습니다. Postman에서 테스트해보세요: [테스트하러 가기](https://www.postman.com/programgarden-team/programgarden/overview)



#### 로그인
LS 증권 API에 로그인하여 세션을 시작합니다. 싱글톤 패턴을 사용하여 인스턴스를 가져옵니다.

```python
from programgarden_finance import LS

ls = LS.get_instance()
login_result = await ls.async_login(
    appkey="your_appkey",
    appsecretkey="your_appsecretkey"
)

if login_result is False:
    print("로그인 실패")
    return
```

#### 차트 데이터 조회
해외주식의 차트 데이터를 조회합니다. 예를 들어, TSLA(테슬라)의 일별 차트 데이터를 가져옵니다.

```python
from programgarden_finance import g3204

chart_request = ls.overseas_stock().차트().차트일주월년별조회(
    g3204.G3204InBlock(
        sujung="Y",          # 수정주가 여부
        delaygb="R",         # 지연 구분
        keysymbol="82TSLA",  # 키 심볼
        exchcd="82",         # 거래소 코드 (나스닥)
        symbol="TSLA",       # 종목 코드
        gubun="2",           # 구분 (일별)
        qrycnt=500,          # 조회 건수
        comp_yn="N",         # 압축 여부
        sdate="20230203",    # 시작 날짜
        edate="20250505"     # 종료 날짜
    )
)

# 비동기로 요청
asyncio.create_task(chart_request.req_async())

# 전체 차트 데이터 응답 받는 것을 대기
await chart_request.occurs_req_async(
    callback=lambda response, status: print(f"응답: {response}, 상태: {status}")
)
```

#### 실시간 데이터 구독
실시간으로 해외주식 데이터를 구독합니다. 예를 들어, AS0 실시간 데이터를 받아옵니다.

```python
from programgarden_finance import AS0

def on_message(resp: AS0.AS0RealResponse):
    print(f"실시간 데이터: {resp}")

client = ls.overseas_stock().real()
await client.connect()

as0 = client.AS0()
as0.on_as0_message(on_message)
```

요청을 끊을 수도 있습니다.
```python
as0.on_remove_as0_message()
```

#### 요청 속도 제한
Finance 라이브러리는 API 요청의 속도를 제한하여 서버 과부하를 방지하고 안정적인 사용을 보장합니다. LS 증권 API의 제한 사항에 따라 초당 전송 횟수를 제어할 수 있습니다.

요청 속도 제한은 각 API의 blocks.py 파일에서 `SetupOptions`를 통해 설정됩니다. 예를 들어:

> 기본 값을 설정해둔 상태이기때문에 SetupOptions를 추가하지 않으셔도 됩니다.

- **rate_limit_count**: 지정된 시간 동안 허용되는 최대 요청 수 (예: 3개)
- **rate_limit_seconds**: 제한 시간 창 (예: 1초)
- **on_rate_limit**: 제한 초과 시 동작 방식
  - `"stop"`: 제한을 넘기면 요청을 중단하고 에러를 발생시킵니다.
  - `"wait"`: 제한이 풀릴 때까지 대기한 후 자동으로 재시도합니다.
- **rate_limit_key**: 여러 인스턴스 간에 rate limit 상태를 공유하기 위한 키 (기본값: None)

각 API의 blocks.py 파일에서 다음과 같이 설정되어 있습니다:

```python
options: SetupOptions = SetupOptions(
    rate_limit_count=3,      # 1초에 최대 3개 요청
    rate_limit_seconds=1,    # 1초 시간 창
    on_rate_limit="wait",    # 초과 시 대기
    rate_limit_key="g3102"   # 공유 키
)
```

이 기능을 사용하면 API 제한으로 인한 에러를 방지하고, 효율적으로 데이터를 조회할 수 있습니다.

---

### 2.4. 예제 코드

#### 차트 데이터 조회 예제
아래는 TSLA의 차트 데이터를 조회하는 완전한 예제입니다.

```python
import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, g3204
from programgarden_core import pg_logger, pg_log
import asyncio

load_dotenv()

async def test_chart_data():
    pg_log(logging.DEBUG)

    ls = LS.get_instance()
    login_result = await ls.async_login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    chart_request = ls.overseas_stock().차트().차트일주월년별조회(
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
            edate="20250505"
        )
    )

    asyncio.create_task(chart_request.req_async())

    await asyncio.sleep(1)
    await chart_request.occurs_req_async(
        callback=lambda response, status: pg_logger.debug(f"성공: {status}, 응답 길이: {len(response.block1) if response and hasattr(response, 'block1') else None}")
    )

if __name__ == "__main__":
    asyncio.run(test_chart_data())
```

#### 실시간 데이터 구독 예제
아래는 실시간 해외주식 데이터를 구독하는 예제입니다.

```python
import asyncio
import os
from programgarden_finance import LS, AS0
from programgarden_core import pg_logger
from dotenv import load_dotenv

load_dotenv()

async def run_real_time():
    ls = LS.get_instance()

    login_result = ls.login(
        appkey=os.getenv("APPKEY"),
        appsecretkey=os.getenv("APPSECRET")
    )

    if login_result is False:
        pg_logger.error("로그인 실패")
        return

    def on_message(resp: AS0.AS0RealResponse):
        print(f"받은 데이터: {resp}")

    client = ls.overseas_stock().real()
    await client.connect()

    as0 = client.AS0()
    as0.on_as0_message(on_message)

    # 무한 루프 등으로 유지
    await asyncio.sleep(3600)  # 1시간 동안 실행 예시

if __name__ == "__main__":
    asyncio.run(run_real_time())
```

이 가이드를 따라 Finance 라이브러리를 사용하여 LS 증권의 금융 데이터를 쉽게 조회하고 모니터링할 수 있습니다. 추가 질문이 있으면 커뮤니티나 Issue를 통해 문의해 주세요.
