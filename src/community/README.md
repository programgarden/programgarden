# ProgramGarden Community

커뮤니티 전략 플러그인 모음입니다. ConditionNode에 연결하여 다양한 기술적 분석 및 포지션 관리 전략을 적용할 수 있습니다.

## 설치

```bash
pip install programgarden-community

# Poetry 사용 시 (개발 환경)
poetry add programgarden-community
```

요구 사항: Python 3.12+

## 포함 플러그인 (67개)

### Technical (기술적 분석) - 52개

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
| IchimokuCloud | 일목균형표 (전환선, 기준선, 구름대) |
| VWAP | 거래량 가중 평균 가격 |
| SuperTrend | ATR 기반 추세 추종 |
| WilliamsR | 윌리엄스 %R 오실레이터 |
| CCI | 상품채널지수 |
| CMF | 차이킨 자금흐름 |
| TRIX | 3중 지수이동평균 오실레이터 |
| ParabolicSAR | 파라볼릭 SAR 추세/반전 |
| PivotPoint | 피봇포인트 지지/저항 |
| KeltnerChannel | 켈트너 채널 (EMA + ATR) |
| SqueezeMomentum | BB/KC 스퀴즈 모멘텀 |
| ZScore | 통계적 Z-Score 편차 |
| MomentumRank | 모멘텀 순위 상위/하위 선별 |
| RelativeStrength | 벤치마크 대비 상대강도 |
| MeanReversion | 평균회귀 매매 |
| CorrelationAnalysis | 상관관계 분석 |
| RegimeDetection | 시장 레짐 감지 (강세/약세/횡보) |
| MarketInternals | 시장 내부 지표 (등락비, 신고가/신저가) |
| MultiTimeframeConfirmation | 다중 타임프레임 확인 |
| GoldenRatio | 피보나치 되돌림 |
| BreakoutRetest | 돌파 후 리테스트 감지 |
| Doji | 도지 캔들 패턴 |
| Engulfing | 장악형 캔들 패턴 |
| HammerShootingStar | 망치형/유성형 캔들 |
| MorningEveningStar | 샛별/석별 3봉 패턴 |
| ThreeLineStrike | 쓰리라인스트라이크 패턴 |
| ContangoBackwardation | 선물 콘탱고/백워데이션 감지 |
| CalendarSpread | 선물 월물 스프레드 |
| RollManagement | 선물 롤오버 관리 |
| PairTrading | 페어트레이딩 (Z-Score 기반) |
| TSMOM | 시계열 모멘텀 |
| ConnorsRSI | 복합 RSI (클래식+연속+백분위) |
| MFI | 자금흐름지수 (거래량 가중 RSI) |
| CoppockCurve | 코폭 커브 (장기 바닥 감지) |
| ElderRay | 엘더레이 (불/베어 파워) |
| TurtleBreakout | 터틀 돌파 (돈치안 채널 + ATR 손절) |
| VolatilityBreakout | 변동성 돌파 (래리 윌리엄스) |
| SeasonalFilter | 계절성 필터 (할로윈 효과) |
| TAA | 전술적 자산배분 (SMA 필터) |
| MagicFormula | 마법공식 (ROC+EY 순위) |
| SupportResistanceLevels | 지지/저항 레벨 감지 (스윙 기반 클러스터링) |

### Position (포지션 관리) - 15개

| 플러그인 | 설명 |
|----------|------|
| StopLoss | 손절 (손실 한도 도달 시 매도) |
| ProfitTarget | 익절 (수익 목표 도달 시 매도) |
| TrailingStop | 트레일링 스탑 (HWM 기반 drawdown 관리) |
| TimeBasedExit | 보유 기간 초과 시 청산 |
| PartialTakeProfit | 다단계 분할 익절 |
| DrawdownProtection | 드로우다운 보호 (최고점 대비 하락 제한) |
| MaxPositionLimit | 포지션 수/비중 제한 |
| VolatilityPositionSizing | 변동성 기반 포지션 사이징 |
| KellyCriterion | 켈리 기준 최적 포지션 크기 |
| RiskParity | 리스크 패리티 (동일 위험 배분) |
| VaRCVaRMonitor | VaR/CVaR 위험 모니터링 |
| CorrelationGuard | 상관관계 레짐 감시 |
| BetaHedge | 베타 헤지 (시장 중립) |
| DynamicStopLoss | ATR 기반 동적 손절 |
| LevelTouch | 레벨 터치/돌파/역할전환 감지 |

### 커뮤니티 노드 (4개)

| 노드 | 카테고리 | 설명 |
|------|----------|------|
| TelegramNode | messaging | Telegram Bot API 메시지 전송 |
| FearGreedIndexNode | market | CNN Fear & Greed Index 조회 |
| FundamentalDataNode | market | FMP API 재무 데이터 조회 |
| FileReaderNode | data | 파일 파싱 (PDF, TXT, CSV, JSON, MD, DOCX, XLSX) |

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
