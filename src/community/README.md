# ProgramGarden Community

증권 분석에 필요한 외부 전략을 모아둔 커뮤니티입니다. 커뮤니티의 발전은 전략을 기여하는 모든 개발자와 함께합니다.

## 개요

`programgarden-community`는 개발자들이 자신만의 커스텀 전략을 공유할 수 있는 공간입니다. 공유된 전략은 다른 투자자들이 쉽게 사용할 수 있으며, DSL을 작성하여 비개발자도 쉽게 활용할 수 있습니다.

## 커스텀 전략 공유하기

커스텀 전략은 `programgarden_community/` 아래에 상품별 폴더를 선택합니다. 예를 들어, 해외 주식 전략의 경우:

- 컨디션: `overseas_stock/strategy_conditions/{StrategyID}/`
- 신규 매수: `overseas_stock/new_buy_conditions/{StrategyID}/`
- 신규 매도: `overseas_stock/new_sell_conditions/{StrategyID}/`

각 전략 폴더에는 다음 파일이 필수입니다:
- `__init__.py`: 전략 클래스를 정의
- `README.md`: 전략 설명, 파라미터, 사용법

자세한 내용은 [커뮤니티 기여 가이드](https://programgarden.gitbook.io/docs/undefined-1/contribution_guide)에서 확인하세요.

## 기여 방법

- 로컬에서 테스트를 완료한 후 PR 제출해 주세요.
- Python 3.9+ 호환 확인해 주세요.
- 폴더 구조 검증: `__init__.py`와 `README.md` 필수입니다.

질문이나 토론은 GitHub Issues나 Discussions를 이용하세요.
