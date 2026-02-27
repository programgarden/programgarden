"""
LevelTouch (레벨 터치/돌파) 플러그인 테스트
"""

import json
import pytest
from unittest.mock import MagicMock
from programgarden_community.plugins.level_touch import (
    level_touch_condition,
    detect_touch,
    detect_breakout,
    detect_role_reversal,
    LEVEL_TOUCH_SCHEMA,
    risk_features,
    _parse_levels,
)


def _make_price_data(symbol="AAPL", exchange="NASDAQ", closes=None):
    """주어진 종가 리스트로 테스트 데이터 생성"""
    if closes is None:
        closes = [100, 102, 105, 103, 100, 98, 100, 102, 105, 108]

    data = []
    for i, close in enumerate(closes):
        data.append({
            "symbol": symbol,
            "exchange": exchange,
            "date": f"202501{i+1:02d}",
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": 1000000,
        })
    return data


def _make_mock_context(initial_states=None):
    """risk_tracker mock context 생성"""
    states = initial_states or {}

    context = MagicMock()
    tracker = MagicMock()

    def load_state(key):
        return states.get(key)

    def save_state(key, value):
        states[key] = value

    tracker.load_state = MagicMock(side_effect=load_state)
    tracker.save_state = MagicMock(side_effect=save_state)
    context.risk_tracker = tracker

    return context, states


class TestDetectTouch:
    """터치 감지 테스트"""

    def test_touching_level(self):
        """레벨 tolerance 내 가격"""
        assert detect_touch(100.5, 100.0, tolerance=0.01) is True

    def test_not_touching_level(self):
        """레벨 tolerance 밖 가격"""
        assert detect_touch(105.0, 100.0, tolerance=0.01) is False

    def test_exact_level(self):
        """정확히 레벨 위"""
        assert detect_touch(100.0, 100.0, tolerance=0.01) is True

    def test_zero_level(self):
        """레벨 가격 0"""
        assert detect_touch(100.0, 0, tolerance=0.01) is False

    def test_tight_tolerance(self):
        """매우 좁은 tolerance"""
        assert detect_touch(100.3, 100.0, tolerance=0.003) is True
        assert detect_touch(100.5, 100.0, tolerance=0.003) is False

    def test_wide_tolerance(self):
        """넓은 tolerance"""
        assert detect_touch(102.0, 100.0, tolerance=0.03) is True


class TestDetectBreakout:
    """돌파 감지 테스트"""

    def test_support_breakout(self):
        """지지선 하향 돌파"""
        closes = [100, 99, 98, 97]  # 지지선(100) 아래로 돌파
        assert detect_breakout(closes, 100.0, "support", threshold=0.015, confirm_bars=2) is True

    def test_resistance_breakout(self):
        """저항선 상향 돌파"""
        closes = [100, 101, 102, 103]  # 저항선(100) 위로 돌파
        assert detect_breakout(closes, 100.0, "resistance", threshold=0.015, confirm_bars=2) is True

    def test_no_breakout_within_threshold(self):
        """threshold 미달"""
        closes = [100, 100.5, 101]  # 0.5% 수준 - threshold(1.5%) 미달
        assert detect_breakout(closes, 100.0, "resistance", threshold=0.015, confirm_bars=2) is False

    def test_breakout_not_confirmed(self):
        """확인 봉 미달"""
        closes = [100, 103, 99]  # 마지막 봉이 레벨 아래로 복귀
        assert detect_breakout(closes, 100.0, "resistance", threshold=0.015, confirm_bars=2) is False

    def test_insufficient_data(self):
        """데이터 부족"""
        assert detect_breakout([100], 100.0, "support", threshold=0.015, confirm_bars=2) is False

    def test_zero_level(self):
        """레벨 0"""
        assert detect_breakout([100, 101], 0, "support", threshold=0.015, confirm_bars=1) is False

    def test_confirm_bars_1(self):
        """confirm_bars=1"""
        closes = [100, 103]
        assert detect_breakout(closes, 100.0, "resistance", threshold=0.015, confirm_bars=1) is True

    def test_confirm_bars_3(self):
        """confirm_bars=3"""
        closes = [100, 103, 104, 105]
        assert detect_breakout(closes, 100.0, "resistance", threshold=0.015, confirm_bars=3) is True


class TestDetectRoleReversal:
    """역할 전환 감지 테스트"""

    def test_resistance_to_support(self):
        """저항 돌파 후 지지로 전환"""
        # 저항 100을 상향 돌파 후, 가격이 100 위에서 100으로 되돌림
        assert detect_role_reversal(100.5, 100.0, "resistance", tolerance=0.01) is True

    def test_support_to_resistance(self):
        """지지 돌파 후 저항으로 전환"""
        # 지지 100을 하향 돌파 후, 가격이 100 아래에서 100으로 되돌림
        assert detect_role_reversal(99.5, 100.0, "support", tolerance=0.01) is True

    def test_too_far_from_level(self):
        """레벨에서 너무 멀면 전환 아님"""
        assert detect_role_reversal(105.0, 100.0, "resistance", tolerance=0.01) is False

    def test_zero_level(self):
        """레벨 0"""
        assert detect_role_reversal(100.0, 0, "resistance", tolerance=0.01) is False

    def test_wrong_side_after_breakout(self):
        """돌파 방향 반대편에서는 전환 아님"""
        # 저항 100을 상향 돌파했으면, 가격이 100 위에 있어야 지지 전환
        # 가격이 97이면 (tolerance 1%를 감안해도) 전환 아님
        assert detect_role_reversal(97.0, 100.0, "resistance", tolerance=0.01) is False


class TestParseLevels:
    """레벨 입력 파싱 테스트"""

    def test_json_string(self):
        """JSON 문자열 파싱"""
        levels = _parse_levels('[{"price": 100, "type": "support"}, {"price": 120, "type": "resistance"}]')
        assert len(levels) == 2
        assert levels[0]["price"] == 100.0
        assert levels[0]["type"] == "support"

    def test_dict_list(self):
        """dict 리스트 직접 입력"""
        levels = _parse_levels([
            {"price": 100, "type": "support"},
            {"price": 120, "type": "resistance"},
        ])
        assert len(levels) == 2

    def test_sr_levels_output_format(self):
        """SupportResistanceLevels symbol_results 형식"""
        sr_output = [
            {
                "symbol": "AAPL",
                "clusters": [
                    {"price": 100.0, "type": "support", "touch_count": 3},
                    {"price": 120.0, "type": "resistance", "touch_count": 2},
                ],
            }
        ]
        levels = _parse_levels(sr_output)
        assert len(levels) == 2
        assert levels[0]["price"] == 100.0
        assert levels[0]["touch_count"] == 3

    def test_empty_string(self):
        """빈 문자열"""
        assert _parse_levels("") == []
        assert _parse_levels("[]") == []

    def test_invalid_json(self):
        """잘못된 JSON"""
        assert _parse_levels("not json") == []

    def test_none_input(self):
        """None 입력"""
        assert _parse_levels(None) == []

    def test_non_list_input(self):
        """리스트가 아닌 입력"""
        assert _parse_levels({"price": 100}) == []

    def test_invalid_price(self):
        """유효하지 않은 price"""
        levels = _parse_levels([{"price": "invalid", "type": "support"}])
        assert len(levels) == 0

    def test_default_type(self):
        """type 없으면 기본값 support"""
        levels = _parse_levels([{"price": 100}])
        assert len(levels) == 1
        assert levels[0]["type"] == "support"


class TestLevelTouchCondition:
    """조건 함수 전체 테스트"""

    @pytest.mark.asyncio
    async def test_first_touch_mode(self):
        """first_touch 모드: 첫 터치에서 신호"""
        # 가격이 100 근처로 접근
        data = _make_price_data(closes=[110, 108, 106, 104, 102, 100.5])
        levels = [{"price": 100.0, "type": "support"}]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "first_touch",
            },
        )

        assert result["analysis"]["mode"] == "first_touch"
        # 첫 터치이므로 신호 발생
        sr = result["symbol_results"][0]
        assert sr["signal"] == "buy"
        assert len(result["passed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_first_touch_no_signal_on_second(self):
        """first_touch 모드: 이미 터치한 레벨에서 재터치 시 신호 없음 (with state)"""
        context, states = _make_mock_context({
            "sr_level_AAPL_100.0": {
                "touch_count": 1,
                "broken": False,
                "original_type": "support",
                "reversed": False,
                "last_touch_date": "20250101",
            }
        })

        data = _make_price_data(closes=[110, 105, 100.5])
        levels = [{"price": 100.0, "type": "support"}]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "first_touch",
            },
            context=context,
        )

        # 이미 1회 터치됨 → 재터치 시 touch_count=2 → 신호 없음
        sr = result["symbol_results"][0]
        assert sr["signal"] is None

    @pytest.mark.asyncio
    async def test_role_reversal_mode(self):
        """role_reversal 모드: 돌파 후 역할 전환 확인"""
        # 저항(100) 돌파 후 되돌림: 가격이 100 위로 올라감 → 100으로 되돌아옴
        data = _make_price_data(closes=[95, 97, 99, 102, 104, 106, 104, 102, 100.5])
        levels = [{"price": 100.0, "type": "resistance"}]

        # 이미 돌파된 상태를 state로 설정
        context, states = _make_mock_context({
            "sr_level_AAPL_100.0": {
                "touch_count": 1,
                "broken": True,
                "original_type": "resistance",
                "reversed": False,
                "last_touch_date": "20250105",
            }
        })

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "role_reversal",
            },
            context=context,
        )

        # 저항 돌파 후 지지로 전환 → 매수 신호
        sr = result["symbol_results"][0]
        assert sr["signal"] == "buy"

    @pytest.mark.asyncio
    async def test_cluster_bounce_mode(self):
        """cluster_bounce 모드: 강한 클러스터에서 반등"""
        data = _make_price_data(closes=[110, 108, 106, 104, 102, 100.5])
        # touch_count >= 2인 강한 클러스터
        levels = [{"price": 100.0, "type": "support", "touch_count": 3}]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "cluster_bounce",
            },
        )

        sr = result["symbol_results"][0]
        assert sr["signal"] == "buy"

    @pytest.mark.asyncio
    async def test_cluster_bounce_weak_level_no_signal(self):
        """cluster_bounce 모드: 약한 레벨(touch_count=1)에서는 신호 없음"""
        data = _make_price_data(closes=[110, 108, 106, 104, 102, 100.5])
        levels = [{"price": 100.0, "type": "support", "touch_count": 1}]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "cluster_bounce",
            },
        )

        sr = result["symbol_results"][0]
        assert sr["signal"] is None

    @pytest.mark.asyncio
    async def test_resistance_sell_signal(self):
        """저항선 터치 시 매도 신호"""
        data = _make_price_data(closes=[90, 92, 95, 97, 99, 99.5])
        levels = [{"price": 100.0, "type": "resistance"}]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "first_touch",
            },
        )

        sr = result["symbol_results"][0]
        assert sr["signal"] == "sell"

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await level_touch_condition(
            data=[],
            fields={"levels": '[{"price": 100, "type": "support"}]'},
        )
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_no_levels(self):
        """레벨 없음"""
        data = _make_price_data()
        result = await level_touch_condition(
            data=data,
            fields={"levels": "[]"},
        )
        assert result["result"] is False
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_no_matching_symbol_data(self):
        """종목 데이터 없음"""
        data = _make_price_data(symbol="AAPL")
        result = await level_touch_condition(
            data=data,
            fields={"levels": '[{"price": 100, "type": "support"}]'},
            symbols=[{"symbol": "TSLA", "exchange": "NASDAQ"}],
        )
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        """다종목 처리"""
        data = _make_price_data("AAPL", closes=[110, 105, 100.5]) + \
               _make_price_data("TSLA", closes=[210, 205, 200.5])
        levels = [
            {"price": 100.0, "type": "support"},
            {"price": 200.0, "type": "support"},
        ]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "first_touch",
            },
        )

        assert len(result["symbol_results"]) == 2

    @pytest.mark.asyncio
    async def test_risk_tracker_state_persistence(self):
        """risk_tracker state 저장/로드"""
        context, states = _make_mock_context()

        data = _make_price_data(closes=[110, 108, 106, 104, 102, 100.5])
        levels = [{"price": 100.0, "type": "support"}]

        await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "first_touch",
            },
            context=context,
        )

        # state가 저장됨
        key = "sr_level_AAPL_100.0"
        assert key in states
        assert states[key]["touch_count"] >= 1

    @pytest.mark.asyncio
    async def test_no_risk_tracker_fallback(self):
        """risk_tracker 없을 때 fallback"""
        data = _make_price_data(closes=[110, 105, 100.5])
        levels = [{"price": 100.0, "type": "support"}]

        # context 없이 호출
        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "first_touch",
            },
            context=None,
        )

        # 에러 없이 동작
        assert "symbol_results" in result

    @pytest.mark.asyncio
    async def test_time_series_output(self):
        """time_series 출력 형식"""
        data = _make_price_data(closes=[110, 105, 100.5])
        levels = [{"price": 100.0, "type": "support"}]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "mode": "first_touch",
            },
        )

        assert len(result["values"]) == 1
        ts = result["values"][0]
        assert "time_series" in ts
        assert len(ts["time_series"]) == 3

    @pytest.mark.asyncio
    async def test_field_defaults(self):
        """필드 기본값"""
        data = _make_price_data()
        result = await level_touch_condition(
            data=data,
            fields={"levels": '[{"price": 100, "type": "support"}]'},
        )

        assert result["analysis"]["mode"] == "first_touch"
        assert result["analysis"]["touch_tolerance"] == 0.01
        assert result["analysis"]["breakout_threshold"] == 0.015
        assert result["analysis"]["confirm_bars"] == 2

    @pytest.mark.asyncio
    async def test_levels_from_sr_plugin_output(self):
        """SupportResistanceLevels 출력을 직접 입력으로"""
        data = _make_price_data(closes=[110, 105, 100.5])
        sr_output = [
            {
                "symbol": "AAPL",
                "clusters": [
                    {"price": 100.0, "type": "support", "touch_count": 3},
                ],
            }
        ]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(sr_output),
                "touch_tolerance": 0.01,
                "mode": "cluster_bounce",
            },
        )

        sr = result["symbol_results"][0]
        assert sr["signal"] == "buy"

    @pytest.mark.asyncio
    async def test_breakout_detection_in_condition(self):
        """조건 함수 내 돌파 감지"""
        # 지지선(100) 하향 돌파: 가격이 100 아래로 2봉 연속
        data = _make_price_data(closes=[105, 103, 100, 97, 96])
        levels = [{"price": 100.0, "type": "support"}]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "breakout_threshold": 0.02,
                "confirm_bars": 2,
                "mode": "first_touch",
            },
        )

        # 돌파 시에는 first_touch 신호가 아닌 다른 상태
        # 가격이 레벨에서 멀리 떨어져 있으므로 터치 아님
        sr = result["symbol_results"][0]
        events = sr["level_events"]
        assert len(events) >= 1


class TestLevelTouchRiskFeatures:
    """risk_features 선언 테스트"""

    def test_risk_features_declared(self):
        assert "state" in risk_features

    def test_risk_features_set_type(self):
        assert isinstance(risk_features, set)


class TestLevelTouchSchema:
    """스키마 검증 테스트"""

    def test_schema_id(self):
        assert LEVEL_TOUCH_SCHEMA.id == "LevelTouch"

    def test_schema_category(self):
        assert LEVEL_TOUCH_SCHEMA.category == "technical"

    def test_schema_fields(self):
        fields = LEVEL_TOUCH_SCHEMA.fields_schema
        assert "levels" in fields
        assert "touch_tolerance" in fields
        assert "breakout_threshold" in fields
        assert "confirm_bars" in fields
        assert "mode" in fields

    def test_schema_mode_enum(self):
        mode = LEVEL_TOUCH_SCHEMA.fields_schema["mode"]
        assert set(mode["enum"]) == {"first_touch", "role_reversal", "cluster_bounce"}

    def test_schema_ko_locale(self):
        assert "ko" in LEVEL_TOUCH_SCHEMA.locales
        ko = LEVEL_TOUCH_SCHEMA.locales["ko"]
        assert "name" in ko
        assert "description" in ko

    def test_schema_tags(self):
        assert "touch" in LEVEL_TOUCH_SCHEMA.tags
        assert "breakout" in LEVEL_TOUCH_SCHEMA.tags
        assert "role_reversal" in LEVEL_TOUCH_SCHEMA.tags

    def test_schema_products(self):
        products = LEVEL_TOUCH_SCHEMA.products
        assert len(products) == 2


class TestIntegrationScenarios:
    """통합 시나리오 테스트"""

    @pytest.mark.asyncio
    async def test_pipeline_sr_to_level_touch(self):
        """SupportResistanceLevels → LevelTouch 파이프라인"""
        from programgarden_community.plugins.support_resistance_levels import (
            support_resistance_levels_condition,
        )

        # Phase 1: S/R 레벨 감지
        data = []
        # 명확한 패턴: 상승→고점(120)→하락→저점(95)→상승→현재(100)
        prices = [100, 105, 110, 115, 120, 118, 114, 108, 102, 97, 95, 97, 100]
        for i, p in enumerate(prices):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": p - 1, "high": p + 3, "low": p - 3,
                "close": p, "volume": 1000000,
            })

        sr_result = await support_resistance_levels_condition(
            data=data,
            fields={
                "lookback": 20,
                "swing_strength": 2,
                "direction": "both",
                "min_cluster_size": 1,
            },
        )

        # Phase 2: 감지된 레벨을 LevelTouch에 전달
        touch_result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(sr_result["symbol_results"]),
                "touch_tolerance": 0.03,
                "mode": "first_touch",
            },
        )

        assert "symbol_results" in touch_result
        assert touch_result["analysis"]["indicator"] == "LevelTouch"

    @pytest.mark.asyncio
    async def test_scenario_support_bounce(self):
        """시나리오: 지지 레벨 터치 → 반등 → 매수 신호"""
        # 가격이 지지선(100)에 접근
        data = _make_price_data(closes=[115, 112, 108, 105, 102, 100.5])
        levels = [{"price": 100.0, "type": "support", "touch_count": 3}]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "cluster_bounce",
            },
        )

        assert result["result"] is True
        assert result["symbol_results"][0]["signal"] == "buy"

    @pytest.mark.asyncio
    async def test_scenario_resistance_breakout_role_reversal(self):
        """시나리오: 저항 돌파 → 되돌림 → 역할 전환 매수"""
        # 가격: 저항(100) 돌파 후 100.5로 되돌림
        data = _make_price_data(closes=[95, 97, 99, 102, 105, 108, 105, 102, 100.5])
        levels = [{"price": 100.0, "type": "resistance"}]

        context, states = _make_mock_context({
            "sr_level_AAPL_100.0": {
                "touch_count": 1,
                "broken": True,
                "original_type": "resistance",
                "reversed": False,
                "last_touch_date": "20250105",
            }
        })

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "role_reversal",
            },
            context=context,
        )

        assert result["result"] is True
        assert result["symbol_results"][0]["signal"] == "buy"

    @pytest.mark.asyncio
    async def test_scenario_cluster_strong_zone(self):
        """시나리오: 강한 클러스터 구역에서 반등"""
        data = _make_price_data(closes=[115, 110, 105, 102, 100.5])
        # 여러 레벨이 100 근처에 밀집 (강한 구역)
        levels = [
            {"price": 99.5, "type": "support", "touch_count": 2},
            {"price": 100.0, "type": "support", "touch_count": 3},
            {"price": 100.5, "type": "support", "touch_count": 2},
        ]

        result = await level_touch_condition(
            data=data,
            fields={
                "levels": json.dumps(levels),
                "touch_tolerance": 0.01,
                "mode": "cluster_bounce",
            },
        )

        assert result["result"] is True
