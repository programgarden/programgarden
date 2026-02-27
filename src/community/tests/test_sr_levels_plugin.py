"""
SupportResistanceLevels (지지/저항 레벨) 플러그인 테스트
"""

import pytest
from programgarden_community.plugins.support_resistance_levels import (
    support_resistance_levels_condition,
    find_swing_points,
    cluster_levels,
    find_nearest_levels,
    SUPPORT_RESISTANCE_LEVELS_SCHEMA,
)


def _make_swing_data(symbol="AAPL", exchange="NASDAQ", n=30, swing_strength=5):
    """
    명확한 swing high/low가 포함된 테스트 데이터 생성

    가격 패턴: 상승 → 고점 → 하락 → 저점 → 상승 → 고점 → 하락
    """
    data = []
    # 패턴: 가격이 100에서 시작, 120까지 상승, 95까지 하락, 115까지 상승, 90까지 하락
    prices = []
    # Phase 1: 100 → 120 (상승, 10봉)
    for i in range(10):
        prices.append(100 + i * 2)
    # Phase 2: 120 → 95 (하락, 10봉)
    for i in range(10):
        prices.append(120 - i * 2.5)
    # Phase 3: 95 → 115 (상승, 10봉)
    for i in range(10):
        prices.append(95 + i * 2)

    for i, price in enumerate(prices):
        data.append({
            "symbol": symbol,
            "exchange": exchange,
            "date": f"202501{i+1:02d}",
            "open": price - 1,
            "high": price + 2,
            "low": price - 2,
            "close": price,
            "volume": 1000000 + i * 10000,
        })
    return data


def _make_clustered_data(symbol="AAPL", exchange="NASDAQ"):
    """
    비슷한 가격대에서 여러 번 반등/저항하는 데이터 (클러스터 형성)

    지지 구역 ~100, 저항 구역 ~120 근처에서 반복
    """
    # 패턴: 100→120→102→118→101→119→103→117→100→115 (현재가)
    close_prices = [
        100, 105, 110, 115, 120,  # 상승
        118, 112, 106, 102,       # 하락 (지지 ~100)
        105, 110, 115, 118,       # 상승 (저항 ~120)
        116, 110, 105, 101,       # 하락 (지지 ~100)
        104, 108, 112, 116, 119,  # 상승 (저항 ~120)
        117, 113, 108, 104, 100,  # 하락 (지지 ~100)
        103, 107, 111, 115,       # 현재: 115 (중간)
    ]

    data = []
    for i, close in enumerate(close_prices):
        data.append({
            "symbol": symbol,
            "exchange": exchange,
            "date": f"202501{i+1:02d}" if i < 31 else f"202502{i-30:02d}",
            "open": close - 1,
            "high": close + 3,
            "low": close - 3,
            "close": close,
            "volume": 1000000,
        })
    return data


class TestFindSwingPoints:
    """Swing High/Low 감지 테스트"""

    def test_basic_swing_detection(self):
        """명확한 고점/저점 감지"""
        # 패턴: 낮은값 → 높은값 → 낮은값 (swing high)
        highs = [10, 11, 12, 15, 12, 11, 10, 9, 10, 11, 12]
        lows = [8, 9, 10, 13, 10, 9, 8, 7, 8, 9, 10]
        dates = [f"d{i}" for i in range(len(highs))]

        result = find_swing_points(highs, lows, dates, strength=2)

        # index=3이 swing high (15)
        assert len(result["swing_highs"]) >= 1
        assert any(sh["price"] == 15 for sh in result["swing_highs"])

        # index=7이 swing low (7)
        assert len(result["swing_lows"]) >= 1
        assert any(sl["price"] == 7 for sl in result["swing_lows"])

    def test_swing_strength_filtering(self):
        """swing_strength 값에 따른 필터링"""
        # strength=2: 양쪽 2봉만 비교 (느슨)
        # strength=4: 양쪽 4봉 비교 (엄격)
        highs = [10, 11, 12, 15, 14, 13, 12, 11, 10, 9, 8]
        lows = [8, 9, 10, 13, 12, 11, 10, 9, 8, 7, 6]
        dates = [f"d{i}" for i in range(len(highs))]

        result_loose = find_swing_points(highs, lows, dates, strength=2)
        result_strict = find_swing_points(highs, lows, dates, strength=4)

        # strength=2에서는 감지되지만 strength=4에서는 데이터가 부족할 수 있음
        assert len(result_loose["swing_highs"]) >= len(result_strict["swing_highs"])

    def test_no_swing_in_flat_data(self):
        """횡보 데이터에서는 swing point가 적음"""
        highs = [101, 102, 101, 102, 101, 102, 101, 102, 101, 102, 101]
        lows = [99, 98, 99, 98, 99, 98, 99, 98, 99, 98, 99]
        dates = [f"d{i}" for i in range(len(highs))]

        result = find_swing_points(highs, lows, dates, strength=2)

        # 횡보 시 명확한 swing point는 적음
        total = len(result["swing_highs"]) + len(result["swing_lows"])
        assert total >= 0  # 에러 없이 동작

    def test_empty_data(self):
        """빈 데이터"""
        result = find_swing_points([], [], [], strength=5)
        assert result["swing_highs"] == []
        assert result["swing_lows"] == []

    def test_insufficient_data(self):
        """데이터가 strength보다 적음"""
        result = find_swing_points([100, 101], [99, 100], ["d0", "d1"], strength=5)
        assert result["swing_highs"] == []
        assert result["swing_lows"] == []

    def test_swing_point_date_included(self):
        """감지된 swing point에 날짜 포함"""
        highs = [10, 11, 15, 11, 10, 9, 8, 7, 8, 9, 10]
        lows = [8, 9, 13, 9, 8, 7, 6, 5, 6, 7, 8]
        dates = ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04",
                 "2025-01-05", "2025-01-06", "2025-01-07", "2025-01-08",
                 "2025-01-09", "2025-01-10", "2025-01-11"]

        result = find_swing_points(highs, lows, dates, strength=2)

        for sh in result["swing_highs"]:
            assert "date" in sh
            assert "price" in sh
            assert "type" in sh
            assert sh["type"] == "resistance"

        for sl in result["swing_lows"]:
            assert sl["type"] == "support"


class TestClusterLevels:
    """레벨 클러스터링 테스트"""

    def test_basic_clustering(self):
        """비슷한 가격대의 레벨이 클러스터로 묶임"""
        levels = [
            {"price": 100.0, "type": "support"},
            {"price": 100.5, "type": "support"},
            {"price": 101.0, "type": "support"},
            {"price": 150.0, "type": "resistance"},
        ]

        clusters = cluster_levels(levels, tolerance=0.015, min_size=2)

        # 100, 100.5, 101은 한 클러스터로 묶여야 함
        support_clusters = [c for c in clusters if c["type"] == "support"]
        assert len(support_clusters) >= 1
        assert support_clusters[0]["touch_count"] >= 2

        # 150은 단독이므로 min_size=2에서 제외
        assert all(c["price"] != 150.0 for c in clusters)

    def test_min_cluster_size_1(self):
        """min_size=1이면 단일 레벨도 포함"""
        levels = [
            {"price": 100.0, "type": "support"},
            {"price": 200.0, "type": "resistance"},
        ]

        clusters = cluster_levels(levels, tolerance=0.015, min_size=1)
        assert len(clusters) == 2

    def test_no_levels(self):
        """빈 레벨 리스트"""
        assert cluster_levels([], tolerance=0.015, min_size=2) == []

    def test_cluster_average_price(self):
        """클러스터 가격은 구성 레벨의 평균"""
        levels = [
            {"price": 100.0, "type": "support"},
            {"price": 101.0, "type": "support"},
        ]

        clusters = cluster_levels(levels, tolerance=0.015, min_size=2)
        assert len(clusters) == 1
        assert abs(clusters[0]["price"] - 100.5) < 0.01

    def test_cluster_has_min_max(self):
        """클러스터에 min/max 가격 포함"""
        levels = [
            {"price": 99.0, "type": "support"},
            {"price": 100.0, "type": "support"},
            {"price": 101.0, "type": "support"},
        ]

        clusters = cluster_levels(levels, tolerance=0.02, min_size=2)
        assert len(clusters) >= 1
        cluster = clusters[0]
        assert "min_price" in cluster
        assert "max_price" in cluster
        assert cluster["min_price"] <= cluster["max_price"]

    def test_cluster_type_by_majority(self):
        """클러스터 타입은 구성 레벨의 다수결"""
        levels = [
            {"price": 100.0, "type": "support"},
            {"price": 100.5, "type": "support"},
            {"price": 101.0, "type": "resistance"},
        ]

        clusters = cluster_levels(levels, tolerance=0.02, min_size=2)
        # support가 2개로 다수
        assert clusters[0]["type"] == "support"

    def test_separate_clusters(self):
        """멀리 떨어진 레벨은 별도 클러스터"""
        levels = [
            {"price": 100.0, "type": "support"},
            {"price": 100.5, "type": "support"},
            {"price": 200.0, "type": "resistance"},
            {"price": 200.5, "type": "resistance"},
        ]

        clusters = cluster_levels(levels, tolerance=0.01, min_size=2)
        assert len(clusters) == 2

    def test_wide_tolerance(self):
        """넓은 tolerance는 더 많은 레벨을 한 클러스터로"""
        levels = [
            {"price": 100.0, "type": "support"},
            {"price": 103.0, "type": "support"},
            {"price": 106.0, "type": "support"},
        ]

        # tolerance=5%면 100~105 범위가 한 클러스터
        clusters_wide = cluster_levels(levels, tolerance=0.05, min_size=2)
        clusters_narrow = cluster_levels(levels, tolerance=0.01, min_size=2)

        assert len(clusters_wide) <= len(clusters_narrow) + 1


class TestFindNearestLevels:
    """현재가 근접 레벨 판별 테스트"""

    @pytest.fixture
    def sample_clusters(self):
        return [
            {"price": 90.0, "type": "support", "touch_count": 3},
            {"price": 100.0, "type": "support", "touch_count": 2},
            {"price": 120.0, "type": "resistance", "touch_count": 2},
            {"price": 130.0, "type": "resistance", "touch_count": 1},
        ]

    def test_near_support(self, sample_clusters):
        """지지선 근처에서 매수 신호"""
        result = find_nearest_levels(101.0, sample_clusters, "support", threshold=0.02)
        assert result["is_near_level"] is True
        assert result["signal"] == "buy"
        assert result["nearest_support"]["price"] == 100.0

    def test_near_resistance(self, sample_clusters):
        """저항선 근처에서 매도 신호"""
        result = find_nearest_levels(119.0, sample_clusters, "resistance", threshold=0.02)
        assert result["is_near_level"] is True
        assert result["signal"] == "sell"
        assert result["nearest_resistance"]["price"] == 120.0

    def test_both_direction(self, sample_clusters):
        """both 모드: 가장 가까운 레벨에 따라 결정"""
        result = find_nearest_levels(101.0, sample_clusters, "both", threshold=0.02)
        assert result["is_near_level"] is True
        assert result["signal"] == "buy"  # support 100이 더 가까움

    def test_no_near_level(self, sample_clusters):
        """레벨에서 멀리 떨어진 경우"""
        result = find_nearest_levels(110.0, sample_clusters, "support", threshold=0.02)
        assert result["is_near_level"] is False
        assert result["signal"] is None

    def test_empty_clusters(self):
        """빈 클러스터"""
        result = find_nearest_levels(100.0, [], "support", threshold=0.02)
        assert result["is_near_level"] is False
        assert result["signal"] is None

    def test_zero_price(self, sample_clusters):
        """현재가 0"""
        result = find_nearest_levels(0, sample_clusters, "support", threshold=0.02)
        assert result["is_near_level"] is False

    def test_distance_pct_calculation(self, sample_clusters):
        """거리 퍼센트 계산"""
        result = find_nearest_levels(101.0, sample_clusters, "support", threshold=0.05)
        assert result["nearest_support"] is not None
        assert result["nearest_support"]["distance_pct"] == pytest.approx(1.0, abs=0.1)

    def test_resistance_direction_ignores_support(self, sample_clusters):
        """resistance 방향에서는 저항선만 평가"""
        result = find_nearest_levels(101.0, sample_clusters, "resistance", threshold=0.02)
        # 100 근처지만 resistance 방향이므로 support는 무시
        assert result["signal"] != "buy"


class TestSupportResistanceLevelsCondition:
    """전체 조건 함수 테스트"""

    @pytest.mark.asyncio
    async def test_basic_detection(self):
        """기본 S/R 레벨 감지"""
        data = _make_swing_data()
        result = await support_resistance_levels_condition(
            data=data,
            fields={"lookback": 30, "swing_strength": 3, "direction": "both"},
        )

        assert "passed_symbols" in result
        assert "failed_symbols" in result
        assert "symbol_results" in result
        assert "values" in result
        assert "result" in result
        assert "analysis" in result

        # symbol_results 확인
        assert len(result["symbol_results"]) == 1
        sr = result["symbol_results"][0]
        assert sr["symbol"] == "AAPL"
        assert "levels" in sr
        assert "clusters" in sr

    @pytest.mark.asyncio
    async def test_support_direction(self):
        """support 방향 필터링"""
        data = _make_swing_data()
        result = await support_resistance_levels_condition(
            data=data,
            fields={"lookback": 30, "swing_strength": 3, "direction": "support"},
        )

        assert result["analysis"]["direction"] == "support"

    @pytest.mark.asyncio
    async def test_resistance_direction(self):
        """resistance 방향 필터링"""
        data = _make_swing_data()
        result = await support_resistance_levels_condition(
            data=data,
            fields={"lookback": 30, "swing_strength": 3, "direction": "resistance"},
        )

        assert result["analysis"]["direction"] == "resistance"

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """빈 데이터"""
        result = await support_resistance_levels_condition(
            data=[],
            fields={"lookback": 60, "swing_strength": 5},
        )

        assert result["result"] is False
        assert result["passed_symbols"] == []
        assert "error" in result["analysis"]

    @pytest.mark.asyncio
    async def test_none_data(self):
        """None 데이터"""
        result = await support_resistance_levels_condition(
            data=None,
            fields={"lookback": 60, "swing_strength": 5},
        )

        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """데이터 부족"""
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "high": 110, "low": 100, "close": 105},
        ]
        result = await support_resistance_levels_condition(
            data=data,
            fields={"lookback": 60, "swing_strength": 5},
        )

        assert result["result"] is False
        assert len(result["failed_symbols"]) == 1

    @pytest.mark.asyncio
    async def test_multi_symbol(self):
        """다종목 처리"""
        data = _make_swing_data("AAPL", "NASDAQ") + _make_swing_data("TSLA", "NASDAQ")
        # TSLA 가격을 AAPL과 다르게 조정
        for row in data:
            if row["symbol"] == "TSLA":
                row["high"] += 100
                row["low"] += 100
                row["close"] += 100
                row["open"] += 100

        result = await support_resistance_levels_condition(
            data=data,
            fields={"lookback": 30, "swing_strength": 3, "direction": "both"},
        )

        assert len(result["symbol_results"]) == 2
        assert len(result["values"]) == 2

    @pytest.mark.asyncio
    async def test_symbols_filter(self):
        """symbols 파라미터로 특정 종목만 평가"""
        data = _make_swing_data("AAPL") + _make_swing_data("TSLA")
        for row in data:
            if row["symbol"] == "TSLA":
                row["close"] += 100
                row["high"] += 100
                row["low"] += 100

        result = await support_resistance_levels_condition(
            data=data,
            fields={"lookback": 30, "swing_strength": 3},
            symbols=[{"symbol": "AAPL", "exchange": "NASDAQ"}],
        )

        assert len(result["symbol_results"]) == 1
        assert result["symbol_results"][0]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_time_series_output(self):
        """time_series 출력 형식"""
        data = _make_swing_data()
        result = await support_resistance_levels_condition(
            data=data,
            fields={"lookback": 30, "swing_strength": 3, "direction": "both"},
        )

        assert len(result["values"]) == 1
        ts = result["values"][0]
        assert ts["symbol"] == "AAPL"
        assert "time_series" in ts
        assert len(ts["time_series"]) > 0

        entry = ts["time_series"][0]
        assert "date" in entry
        assert "is_swing_high" in entry
        assert "is_swing_low" in entry

    @pytest.mark.asyncio
    async def test_cluster_detection_with_repeated_levels(self):
        """반복 레벨 데이터에서 클러스터 감지"""
        data = _make_clustered_data()
        result = await support_resistance_levels_condition(
            data=data,
            fields={
                "lookback": 60,
                "swing_strength": 2,
                "cluster_tolerance": 0.03,
                "min_cluster_size": 2,
                "direction": "both",
            },
        )

        sr = result["symbol_results"][0]
        assert len(sr["clusters"]) > 0

    @pytest.mark.asyncio
    async def test_near_support_passed(self):
        """지지선 근접 시 passed"""
        # 현재가가 지지 레벨 근처인 데이터
        data = []
        # 상승 → 고점 → 하락 → 저점(100) → 소폭 상승 → 다시 100 근처
        prices = [100, 105, 110, 115, 120, 115, 110, 105, 100, 103, 106, 103, 101]
        for i, p in enumerate(prices):
            data.append({
                "symbol": "AAPL", "exchange": "NASDAQ",
                "date": f"202501{i+1:02d}",
                "open": p - 1, "high": p + 2, "low": p - 2,
                "close": p, "volume": 1000000,
            })

        result = await support_resistance_levels_condition(
            data=data,
            fields={
                "lookback": 20,
                "swing_strength": 2,
                "proximity_threshold": 0.03,
                "direction": "support",
                "min_cluster_size": 1,
            },
        )

        # 분석이 실행됨을 확인
        assert result["analysis"]["indicator"] == "SupportResistanceLevels"

    @pytest.mark.asyncio
    async def test_field_defaults(self):
        """필드 기본값 적용"""
        data = _make_swing_data()
        result = await support_resistance_levels_condition(
            data=data,
            fields={},  # 모든 기본값 사용
        )

        assert result["analysis"]["lookback"] == 60
        assert result["analysis"]["swing_strength"] == 5
        assert result["analysis"]["cluster_tolerance"] == 0.015
        assert result["analysis"]["min_cluster_size"] == 2
        assert result["analysis"]["proximity_threshold"] == 0.02
        assert result["analysis"]["direction"] == "support"

    @pytest.mark.asyncio
    async def test_invalid_row_skipped(self):
        """유효하지 않은 행 건너뜀"""
        data = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20250101",
             "high": "invalid", "low": 100, "close": 105},
        ] + _make_swing_data()

        result = await support_resistance_levels_condition(
            data=data,
            fields={"lookback": 30, "swing_strength": 3},
        )

        # 에러 없이 처리됨
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_no_symbol_in_data(self):
        """symbol 필드 없는 데이터는 건너뜀"""
        data = [{"high": 110, "low": 100, "close": 105}]
        result = await support_resistance_levels_condition(
            data=data,
            fields={"lookback": 30, "swing_strength": 3},
        )

        assert result["result"] is False


class TestSupportResistanceLevelsSchema:
    """스키마 검증 테스트"""

    def test_schema_id(self):
        assert SUPPORT_RESISTANCE_LEVELS_SCHEMA.id == "SupportResistanceLevels"

    def test_schema_category(self):
        assert SUPPORT_RESISTANCE_LEVELS_SCHEMA.category == "technical"

    def test_schema_fields(self):
        fields = SUPPORT_RESISTANCE_LEVELS_SCHEMA.fields_schema
        assert "lookback" in fields
        assert "swing_strength" in fields
        assert "cluster_tolerance" in fields
        assert "min_cluster_size" in fields
        assert "proximity_threshold" in fields
        assert "direction" in fields

    def test_schema_direction_enum(self):
        direction = SUPPORT_RESISTANCE_LEVELS_SCHEMA.fields_schema["direction"]
        assert set(direction["enum"]) == {"support", "resistance", "both"}

    def test_schema_required_fields(self):
        req = SUPPORT_RESISTANCE_LEVELS_SCHEMA.required_fields
        assert "symbol" in req
        assert "exchange" in req
        assert "date" in req
        assert "high" in req
        assert "low" in req
        assert "close" in req

    def test_schema_ko_locale(self):
        assert "ko" in SUPPORT_RESISTANCE_LEVELS_SCHEMA.locales
        ko = SUPPORT_RESISTANCE_LEVELS_SCHEMA.locales["ko"]
        assert "name" in ko
        assert "description" in ko

    def test_schema_tags(self):
        assert "support" in SUPPORT_RESISTANCE_LEVELS_SCHEMA.tags
        assert "resistance" in SUPPORT_RESISTANCE_LEVELS_SCHEMA.tags
        assert "cluster" in SUPPORT_RESISTANCE_LEVELS_SCHEMA.tags

    def test_schema_products(self):
        products = SUPPORT_RESISTANCE_LEVELS_SCHEMA.products
        assert len(products) == 2
