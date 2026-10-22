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

    # corpus 패턴 검사 4건(예제 11/12/28/29 items/fields 규약)은 corpus 와 함께
    # programgarden_ai/tests/test_workflow_examples_corpus.py 로 이관 (2026-08-07 비공개화).



# ===========================================================================
# HTTPRequestNode 종목별 반복 (오너 결정 2026-09-28)
# ===========================================================================
#
# HTTP 노드는 config 가 {{ item… }}/{{ index }}/{{ total }} 을 참조할 때만 상류
# 목록의 항목마다 1회씩 실행되고(예: 종목별 외부 시세 조회), 참조가 없으면 오늘처럼
# 1회만 실행된다(조건 → webhook POST 알림 예제는 N 번 발화하면 안 된다 — 하위 호환).
# 반복 결과는 `results` 배열 포트로 노출되고, response/status_code/success/error 는
# 마지막 항목 값을 유지한다.

import asyncio as _asyncio
import time as _time
from unittest.mock import patch as _patch


class _HTTPMockContext:
    """HTTP 반복 실행 테스트용 최소 ExecutionContext (dry_run pacing 테스트와 동형)."""

    def __init__(self, *, dry_run: bool = False, deep_validate: bool = False):
        self._node_states: Dict[str, Any] = {}
        self.is_running = True
        self.is_dry_run = dry_run or deep_validate
        self.is_deep_validate = deep_validate
        self.logs: list = []
        self._iteration_item: Any = None
        self._iteration_index: int = 0
        self._iteration_total: int = 0

    def get_node_state(self, node_id, key):
        return self._node_states.get(f"{node_id}:{key}")

    def set_node_state(self, node_id, key, value):
        self._node_states[f"{node_id}:{key}"] = value

    def log(self, level, message, node_id=None):
        self.logs.append({"level": level, "message": message, "node_id": node_id})

    def get_output(self, node_id, port=None):
        return None

    def set_output(self, node_id, port_name, value):
        pass

    def get_all_outputs(self, node_id):
        return {}

    def set_iteration_context(self, item, idx, total):
        self._iteration_item, self._iteration_index, self._iteration_total = item, idx, total

    def clear_iteration_context(self):
        self._iteration_item, self._iteration_index, self._iteration_total = None, 0, 0

    def get_expression_context(self):
        from programgarden.context import ExpressionContext
        ctx = ExpressionContext.__new__(ExpressionContext)
        ctx.node_outputs = {}
        ctx.context_params = {}
        ctx.iteration_item = self._iteration_item
        ctx.iteration_index = self._iteration_index
        ctx.iteration_total = self._iteration_total
        return ctx


class _ScriptedHTTPExecutor:
    """execute_node 가 호출 순서대로 미리 정한 결과를 돌려주거나(예외면 raise) 한다."""

    def __init__(self, outcomes: list):
        self.outcomes = outcomes
        self.calls = 0

    async def execute_node(self, **kwargs):
        i = self.calls
        self.calls += 1
        outcome = self.outcomes[i]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _HTTPNode:
    def __init__(self):
        self.node_type = "HTTPRequestNode"
        self.plugin = None
        self.fields = {}


def _http_job(outcomes, ctx=None):
    from programgarden.executor import WorkflowJob
    job = object.__new__(WorkflowJob)
    job.context = ctx or _HTTPMockContext()
    job.executor = _ScriptedHTTPExecutor(outcomes)
    job.workflow = object()
    return job


_THREE_SYMBOLS = [
    {"symbol": "AAPL", "exchange": "NASDAQ"},
    {"symbol": "TSLA", "exchange": "NASDAQ"},
    {"symbol": "NVDA", "exchange": "NASDAQ"},
]

# 반복을 즉시 끝내려고 rate_limit_interval=0 으로 pacing sleep 을 끈다(간격은 (e)에서 별도 검증).
_NO_PACE = {"url": "https://api.example.com/quote", "rate_limit_interval": 0}


def _ok(symbol, price):
    return {"response": {"symbol": symbol, "price": price}, "status_code": 200, "success": True, "error": None}


class TestHTTPConditionalIterate:
    """_should_auto_iterate: HTTP 는 config 가 아이템 바인딩을 참조할 때만 반복."""

    def _make_job(self):
        from programgarden.executor import WorkflowJob
        job = MagicMock(spec=WorkflowJob)
        job.NO_AUTO_ITERATE_NODE_TYPES = WorkflowJob.NO_AUTO_ITERATE_NODE_TYPES
        job.WHOLE_ARRAY_INPUT_PORTS = WorkflowJob.WHOLE_ARRAY_INPUT_PORTS
        job._references_iteration_item = WorkflowJob._references_iteration_item
        job._consumes_whole_array = WorkflowJob._consumes_whole_array.__get__(job)
        job._should_auto_iterate = WorkflowJob._should_auto_iterate.__get__(job)
        return job

    def test_http_iterates_when_url_references_item(self):
        job = self._make_job()
        should, port, items = job._should_auto_iterate(
            "HTTPRequestNode", _THREE_SYMBOLS,
            {"method": "GET", "url": "https://fmp.example/quote/{{ item.symbol }}"},
        )
        assert should is True
        assert port == "item"
        assert len(items) == 3

    def test_http_iterates_when_nested_body_references_item(self):
        job = self._make_job()
        should, _, items = job._should_auto_iterate(
            "HTTPRequestNode", _THREE_SYMBOLS,
            {"method": "POST", "url": "https://x", "body": {"ticker": "{{ item.symbol }}"}},
        )
        assert should is True and len(items) == 3

    def test_http_iterates_on_index_reference(self):
        job = self._make_job()
        should, _, _ = job._should_auto_iterate(
            "HTTPRequestNode", _THREE_SYMBOLS,
            {"url": "https://x?page={{ index }}"},
        )
        assert should is True

    def test_http_no_iterate_without_item_reference_webhook(self):
        """조건 → webhook POST 예제: 아이템 참조 없음 → 1회 실행(반복 안 함)."""
        job = self._make_job()
        should, port, items = job._should_auto_iterate(
            "HTTPRequestNode", _THREE_SYMBOLS,
            {"method": "POST", "url": "https://hooks.slack.com/services/X",
             "body": {"text": "Buy signal for {{ nodes.condition.passed_symbols }}"}},
        )
        assert should is False
        assert items == []

    def test_http_no_iterate_when_config_none(self):
        """레거시 호출(config=None) → 아이템 참조 판정 불가 → 반복 안 함(안전 기본값)."""
        job = self._make_job()
        should, _, _ = job._should_auto_iterate("HTTPRequestNode", _THREE_SYMBOLS)
        assert should is False


class TestHTTPIterateResultsMerge:
    """_execute_with_auto_iterate + _merge_http_iterate_results 결과 형태."""

    @pytest.mark.asyncio
    async def test_a_all_success_results_ordered_and_response_last(self):
        outcomes = [_ok("AAPL", 189), _ok("TSLA", 250), _ok("NVDA", 900)]
        job = _http_job(outcomes)
        merged = await job._execute_with_auto_iterate(
            node_id="http", node=_HTTPNode(), config=dict(_NO_PACE),
            items=list(_THREE_SYMBOLS), port_name="item",
        )
        assert job.executor.calls == 3
        assert len(merged["results"]) == 3
        assert [r["item"]["symbol"] for r in merged["results"]] == ["AAPL", "TSLA", "NVDA"]
        assert [r["response"]["symbol"] for r in merged["results"]] == ["AAPL", "TSLA", "NVDA"]
        assert all(r["success"] for r in merged["results"])
        # response(첫 포트)는 마지막 항목 값 — {{ nodes.http.response }} 호환
        assert merged["response"] == {"symbol": "NVDA", "price": 900}
        assert merged["status_code"] == 200
        assert merged["success"] is True
        assert merged["error"] == ""

    @pytest.mark.asyncio
    async def test_b_single_execution_when_no_iteration(self):
        """아이템 참조가 없으면 실행 경로는 1회 실행(_should_auto_iterate=False).

        webhook POST 예제가 종목 수만큼 발화하지 않음을 결정 단계에서 확인."""
        from programgarden.executor import WorkflowJob
        job = MagicMock(spec=WorkflowJob)
        job.NO_AUTO_ITERATE_NODE_TYPES = WorkflowJob.NO_AUTO_ITERATE_NODE_TYPES
        job.WHOLE_ARRAY_INPUT_PORTS = WorkflowJob.WHOLE_ARRAY_INPUT_PORTS
        job._references_iteration_item = WorkflowJob._references_iteration_item
        job._consumes_whole_array = WorkflowJob._consumes_whole_array.__get__(job)
        job._should_auto_iterate = WorkflowJob._should_auto_iterate.__get__(job)
        should, _, _ = job._should_auto_iterate(
            "HTTPRequestNode", _THREE_SYMBOLS,
            {"method": "POST", "url": "https://hooks.slack.com/services/X",
             "body": {"text": "alert"}},
        )
        assert should is False

    @pytest.mark.asyncio
    async def test_c_first_item_errors_others_succeed(self):
        outcomes = [RuntimeError("boom"), _ok("TSLA", 250), _ok("NVDA", 900)]
        job = _http_job(outcomes)
        merged = await job._execute_with_auto_iterate(
            node_id="http", node=_HTTPNode(), config=dict(_NO_PACE),
            items=list(_THREE_SYMBOLS), port_name="item",
        )
        assert job.executor.calls == 3
        # 첫 항목 오류에도 3건 전부 results 에 순서대로 남는다(results[0] 키만 뽑는 결함 회귀 방지)
        assert len(merged["results"]) == 3
        assert [r["item"]["symbol"] for r in merged["results"]] == ["AAPL", "TSLA", "NVDA"]
        assert merged["results"][0]["success"] is False
        assert merged["results"][0]["error"] == "boom"
        assert merged["results"][0]["response"] is None
        assert merged["results"][1]["success"] is True
        assert merged["results"][2]["success"] is True
        # 최상위: 일부 성공 → error 비움, success 는 AND(False), response 는 마지막 성공 값
        assert merged["error"] == ""
        assert merged["success"] is False
        assert merged["response"] == {"symbol": "NVDA", "price": 900}

    @pytest.mark.asyncio
    async def test_d_all_fail_sets_top_level_error(self):
        # 전 항목 4xx(명시 success=False + error 문자열)
        outcomes = [
            {"response": {"m": "nf"}, "status_code": 404, "success": False, "error": "HTTP 404"},
            {"response": {"m": "nf"}, "status_code": 404, "success": False, "error": "HTTP 404"},
            {"response": {"m": "nf"}, "status_code": 404, "success": False, "error": "HTTP 404"},
        ]
        job = _http_job(outcomes)
        merged = await job._execute_with_auto_iterate(
            node_id="http", node=_HTTPNode(), config=dict(_NO_PACE),
            items=list(_THREE_SYMBOLS), port_name="item",
        )
        assert len(merged["results"]) == 3
        assert all(r["success"] is False for r in merged["results"])
        assert merged["success"] is False
        # 전부 실패 → 최상위 error 채움(재생 bool(error) 규칙에서 실패로 읽힌다)
        assert merged["error"] == "HTTP 404"

    @pytest.mark.asyncio
    async def test_d2_all_fail_via_exceptions(self):
        outcomes = [RuntimeError("e1"), RuntimeError("e2"), RuntimeError("e3")]
        job = _http_job(outcomes)
        merged = await job._execute_with_auto_iterate(
            node_id="http", node=_HTTPNode(), config=dict(_NO_PACE),
            items=list(_THREE_SYMBOLS), port_name="item",
        )
        assert len(merged["results"]) == 3
        assert merged["success"] is False
        assert merged["error"]  # non-empty (대표 사유)
        assert merged["error"] == "e1"


class TestHTTPIterateRateLimitInterval:
    """(e) per-item 간격이 사용자 config 의 rate_limit_interval 을 반영한다(min 1s 기본 유지)."""

    @pytest.mark.asyncio
    async def test_config_rate_limit_interval_honoured(self):
        outcomes = [_ok("AAPL", 1), _ok("TSLA", 2), _ok("NVDA", 3)]
        job = _http_job(outcomes)
        slept = []

        async def _fake_sleep(sec):
            slept.append(sec)

        with _patch("programgarden.executor.asyncio.sleep", new=_fake_sleep):
            await job._execute_with_auto_iterate(
                node_id="http", node=_HTTPNode(),
                config={"url": "https://x/{{ item.symbol }}", "rate_limit_interval": 0.2},
                items=list(_THREE_SYMBOLS), port_name="item",
            )
        assert job.executor.calls == 3
        # 첫 항목은 대기 없음 → 나머지 2번만 sleep, 값은 config 의 0.2 (ClassVar 기본 1초가 아님)
        assert len(slept) == 2, slept
        assert all(0.15 <= s <= 0.25 for s in slept), slept

    @pytest.mark.asyncio
    async def test_default_interval_stays_one_second_without_config(self):
        outcomes = [_ok("AAPL", 1), _ok("TSLA", 2), _ok("NVDA", 3)]
        job = _http_job(outcomes)
        slept = []

        async def _fake_sleep(sec):
            slept.append(sec)

        with _patch("programgarden.executor.asyncio.sleep", new=_fake_sleep):
            await job._execute_with_auto_iterate(
                node_id="http", node=_HTTPNode(),
                config={"url": "https://x/{{ item.symbol }}"},  # rate_limit_interval 없음
                items=list(_THREE_SYMBOLS), port_name="item",
            )
        assert job.executor.calls == 3
        assert len(slept) == 2, slept
        # HTTPRequestNode._rate_limit.min_interval_sec = 1 (클래스 기본) 유지
        assert all(0.9 <= s <= 1.1 for s in slept), slept
