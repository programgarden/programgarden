"""
외부 시장 데이터 노드 Executor 디스패치 + 워크플로우 통합 테스트

테스트 대상:
1. GenericNodeExecutor 매핑 확인 (CurrencyRateNode, FearGreedIndexNode, VIXDataNode)
2. GenericNodeExecutor를 통한 실제 실행 로직 (mock API)
3. 워크플로우 JSON 통합 테스트 (StartNode → 외부 노드 → 검증)

실행:
    cd src/programgarden && poetry run pytest tests/test_market_external_executor.py -v
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from programgarden.executor import WorkflowExecutor, GenericNodeExecutor


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_async_response(*, json_data=None, text_data=None, status=200):
    """aiohttp 응답 mock (async context manager 지원)"""
    resp = MagicMock()
    resp.status = status
    if json_data is not None:
        resp.json = AsyncMock(return_value=json_data)
    if text_data is not None:
        resp.text = AsyncMock(return_value=text_data)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _make_async_session(response):
    """aiohttp.ClientSession mock"""
    session = MagicMock()
    session.get = MagicMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


def _make_url_routing_session(routes: Dict[str, MagicMock]):
    """URL 패턴 → 응답 라우팅 session"""
    session = MagicMock()

    def mock_get(url, **kwargs):
        for pattern, resp in routes.items():
            if pattern in url:
                return resp
        return _make_async_response(json_data={"error": "not found"}, status=404)

    session.get = mock_get
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


# Yahoo Finance chart API 응답 형식
def _yahoo_vix_response(price: float):
    return {
        "chart": {
            "result": [{
                "meta": {"regularMarketPrice": price, "symbol": "^VIX"},
                "timestamp": [1740000000],
                "indicators": {
                    "quote": [{"close": [price], "open": [price - 0.5], "high": [price + 0.3], "low": [price - 1.0]}]
                },
            }]
        }
    }


# ---------------------------------------------------------------------------
# Part 1: Executor 디스패치 테스트
# ---------------------------------------------------------------------------


class TestMarketExternalExecutorRegistration:
    """외부 시장 데이터 노드가 executor 맵에 등록되어 있는지 검증"""

    @pytest.fixture
    def executors(self):
        we = WorkflowExecutor()
        return we._executors

    def test_currency_rate_node_registered(self, executors):
        """CurrencyRateNode가 executor 맵에 등록"""
        assert "CurrencyRateNode" in executors

    def test_fear_greed_node_registered(self, executors):
        """FearGreedIndexNode가 executor 맵에 등록"""
        assert "FearGreedIndexNode" in executors

    def test_vix_node_registered(self, executors):
        """VIXDataNode가 executor 맵에 등록"""
        assert "VIXDataNode" in executors

    def test_currency_rate_is_generic_executor(self, executors):
        """CurrencyRateNode → GenericNodeExecutor 인스턴스"""
        assert isinstance(executors["CurrencyRateNode"], GenericNodeExecutor)

    def test_fear_greed_is_generic_executor(self, executors):
        """FearGreedIndexNode → GenericNodeExecutor 인스턴스"""
        assert isinstance(executors["FearGreedIndexNode"], GenericNodeExecutor)

    def test_vix_is_generic_executor(self, executors):
        """VIXDataNode → GenericNodeExecutor 인스턴스"""
        assert isinstance(executors["VIXDataNode"], GenericNodeExecutor)


class TestMarketExternalExecutorDispatch:
    """GenericNodeExecutor를 통한 외부 노드 실행 검증 (mock API)"""

    @pytest.fixture
    def mock_context(self):
        ctx = MagicMock()
        ctx.log = MagicMock()
        expr_ctx = MagicMock()
        expr_ctx.to_dict = MagicMock(return_value={"nodes": {}})
        ctx.get_expression_context = MagicMock(return_value=expr_ctx)
        ctx.get_all_outputs = MagicMock(return_value={})
        ctx.credential_store = []
        return ctx

    @pytest.mark.asyncio
    async def test_currency_rate_dispatch(self, mock_context):
        """GenericNodeExecutor → CurrencyRateNode.execute() 호출 검증"""
        executor = GenericNodeExecutor()
        session = _make_async_session(_make_async_response(json_data={
            "base": "USD",
            "rates": {"KRW": 1350.5, "EUR": 0.92, "JPY": 149.3},
        }))

        with patch("aiohttp.ClientSession", return_value=session):
            result = await executor.execute(
                node_id="currency1",
                node_type="CurrencyRateNode",
                config={
                    "type": "CurrencyRateNode",
                    "base_currency": "USD",
                    "target_currencies": ["KRW", "EUR", "JPY"],
                },
                context=mock_context,
            )

        assert "rates" in result
        assert result["krw_rate"] == 1350.5
        assert len(result["rates"]) == 3

    @pytest.mark.asyncio
    async def test_fear_greed_dispatch(self, mock_context):
        """GenericNodeExecutor → FearGreedIndexNode.execute() 호출 검증"""
        executor = GenericNodeExecutor()
        session = _make_async_session(_make_async_response(json_data={
            "fear_and_greed": {"score": 25, "rating": "Fear"},
        }))

        with patch("aiohttp.ClientSession", return_value=session):
            result = await executor.execute(
                node_id="fg1",
                node_type="FearGreedIndexNode",
                config={"type": "FearGreedIndexNode"},
                context=mock_context,
            )

        assert result["value"] == 25
        assert result["label"] == "Fear"

    @pytest.mark.asyncio
    async def test_vix_dispatch(self, mock_context):
        """GenericNodeExecutor → VIXDataNode.execute() 호출 검증"""
        executor = GenericNodeExecutor()
        session = _make_async_session(_make_async_response(
            json_data=_yahoo_vix_response(12.5),  # < 15 → "low"
        ))

        with patch("aiohttp.ClientSession", return_value=session):
            result = await executor.execute(
                node_id="vix1",
                node_type="VIXDataNode",
                config={"type": "VIXDataNode", "include_history": False},
                context=mock_context,
            )

        assert result["vix"] == 12.5
        assert result["level"] == "low"


# ---------------------------------------------------------------------------
# Part 2: 워크플로우 JSON 통합 테스트
# ---------------------------------------------------------------------------


class _WorkflowTracker:
    """워크플로우 노드 상태/출력 추적"""

    def __init__(self):
        self.completed = []
        self.outputs = {}

    async def on_node_state_change(self, event):
        state = event.state.value if hasattr(event.state, "value") else str(event.state)
        if state == "completed":
            self.completed.append(event.node_id)
            if event.outputs:
                self.outputs[event.node_id] = event.outputs

    async def on_edge_state_change(self, event): pass
    async def on_log(self, event): pass
    async def on_job_state_change(self, event): pass
    async def on_display_data(self, event): pass


class TestMarketExternalWorkflow:
    """외부 시장 데이터 노드 워크플로우 통합 테스트"""

    @pytest.mark.asyncio
    async def test_currency_rate_workflow(self):
        """환율 워크플로우: StartNode → CurrencyRateNode 실행 + 출력 검증"""
        workflow = {
            "id": "test-currency-rate",
            "name": "환율 조회 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "currency",
                    "type": "CurrencyRateNode",
                    "base_currency": "USD",
                    "target_currencies": ["KRW", "JPY"],
                },
            ],
            "edges": [
                {"from": "start", "to": "currency"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()

        session = _make_url_routing_session({
            "frankfurter.app": _make_async_response(json_data={
                "base": "USD",
                "date": "2026-02-23",
                "rates": {"KRW": 1350.5, "JPY": 149.3},
            }),
        })

        with patch("aiohttp.ClientSession", return_value=session):
            job = await executor.execute(workflow, listeners=[tracker])
            await asyncio.wait_for(job._task, timeout=10)

        assert "currency" in tracker.completed

        output = job.context.get_all_outputs("currency")
        assert output["krw_rate"] == 1350.5
        assert len(output["rates"]) == 2
        assert output["rates"][0]["base"] == "USD"

    @pytest.mark.asyncio
    async def test_fear_greed_if_branch_workflow(self):
        """공포/탐욕 → IfNode 분기: score 20 <= 25 → true 브랜치 활성화"""
        workflow = {
            "id": "test-fear-greed-if",
            "name": "공포/탐욕 IfNode 분기 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "fg", "type": "FearGreedIndexNode"},
                {
                    "id": "check",
                    "type": "IfNode",
                    "left": "{{ nodes.fg.value }}",
                    "operator": "<=",
                    "right": 25,
                },
                {
                    "id": "buy-signal",
                    "type": "FieldMappingNode",
                    "mapping": {"action": "buy"},
                },
                {
                    "id": "hold-signal",
                    "type": "FieldMappingNode",
                    "mapping": {"action": "hold"},
                },
            ],
            "edges": [
                {"from": "start", "to": "fg"},
                {"from": "fg", "to": "check"},
                {"from": "check", "to": "buy-signal", "from_port": "true"},
                {"from": "check", "to": "hold-signal", "from_port": "false"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()

        session = _make_url_routing_session({
            "dataviz.cnn.io": _make_async_response(json_data={
                "fear_and_greed": {"score": 20, "rating": "Extreme Fear"},
            }),
        })

        with patch("aiohttp.ClientSession", return_value=session):
            job = await executor.execute(workflow, listeners=[tracker])
            await asyncio.wait_for(job._task, timeout=10)

        # FearGreedIndexNode 출력 검증
        fg_output = job.context.get_all_outputs("fg")
        assert fg_output["value"] == 20
        assert fg_output["label"] == "Extreme Fear"

        # IfNode true 브랜치 (score 20 <= 25)
        check_output = job.context.get_all_outputs("check")
        assert check_output["result"] is True

        # buy-signal 실행됨 (true 브랜치), hold-signal 스킵됨 (false 브랜치)
        assert "buy-signal" in tracker.completed
        assert "hold-signal" in tracker.completed  # 스킵도 COMPLETED로 emit

    @pytest.mark.asyncio
    async def test_vix_workflow(self):
        """VIX 워크플로우: StartNode → VIXDataNode 실행 + 출력 검증"""
        workflow = {
            "id": "test-vix-data",
            "name": "VIX 조회 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "vix",
                    "type": "VIXDataNode",
                    "include_history": False,
                },
            ],
            "edges": [
                {"from": "start", "to": "vix"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()

        session = _make_url_routing_session({
            "yahoo": _make_async_response(json_data=_yahoo_vix_response(28.9)),
        })

        with patch("aiohttp.ClientSession", return_value=session):
            job = await executor.execute(workflow, listeners=[tracker])
            await asyncio.wait_for(job._task, timeout=10)

        assert "vix" in tracker.completed

        output = job.context.get_all_outputs("vix")
        assert output["vix"] == 28.9
        assert output["level"] == "high"
