# 자동화매매 빠르게 사용하기

## 1. 개요

아래는 비전공 투자자도 이해하기 쉽게 정리한 구성 가이드입니다. 각 항목이 어떤 의미인지, 투자자가 직접 설정할 때 필요한 부분들을 설명합니다.

문서를 읽다가 헷갈리는 부분은 Issue 페이지 또는 뮤니티를 통해서 언제든지 피드백주세요. 적극적으로 반영하겠습니다.

* 사용자 커뮤니티: https://cafe.naver.com/programgarden

\


## 2. 사용법

### 2.1. 간단 소개

자동으로 시장을 분석하고 조건이 맞으면 매수/매도 주문을 내도록 만든 특정 목적의 언어를 의미하는 `DSL(Domain Specific Language)`입니다. 크게 4부분으로 나뉩니다.

* **시스템 정보**: 이름·버전 등 메타정보
* **증권/인증 정보**: API 키 등
* **전략(Strategies)**: 종목 전략 분석
* **주문(Orders)**: 전략 계산 후 주문 정보

***

### 2.2. 준비 단계

### 계좌 개설

거래에 필요한 계좌를 개설해 주세요.

> 현재 LS증권을 메인 증권사로 지원하고 있습니다. 다른 증권사는 추후 지원될 예정입니다.

투혼앱에서 글로벌 상품 거래가 가능한 계좌를 비대면으로 개설해 주세요. 방법을 모르시면 LS증권 고객센터(1588-2428)에 문의해 주세요.

### 자동화매매 키 발급

투혼앱에서 API를 신청하고 매매에 필요한 Appkey와 Appsecretkey를 발급 받으세요. API 신청 위치는 아래와 같습니다.

**투혼앱 열기 -> 전체 메뉴 -> 투자정보 -> 투자 파트너 -> API 메뉴**

발급 받은 후 자동매매 세팅에 들어가세요.

***

### 2.3. 자동매매 각 항목 세팅하기

ProgramGarden 자동매매는 4가지 항목을 가집니다.

* **settings**: 전략의 이름·설명·디버그 모드 등
* **securities**: API 연동 정보(서비스 제공자, - product, appkey 등)
* **strategies**: 어떤 종목을 언제 어떻게 분석할지 정의합니다.
* **orders**: 분석 결과를 실제 주문으로 전환할 규칙들 입니다.

```python
{
    "settings": {
        ...
    },
    "securities": {
        ...
    },
    "strategies": {
        ...
    },
    "orders": {
        ...
    }
}
```

영역별로 자세히 알아보겠습니다.

### settings 영역

만들려는 자동화매매 정보를 작성합니다.

```python
{
    "settings": {
        # 자동화매매 시스템 ID (중복 금지)
        "system_id": "my_trading_system_001",

        # 자동매매 제목
        "name": "추세 자동매매",
        
        # 자동매매 설명
        "description": "장기 우상향 추세추종 자동화 매매",
        
        # 자동매매 버전
        "version": "1.0.0",
        
        # 내이름
        "author": "홍길동",
        
        # 만든 날짜
        "date": "2025-09-21",
    },
}
```

### securities 영역

자동화매매 거래에 사용할 증권사 정보를 입력하세요. 지금은 LS증권만 지원하고 있습니다.

```python
{
    "securities": {
        #증권사 상호명
        "company": "ls",
        
        # 상품명
        "product": "overseas_stock",
        
        # 발급 받은 appkey 입력
        "appkey": "wkIEUFenwkOE923iEKE..."
        
        # 발급 받은 appsecretkey 입력
        "appsecretkey": "EIfie9wi3kr3rkE..."
    }
}
```

#### 상세설명

* **product**
  * `overseas_stock`(해외주식), `overseas_future`(해외선물)만 지원 중이고 다른 상품들도 지원 예정입니다.

### strategies 영역

종목을 분석하는 전략과 매매 방법을 작성합니다.

```python
{
    strategies: [
        {
            # 전략 식별자 (중복 금지)
            "id": "trending_trade",
            
            # 전략 설명
            "description": "장기 이평선 계산 후 매수합니다.",
            
            # 전략 계산을 특정 시기마다 동작시키는 스케줄
            "schedule": "0 */15 * * * *",
            
            # 스케줄 기준 시간대를 작성 
            "timezone": "Asia/Seoul",
            
            # 만족해야하는 조건 방법
            "logic": "at_least", 
            
            # 조건의 임계값
            "threashold": 1,
            
            # 분석할 종목 목록(비어있으면 전체 종목 대상)
            "symbols": [ 
                { "symbol": "TSLA", "exchcd": "82" },
                { "symbol": "NVDA", "exchcd": "82" }
            ],
            
            # 분석에 사용하려는 최대 종목 갯수
            "max_symbols": {
                # 종목 선정 방식
                "order": "mcap",
                # 최대 5개 선택
                "limit": 5
            },

            # 주문 방법: 전략 계산 완료 후에 orders 영역의 주문 전략 id를 기입
            "order_id": "분할매수_1",

            # 실제 분석 조건 리스트(여러 개를 둘 수 있음)
            "conditions": [
                {
                    # 조건 ID
                    "condition_id": "SMAGoldenDeadCross",
                    # SMAGoldenDeadCross에서 요구하는 데이터 값 작성
                    "params": {
                    }
                }
            ]
        }
    ]
}
```

#### 상세 설명

* **schedule**
  * 스케줄러 작성 가이드 보기: [자동화매매 스케줄 가이드](../docs/schedule_guide.md)
* **timezone**
  * 스케줄 기준 시간대로 한국 실행은 `Asia/Seoul`로 설정합니다.
  * 다른 나라 지역 시간 확인: [다른 나라 지역 확인](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
* **logic**
  * 조건들의 계산 결과로 전략의 트리거(주문 실행) 여부가 결정됩니다. 이를 위해 logic을 설정합니다.
*   **threshold**

    * `logic`필드에서 `at_least`, `at_most`, `exactly`, `weighted`를 사용한다면 `threahold`를 필수로 작성해야 합니다. 그 외에는 `threahold`가 필요하지 않습니다.
    * `threshold`가 2이면 최소(또는 정확히/최대) 2개의 조건이 만족되어야 합니다.

    ```json
    "logic": "at_least",
    "threshold": 2
    ```

    * logic 가이드 보기: [조건 계산 가이드](../docs/logic_guide.md)
* **symbols**
  * 계산하려는 종목을 여러 개 작성합니다. 작성하지 않으면 시장에 상장된 모든 종목을 대상으로 계산하므로 연산 시간이 오래 걸릴 수 있습니다.
  * `symbol`은 종목 코드입니다.
  * `exchcd`는 거래소 코드입니다. 예: 나스닥(`82`), 뉴욕증권거래소(NYSE, `81`).
* **max\_symbols**
  * 전략 실행 시 최종 대상으로 삼을 종목을 제한합니다.
  * `order`는 `random`: 랜덤 선택, `mcap`: 시가총액 상위 선택
  * `limit`은 대상이 될 상위 종목 수를 정합니다.
* **conditions**
  *   전략 계산 조건들의 모음이며 세 가지 형태를 가집니다.

      1. [`programgarden-community`](../docs/contribution_guide.md) 라이브러리에 기여된 전략을 이용합니다. [Community 전략들 둘러보기](community_list.md)

      ```python
      {
          # Community 전략의 ID를 넣습니다.
          "condition_id": "SMAGoldenDeadCross",
          # 전략에서 요구하는 데이터들을 넣습니다.
          "params": {
              ...
          },
          # logic이 weight인 경우에만 사용됩니다.
          "weight": 0.2
      }
      ```

      2. 개인 전략을 활용하려면 `python` 코드를 이용해 커스텀 가능합니다. [커스텀하기](../docs/custom_dsl.md)
      3. 조건 중첩도 가능합니다. 하위 conditions가 통과되면 상위 conditions의 계산을 수행하는 형태입니다.

      ```python
      {
          "condition_id": "SMAGoldenDeadCross",
          "params": {
              ...
          },
          # 중첩을 합니다.
          "conditions": [
              {
                  "condition_id": "IncreaseAmount",
                  "params": {
                      ...
                  },
                  # 추가 중첩 예시
                  "conditions": [
                      {
                          "condition_id": "VolumeSpike",
                          "params": {
                              ...
                          }
                      }
                  ]
              }
          ]
      }
      ```
* **order\_id**
  * `orders` 영역에서 작성된 매매전략의 order\_id를 기재합니다.

### orders 영역

orders 영역은 사용하려는 매매 전략을 작성하는 곳입니다. 매매 전략은 Community의 전략을 가져오거나 개별적으로 파이썬 코드로 커스텀할 수 있습니다. Community에서 전략을 가져와 사용하는 경우에, 매매전략이 원하는 방향의 매수/매도를 지원하는지 자세하게 체크하고 사용하세요.

사용 방법은 다음과 같습니다.

```python
{
    "orders": [
        # 매매 전략의 ID (중복 불가)
        "order_id": "분할매매_1",
        # 매매 전략 설명
        "description": "시장 분석 전략",
        # 보유 중인 종목은 추가 매수하지 않습니다.
        "block_duplicate_trade": True,
        # 특정 시간 안에서만 매매합니다.
        "order_time": {
            # 시작(start)과 끝(end) 시간입니다.
            "start": "13:58:00",
            "end": "20:00:00",
            # 지정된 요일에만 매매합니다.
            "days": ["mon", "tue", "wed", "thu", "fri"],
            # 국가와 지역 시간대입니다.
            "timezone": "Asia/Seoul",
            # 주문 시간까지 대기 여부: 'defer' 또는 'skip'
            "behavior": "defer",
            # 최대 대기 시간(초)
            "max_delay_seconds": 86400
        },
        # 매매 전략은 1개만 지정할 수 있습니다.
        "condition": {
            # Community에서 선택된 매매 전략 ID
            "condition_id": "StockSplitFunds",
            # 매매 전략에서 요구하는 데이터 값 작성
            "params": {
                "appkey": os.getenv("APPKEY"),
                "appsecretkey": os.getenv("APPSECRET"),
                "percent_balance": 0.8,
                "max_symbols": 2
            }
        }
    ]
}
```

#### 상세설명

* **매매 종류**
  * 현재는 해외주식 매매만 지원하고 있습니다.
  * 선물·옵션 매매 전략도 곧 업데이트될 예정입니다.
* **order\_time**
  * 매매를 수행할 특정 시간대를 지정합니다. 보통 거래소 운영 시간에 맞춥니다.
  * **behavior**는 종목 전략 계산이 끝난 후 매매 시간이 될 때까지 기다릴지 여부입니다. `defer`는 매매 시간까지 기다리며 다음 전략 계산으로 넘어가지 않습니다. `skip`은 매매 시간이 아니면 해당 주문을 건너뛰고 다음 전략 계산으로 넘어갑니다.
* **max\_delay\_seconds**
  * 매매 시간까지 대기할 수 있는 최대 시간(초)입니다. `behavior`가 `defer`일 때 사용됩니다.

### 2.4. 실행하기

자동매매 설정이 완료되었으면, 다음 단계에 따라 실행하세요. 실행용 예제파일은 [여기](../src/programgarden/example/programgarden_example.py)에서 확인할 수 있습니다.

1.  **programgarden 패키지 설치**: 터미널에서 아래 명령어를 실행하여 `programgarden` 패키지를 설치합니다.

    ```bash
    pip install programgarden
    ```
2.  **Python 코드 작성 및 실행**: Python 파일(예: `trading_bot.py`)을 생성하고, 아래 코드를 작성합니다. 이 코드는 Programgarden 인스턴스를 생성하고, 콜백을 설정한 후 시스템 설정을 전달하여 실행합니다.

    *   **Programgarden 인스턴스 생성**:

        ```python
        pg = Programgarden()
        ```
    *   **콜백 설정**: 전략 수행 결과를 모니터링하기 위해 콜백을 설정합니다.

        ```python
        # 전략 수행 응답 콜백
        pg.on_strategies_message(
            callback=lambda message: print(f"Strategies: {message.get('condition_id')}")
        )

        # 실시간 주문 응답 콜백
        pg.on_real_order_message(
            callback=lambda message: print(f"Real Order Message: {message.get('order_type')}")
        )
        ```
    *   **실행**: `pg.run()` 메서드를 호출하여 자동매매를 시작합니다. `system` 파라미터에 위에서 설정한 `settings`, `securities`, `strategies`, `orders`를 포함한 딕셔너리를 전달합니다.

        ```python
        pg.run(
            system={
                "settings": {
                    # ... 시스템 정보 설정 ...
                },
                "securities": {
                    # ... 증권사 설정 ...
                },
                "strategies": [
                    {
                        # ... 전략 설정 ...
                    },
                ],
                "orders": [
                    # ... 주문 전략 설정 ...
                ]
            }
        )
        ```

    최종적으로 자동매매 시스템이 시작됩니다. 전략에 따라 주기적으로 시장을 분석하고, 조건이 만족되면 주문을 실행합니다.

실행용 예제파일에서 확인해보세요. [예제파일 이동](../src/programgarden/example/programgarden_example.py)
