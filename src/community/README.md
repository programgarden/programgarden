# ProgramGarden Community

커뮤니티 전략 플러그인 모음입니다. ConditionNode에 연결하여 다양한 기술적 분석 및 포지션 관리 전략을 적용할 수 있습니다.

## 설치

```bash
pip install programgarden-community

# Poetry 사용 시 (개발 환경)
poetry add programgarden-community
```

요구 사항: Python 3.12+

## 포함 플러그인 (14개)

### Technical (기술적 분석) - 11개

| 플러그인 | 설명 |
|----------|------|
| RSI | RSI 과매수/과매도 조건 |
| MACD | MACD 크로스오버 조건 |
| BollingerBands | 볼린저밴드 이탈/복귀 조건 |
| VolumeSpike | 거래량 급증 감지 |
| MovingAverageCross | 이동평균 골든/데드 크로스 |
| DualMomentum | 듀얼 모멘텀 (절대 + 상대) |
| Stochastic | 스토캐스틱 오실레이터 (%K, %D) |
| ATR | ATR 변동성 측정 |
| PriceChannel | 가격 채널 / 돈치안 채널 |
| ADX | ADX 추세 강도 측정 |
| OBV | OBV 거래량 기반 모멘텀 |

### Position (포지션 관리) - 3개

| 플러그인 | 설명 |
|----------|------|
| StopLoss | 손절 (손실 한도 도달 시 매도) |
| ProfitTarget | 익절 (수익 목표 도달 시 매도) |
| TrailingStop | 트레일링 스탑 (HWM 기반 drawdown 관리) |

## 사용법

```python
from programgarden_community.plugins import register_all_plugins, get_plugin, list_plugins

# 모든 플러그인 등록
register_all_plugins()

# 특정 플러그인 스키마 조회
schema = get_plugin("RSI")

# 카테고리별 플러그인 목록
plugins = list_plugins(category="technical")
```

## 기여하기

새로운 전략 플러그인 PR을 환영합니다. `plugins/` 디렉토리에 새 폴더를 만들고 `*_SCHEMA`와 `*_condition` 함수를 구현하면 됩니다.

## 변경 로그

자세한 변경 사항은 `CHANGELOG.md`를 참고하세요.
