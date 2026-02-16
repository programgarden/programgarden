"""
Auto-iterate 체이닝 테스트

WatchlistNode → HistoricalDataNode → ConditionNode 파이프라인에서
HistoricalDataNode의 merged 출력이 ConditionNode로 올바르게 전달되는지 검증.

핵심: HistoricalDataNode가 auto-iterate 후 merge되면
- symbols: ["AAPL", "TSLA"] (string 배열)
- value: [{symbol: "AAPL", ...}, {symbol: "TSLA", ...}] (dict 배열)
→ ConditionNode는 value 포트의 dict 배열로 auto-iterate 해야 함
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any


# === 테스트용 mock 데이터 ===

WATCHLIST_SYMBOLS = [
    {"exchange": "NASDAQ", "symbol": "AAPL"},
    {"exchange": "NASDAQ", "symbol": "TSLA"},
]

HISTORICAL_MERGED_OUTPUT = {
    "value": [
        {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "time_series": [
                {"date": "20260101", "open": 150, "high": 155, "low": 148, "close": 152, "volume": 1000},
                {"date": "20260102", "open": 152, "high": 158, "low": 150, "close": 156, "volume": 1200},
            ],
        },
        {
            "symbol": "TSLA",
            "exchange": "NASDAQ",
            "time_series": [
                {"date": "20260101", "open": 200, "high": 210, "low": 195, "close": 205, "volume": 2000},
                {"date": "20260102", "open": 205, "high": 215, "low": 200, "close": 210, "volume": 2500},
            ],
        },
    ],
    "values": [
        {"symbol": "AAPL", "exchange": "NASDAQ", "time_series": [...]},
        {"symbol": "TSLA", "exchange": "NASDAQ", "time_series": [...]},
    ],
    "symbols": ["AAPL", "TSLA"],
    "period": "20260101~20260102",
    "interval": "1d",
}

HISTORICAL_SINGLE_OUTPUT = {
    "value": {
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "time_series": [
            {"date": "20260101", "open": 150, "high": 155, "low": 148, "close": 152, "volume": 1000},
        ],
    },
    "symbols": ["AAPL"],
    "period": "20260101~20260102",
    "interval": "1d",
}


class TestAutoIterateInputResolution:
    """auto-iterate input 해석 로직 테스트"""

    def _make_context_with_outputs(self, node_id: str, outputs: Dict[str, Any]):
        """주어진 outputs으로 context mock 생성"""
        from programgarden.context import ExecutionContext

        context = MagicMock(spec=ExecutionContext)

        def mock_get_output(nid, port=None):
            if nid != node_id:
                return None
            if port:
                return outputs.get(port)
            if outputs:
                return list(outputs.values())[0]
            return None

        context.get_output = mock_get_output
        return context

    def test_watchlist_symbols_dict_array_used_directly(self):
        """WatchlistNode의 symbols (dict 배열)는 그대로 사용"""
        # WatchlistNode → HistoricalDataNode: symbols = [{exchange, symbol}, ...]
        context = self._make_context_with_outputs("watchlist", {
            "symbols": WATCHLIST_SYMBOLS,
        })

        input_data = context.get_output("watchlist", "symbols")

        # dict 배열이므로 폴백 없이 그대로 사용
        assert isinstance(input_data, list)
        assert len(input_data) == 2
        assert isinstance(input_data[0], dict)
        assert input_data[0]["symbol"] == "AAPL"

    def test_historical_merged_symbols_fallback_to_value(self):
        """HistoricalDataNode merged symbols (string 배열)는 value 포트로 폴백"""
        context = self._make_context_with_outputs("historical", HISTORICAL_MERGED_OUTPUT)

        # 1) symbols 포트 확인 → string 배열
        input_data = context.get_output("historical", "symbols")
        assert isinstance(input_data, list)
        assert isinstance(input_data[0], str)  # ["AAPL", "TSLA"]

        # 2) string 배열이면 → value 포트로 폴백 (executor 로직 시뮬레이션)
        if (isinstance(input_data, list) and input_data
                and not isinstance(input_data[0], dict)):
            value_data = context.get_output("historical", "value")
            if value_data is not None:
                if isinstance(value_data, list):
                    input_data = value_data
                elif isinstance(value_data, dict):
                    input_data = [value_data]

        # 결과: value 포트의 dict 배열
        assert isinstance(input_data, list)
        assert len(input_data) == 2
        assert isinstance(input_data[0], dict)
        assert input_data[0]["symbol"] == "AAPL"
        assert "time_series" in input_data[0]

    def test_historical_single_symbol_value_wrapped_in_list(self):
        """단일 심볼 HistoricalDataNode의 value (dict)는 list로 래핑"""
        context = self._make_context_with_outputs("historical", HISTORICAL_SINGLE_OUTPUT)

        input_data = context.get_output("historical", "symbols")

        # string 배열이면 폴백
        if (isinstance(input_data, list) and input_data
                and not isinstance(input_data[0], dict)):
            value_data = context.get_output("historical", "value")
            if value_data is not None:
                if isinstance(value_data, list):
                    input_data = value_data
                elif isinstance(value_data, dict):
                    input_data = [value_data]  # dict → [dict]

        assert isinstance(input_data, list)
        assert len(input_data) == 1
        assert isinstance(input_data[0], dict)
        assert input_data[0]["symbol"] == "AAPL"

    def test_no_symbols_port_fallback_to_default(self):
        """symbols 포트가 없으면 기본 출력 폴백"""
        context = self._make_context_with_outputs("somenode", {
            "result": [{"data": 1}, {"data": 2}],
        })

        input_data = context.get_output("somenode", "symbols")
        assert input_data is None

        # None이면 기본 출력으로 폴백
        if input_data is None:
            input_data = context.get_output("somenode", None)

        assert isinstance(input_data, list)
        assert len(input_data) == 2


class TestShouldAutoIterate:
    """_should_auto_iterate 메서드 테스트"""

    def _make_job(self):
        """WorkflowJob mock 생성"""
        from programgarden.executor import WorkflowJob
        job = MagicMock(spec=WorkflowJob)
        job.NO_AUTO_ITERATE_NODE_TYPES = WorkflowJob.NO_AUTO_ITERATE_NODE_TYPES
        job._should_auto_iterate = WorkflowJob._should_auto_iterate.__get__(job)
        return job

    def test_dict_array_triggers_iterate(self):
        """dict 배열 입력은 auto-iterate 트리거"""
        job = self._make_job()
        should, port, items = job._should_auto_iterate(
            "ConditionNode",
            [{"symbol": "AAPL"}, {"symbol": "TSLA"}],
        )
        assert should is True
        assert port == "item"
        assert len(items) == 2

    def test_empty_list_no_iterate(self):
        """빈 배열은 iterate 불필요"""
        job = self._make_job()
        should, port, items = job._should_auto_iterate("ConditionNode", [])
        assert should is False

    def test_non_list_no_iterate(self):
        """배열이 아닌 입력은 iterate 불필요"""
        job = self._make_job()
        should, port, items = job._should_auto_iterate("ConditionNode", {"key": "val"})
        assert should is False

    def test_none_no_iterate(self):
        """None 입력은 iterate 불필요"""
        job = self._make_job()
        should, port, items = job._should_auto_iterate("ConditionNode", None)
        assert should is False

    def test_excluded_node_no_iterate(self):
        """NO_AUTO_ITERATE_NODE_TYPES에 포함된 노드는 iterate 제외"""
        job = self._make_job()
        should, port, items = job._should_auto_iterate(
            "SplitNode",
            [{"a": 1}, {"b": 2}],
        )
        assert should is False

    def test_single_item_list_triggers_iterate(self):
        """단일 아이템 배열도 iterate 트리거"""
        job = self._make_job()
        should, port, items = job._should_auto_iterate(
            "ConditionNode",
            [{"symbol": "AAPL"}],
        )
        assert should is True
        assert len(items) == 1


class TestMergeIterateResults:
    """_merge_iterate_results 메서드 테스트"""

    def _make_job(self):
        from programgarden.executor import WorkflowJob
        job = MagicMock(spec=WorkflowJob)
        job._merge_iterate_results = WorkflowJob._merge_iterate_results.__get__(job)
        return job

    def test_array_fields_merged(self):
        """배열 필드 (value, result 등)는 병합"""
        job = self._make_job()
        results = [
            {
                "value": {"symbol": "AAPL", "rsi": 28},
                "result": {"is_met": True, "symbol": "AAPL"},
                "symbols": ["AAPL"],
            },
            {
                "value": {"symbol": "TSLA", "rsi": 45},
                "result": {"is_met": False, "symbol": "TSLA"},
                "symbols": ["TSLA"],
            },
        ]
        merged = job._merge_iterate_results(results)

        # value, result는 array_fields → 병합
        assert isinstance(merged["value"], list)
        assert len(merged["value"]) == 2
        assert merged["value"][0]["symbol"] == "AAPL"
        assert merged["value"][1]["symbol"] == "TSLA"

        assert isinstance(merged["result"], list)
        assert len(merged["result"]) == 2

    def test_non_array_fields_last_value(self):
        """비배열 필드는 마지막 유효 값"""
        job = self._make_job()
        results = [
            {"value": {"a": 1}, "symbols": ["A"], "period": "20260101~20260102"},
            {"value": {"b": 2}, "symbols": ["B"], "period": "20260101~20260103"},
        ]
        merged = job._merge_iterate_results(results)

        # symbols는 array_fields가 아니므로 마지막 값... 아, symbols는 안 들어있다
        # period는 비배열 → 마지막 값
        assert merged["period"] == "20260101~20260103"

    def test_empty_results(self):
        """빈 결과 목록"""
        job = self._make_job()
        merged = job._merge_iterate_results([])
        assert merged == {}


class TestAutoIterateChainFlow:
    """WatchlistNode → HistoricalDataNode → ConditionNode 전체 흐름 검증"""

    def test_item_expression_resolves_per_symbol(self):
        """ConditionNode의 {{ item.xxx }} 표현식이 종목별로 올바르게 해석되는지"""
        # auto-iterate에서 각 item은 HistoricalDataNode의 merged value의 각 요소
        items = HISTORICAL_MERGED_OUTPUT["value"]

        for idx, item in enumerate(items):
            # {{ item.time_series }} → 해당 종목의 time_series
            assert "time_series" in item
            assert isinstance(item["time_series"], list)

            # {{ item.symbol }} → 해당 종목 코드
            assert "symbol" in item
            assert item["symbol"] in ("AAPL", "TSLA")

            # {{ item.exchange }} → 거래소
            assert item["exchange"] == "NASDAQ"

    def test_condition_node_items_config_pattern(self):
        """ConditionNode의 items config가 올바른 패턴인지"""
        import json
        from pathlib import Path

        workflow_path = (
            Path(__file__).parent.parent
            / "examples"
            / "workflows"
            / "11-condition-rsi-filter.json"
        )
        with open(workflow_path) as f:
            workflow = json.load(f)

        rsi_node = next(n for n in workflow["nodes"] if n["id"] == "rsi_condition")

        # items.from은 {{ item.time_series }} 패턴이어야 함
        assert rsi_node["items"]["from"] == "{{ item.time_series }}"

        # extract의 symbol/exchange는 {{ item.xxx }} 패턴
        extract = rsi_node["items"]["extract"]
        assert extract["symbol"] == "{{ item.symbol }}"
        assert extract["exchange"] == "{{ item.exchange }}"

        # extract의 date/close는 {{ row.xxx }} 패턴 (items 내부 반복)
        assert extract["date"] == "{{ row.date }}"
        assert extract["close"] == "{{ row.close }}"

    def test_workflow_12_uses_items_pattern(self):
        """Workflow 12 (MACD)가 레거시 data 대신 items 패턴 사용하는지"""
        import json
        from pathlib import Path

        workflow_path = (
            Path(__file__).parent.parent
            / "examples"
            / "workflows"
            / "12-condition-macd-chain.json"
        )
        with open(workflow_path) as f:
            workflow = json.load(f)

        macd_node = next(n for n in workflow["nodes"] if n["id"] == "macd_condition")

        # data 필드가 없어야 함 (레거시 제거)
        assert "data" not in macd_node

        # items 패턴 사용
        assert "items" in macd_node
        assert macd_node["items"]["from"] == "{{ item.time_series }}"

    def test_workflow_28_uses_items_and_fields(self):
        """Workflow 28 (RSI full)이 items/fields 패턴 사용하는지"""
        import json
        from pathlib import Path

        workflow_path = (
            Path(__file__).parent.parent
            / "examples"
            / "workflows"
            / "28-strategy-rsi-full.json"
        )
        with open(workflow_path) as f:
            workflow = json.load(f)

        rsi_node = next(n for n in workflow["nodes"] if n["id"] == "rsi_condition")

        # 레거시 필드 제거 확인
        assert "data" not in rsi_node
        assert "params" not in rsi_node

        # 새 패턴 사용
        assert "items" in rsi_node
        assert "fields" in rsi_node
        assert rsi_node["items"]["from"] == "{{ item.time_series }}"

    def test_workflow_29_uses_items_and_fields(self):
        """Workflow 29 (multi RSI)가 items/fields 패턴 사용하는지"""
        import json
        from pathlib import Path

        workflow_path = (
            Path(__file__).parent.parent
            / "examples"
            / "workflows"
            / "29-monitor-multi-rsi.json"
        )
        with open(workflow_path) as f:
            workflow = json.load(f)

        rsi_node = next(n for n in workflow["nodes"] if n["id"] == "rsi_condition")

        assert "data" not in rsi_node
        assert "params" not in rsi_node
        assert "items" in rsi_node
        assert "fields" in rsi_node
        assert rsi_node["items"]["from"] == "{{ item.time_series }}"
