# Programgarden Core

Programgarden은 AI 시대에 맞춰 파이썬을 모르는 투자자도 개인화된 시스템 트레이딩을 자동으로 수행할 수 있게 돕는 오픈소스입니다. 본 저장소는 그 중 핵심 타입, 베이스 클래스, 로깅, 한글 별칭 처리 등 엔진과 플러그인이 공통으로 사용하는 "코어" 모듈입니다. LS증권 OpenAPI를 메인으로 해외 주식/파생 거래 자동화를 목표로 하며, 타 증권사 지원은 추후 확장될 예정입니다.

- 문서(비개발자 빠른 시작): https://programgarden.gitbook.io/docs/invest/non_dev_quick_guide
- 문서(개발자 구조 안내): https://programgarden.gitbook.io/docs/develop/structure

- 유튜브: https://www.youtube.com/@programgarden
- 실시간소통 오픈톡방: https://open.kakao.com/o/gKVObqUh

## 주요 특징

- 자동화 전략 실행을 위한 타입 안전한 계약 제공: System/Strategy/Order 구성 스키마를 TypedDict로 정의해 IDE 친화적이고 안전합니다.
- 실시간 주문 처리 인터페이스: 신규/정정/취소 주문 베이스 클래스를 제공하고, 브로커 콜백 타입을 명확히 정의합니다.
- 증권사 API 통합 전제: LS증권 OpenAPI 사용을 염두에 둔 필드/코드값을 표준화했습니다.
- 플러그인 기반 조건: 전략 조건(BaseStrategyCondition…)을 상속해 다양한 전략 플러그인을 손쉽게 확장할 수 있습니다.
- 한글 별칭 지원: 설정 파일에서 한글 키를 사용해도 `normalize_system_config` 로 표준 키로 자동 변환됩니다.
- 컬러 로깅: `pg_log`, `system_logger`, `strategy_logger` 등 범주화된 컬러 로그를 기본 제공합니다.

## 설치

아래는 일반적인 설치 방법 예시입니다.

```bash
# PyPI에 게시된 경우
pip install programgarden-core

# Poetry 사용 시(개발 환경)
poetry add programgarden-core
```

요구 사항: Python 3.9+

## 타입과 베이스 클래스를 어디서 가져오나요?

코어는 사용 빈도가 높은 심볼들을 패키지 루트에서 재노출합니다.

```python
from programgarden_core import (
  # 설정/전략/주문 타입
  SystemType, StrategyType, DictConditionType,
  OrderType, OrderRealResponseType,

  # 심볼/포지션 타입
  SymbolInfoOverseasStock, SymbolInfoOverseasFutures,
  HeldSymbol, NonTradedSymbol,

  # 전략 베이스
  BaseStrategyConditionOverseasStock, BaseStrategyConditionOverseasFutures,

  # 주문 베이스(신규/정정/취소)
  BaseNewOrderOverseasStock, BaseModifyOrderOverseasStock, BaseCancelOrderOverseasStock,
  BaseNewOrderOverseasFutures, BaseModifyOrderOverseasFutures, BaseCancelOrderOverseasFutures,

  # 한글 별칭 유틸
  normalize_system_config,

  # 로깅
  pg_log, system_logger, strategy_logger,
)
```


## 기여하기

이슈/토론/PR 환영합니다. 버그 리포트 시 재현 단계와 최소 예시를 함께 제공해 주시면 빠르게 대응할 수 있습니다.

## 변경 로그

자세한 변경 사항은 루트의 `CHANGELOG.md` 를 참고하세요.

