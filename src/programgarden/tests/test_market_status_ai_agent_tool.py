"""MarketStatusNode AI Agent Tool 통합 테스트 (Phase 5).

Plan: .claude/pg-plans/20260418-jif-market-status-plan.md (Phase 5)

LLM 실호출 없이 MarketStatusNode 가 AI Agent Tool 로 제대로 등록되고,
tool_call 이 trigger 되면 실제 MarketStatusNodeExecutor 를 호출하여
us_is_open / kospi_is_open 등 포트 결과를 LLM 에 반환하는 경로를 검증.

검증 범위:
1. `is_tool_enabled=True` + tool schema (tool_name, description, params)
2. AIAgentToolExecutor.register_tools 가 market_status 포함
3. tool_call 발생 시 GenericNodeExecutor 경유 결과 반환
4. markets Literal — 해외선물 키 (CME/SGX) 는 tool schema 파라미터 enum 에서 제외

**LLM 의 자연어 → tool 선택 품질 자체**는 본 테스트 범위 밖.
FastEmbed semantic matching 은 실측이 필요하므로 docs/ai_agent_guide.md
의 샘플 쿼리로 문서화되며, 본 테스트에서는 tool_call.arguments 를
직접 stub 하여 pipe 연결성만 검증.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from programgarden.resolver import ResolvedEdge, ResolvedNode, ResolvedWorkflow


# ---------------------------------------------------------------------------
# fixtures (재사용: test_ai_agent.py 패턴)
# ---------------------------------------------------------------------------


def _make_context(outputs: Dict[str, Dict[str, Any]] | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.log = MagicMock()
    ctx.job_id = "test-job-ms"
    ctx.is_running = True
    ctx.get_workflow_credential = MagicMock(return_value=None)

    _store: Dict[str, Dict[str, Any]] = outputs or {}

    def _set_output(node_id, port, value):
        _store.setdefault(node_id, {})[port] = value

    def _get_output(node_id, port):
        return _store.get(node_id, {}).get(port)

    def _get_all_outputs(node_id):
        return _store.get(node_id, {})

    ctx.set_output = MagicMock(side_effect=_set_output)
    ctx.get_output = MagicMock(side_effect=_get_output)
    ctx.get_all_outputs = MagicMock(side_effect=_get_all_outputs)

    ctx.get_expression_context = MagicMock(return_value={})
    ctx.notify_llm_stream = AsyncMock()
    ctx.notify_token_usage = AsyncMock()
    ctx.notify_ai_tool_call = AsyncMock()
    ctx.notify_node_state = AsyncMock()

    _node_state: Dict[str, Dict[str, Any]] = {}
    ctx.get_node_state = MagicMock(side_effect=lambda n, k: _node_state.get(f"{n}_{k}"))
    ctx.set_node_state = MagicMock(
        side_effect=lambda n, k, v: _node_state.__setitem__(f"{n}_{k}", v)
    )

    return ctx


def _make_resolved_workflow(
    nodes: Dict[str, ResolvedNode],
    tool_edges: List[ResolvedEdge] | None = None,
    ai_model_edges: List[ResolvedEdge] | None = None,
) -> ResolvedWorkflow:
    return ResolvedWorkflow(
        workflow_id="test-wf-ms",
        version="1.0.0",
        nodes=nodes,
        edges=[],
        execution_order=list(nodes.keys()),
        tool_edges=tool_edges or [],
        ai_model_edges=ai_model_edges or [],
    )


def _make_litellm_response(content: str = "", tool_calls: list | None = None):
    from programgarden.providers import LLMResponse

    return LLMResponse(
        content=content,
        model="gpt-4o",
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        cost_usd=0.001,
        tool_calls=tool_calls,
        finish_reason="tool_calls" if tool_calls else "stop",
    )


# ---------------------------------------------------------------------------
# 1. MarketStatusNode 의 tool schema 검증
# ---------------------------------------------------------------------------


class TestMarketStatusToolSchema:
    def test_is_tool_enabled(self):
        from programgarden_core.nodes.market_status import MarketStatusNode

        assert MarketStatusNode.is_tool_enabled() is True

    def test_tool_schema_has_expected_fields(self):
        """FastEmbed semantic matching 이 tool_name/description 기반으로
        작동하므로 핵심 키워드가 description 에 포함되어야 함."""

        from programgarden_core.nodes.market_status import MarketStatusNode

        schema = MarketStatusNode.as_tool_schema()

        assert schema["tool_name"] == "market_status"
        assert "market" in schema["description"].lower()
        # Plan 이 요구한 자연어 질의 예제 키워드
        assert "open" in schema["description"].lower()
        assert "KOSPI" in schema["description"] or "US market" in schema["description"]

        # 파라미터 3종 (Plan 5.x 스키마)
        params = schema.get("parameters", {})
        assert "markets" in params
        assert "stay_connected" in params
        assert "include_extended_hours" in params

    def test_market_key_literal_excludes_overseas_futures(self):
        """MarketKey Literal 이 해외선물 키 (CME/SGX/HKEX_FUTURES) 제외.
        Plan 의 'JIF 범위 밖' 제약을 Pydantic 타입에서 강제.

        Pydantic Literal 의 validation 이 tool schema 의 enum 보다 상위
        방어선. LLM 이 arguments 로 해외선물 키를 넘기더라도 Pydantic
        ValidationError 가 발생하여 tool 실행 자체가 차단됨.

        (참고: core as_tool_schema 는 현재 Literal 을 enum 으로 노출하지
        않음 — 별도 개선 과제. 본 테스트는 타입 레벨 방어를 검증.)
        """

        from typing import get_args

        from programgarden_core.nodes.market_status import MarketKey

        literal_values = set(get_args(MarketKey))

        # JIF 지원 12개 시장만 허용
        forbidden = {"CME", "SGX", "HKEX_FUTURES", "SGX_FUTURES", "EUREX"}
        assert not (forbidden & literal_values), (
            f"해외선물 시장 키가 MarketKey Literal 에 포함됨: "
            f"{forbidden & literal_values}"
        )

        # 대표 JIF 시장 키 포함 검증
        expected = {"US", "KOSPI", "KOSDAQ", "HK_AM", "HK_PM", "JP_AM", "CN_AM"}
        assert expected.issubset(literal_values), (
            f"JIF 지원 시장이 MarketKey 에서 누락: {expected - literal_values}"
        )

        # Pydantic 검증 — 해외선물 키 주입 시 ValidationError
        from pydantic import ValidationError

        from programgarden_core.nodes.market_status import MarketStatusNode

        with pytest.raises(ValidationError):
            MarketStatusNode(markets=["CME"])


# ---------------------------------------------------------------------------
# 2. AIAgentToolExecutor 가 MarketStatusNode 를 tool 로 등록
# ---------------------------------------------------------------------------


class TestMarketStatusToolRegistration:
    def test_register_tools_includes_market_status(self):
        from programgarden.executor import AIAgentToolExecutor, GenericNodeExecutor

        ctx = _make_context()
        nodes = {
            "agent": ResolvedNode("agent", "AIAgentNode", "ai", {}),
            "market_status": ResolvedNode(
                "market_status", "MarketStatusNode", "market",
                {"markets": ["US"], "stay_connected": False},
            ),
        }
        tool_edges = [ResolvedEdge("market_status", "agent", "tool")]
        wf = _make_resolved_workflow(nodes=nodes, tool_edges=tool_edges)

        executor = AIAgentToolExecutor(ctx, wf, GenericNodeExecutor())
        tools = executor.register_tools("agent")

        tool_names = [t["function"]["name"] for t in tools]
        assert "market_status" in tool_names, (
            f"market_status tool 이 등록되지 않음: {tool_names}"
        )

        # 등록된 tool 의 description 에 핵심 키워드 포함
        ms_tool = next(t for t in tools if t["function"]["name"] == "market_status")
        assert "market" in ms_tool["function"]["description"].lower()


# ---------------------------------------------------------------------------
# 3. AIAgentNodeExecutor tool_call 루프 — market_status 호출 후 응답 생성
# ---------------------------------------------------------------------------


class TestMarketStatusAgentToolCallLoop:
    @pytest.mark.asyncio
    async def test_us_open_query_routes_to_market_status_tool(self):
        """자연어 질의 'Is US market open now?' 시나리오 (tool_call stub).

        LLM 이 markets=['US'] 인자로 market_status tool 을 호출 →
        GenericNodeExecutor mock 이 us_is_open=True 반환 →
        LLM 2차 호출에서 최종 답변 생성. 실제 LLM semantic matching 은
        범위 밖이므로 tool_calls 를 직접 stub."""

        from programgarden.executor import AIAgentNodeExecutor

        executor = AIAgentNodeExecutor()

        ctx = _make_context(outputs={
            "llm": {"connection": {
                "provider": "openai", "model": "gpt-4o",
                "api_key": "sk-test", "temperature": 0.7,
                "max_tokens": 1000, "streaming": False,
            }},
        })

        nodes = {
            "agent": ResolvedNode("agent", "AIAgentNode", "ai", {}),
            "llm": ResolvedNode("llm", "LLMModelNode", "ai", {}),
            "market_status": ResolvedNode(
                "market_status", "MarketStatusNode", "market",
                {"markets": ["US"], "stay_connected": False},
            ),
        }
        tool_edges = [ResolvedEdge("market_status", "agent", "tool")]
        ai_model_edges = [ResolvedEdge("llm", "agent", "ai_model")]
        wf = _make_resolved_workflow(
            nodes=nodes, tool_edges=tool_edges, ai_model_edges=ai_model_edges,
        )

        config = {
            "user_prompt": "Is the US market open now?",
            "output_format": "text",
        }

        tool_call_response = _make_litellm_response(
            content="",
            tool_calls=[{
                "id": "call_ms_1",
                "type": "function",
                "function": {
                    "name": "market_status",
                    "arguments": '{"markets": ["US"], "stay_connected": false}',
                },
            }],
        )
        final_response = _make_litellm_response(
            content="Yes, the US market is currently open (regular hours).",
        )

        call_count = 0
        captured_tool_executions: List[Dict[str, Any]] = []

        async def mock_chat(messages, tools=None):
            nonlocal call_count
            call_count += 1
            return tool_call_response if call_count == 1 else final_response

        async def mock_generic_execute(self, node_id, node_type, config, context, **kwargs):
            captured_tool_executions.append({
                "node_id": node_id, "node_type": node_type, "config": config,
            })
            # MarketStatusNode 실제 실행을 흉내낸 스냅샷 반환
            return {
                "statuses": [{
                    "market": "US", "jstatus": "21",
                    "jstatus_label": "Market open", "is_open": True,
                    "is_regular_open": True,
                }],
                "us_is_open": True,
            }

        with patch("programgarden.providers.LLMProvider.chat", side_effect=mock_chat):
            with patch(
                "programgarden.executor.GenericNodeExecutor.execute",
                new=mock_generic_execute,
            ):
                result = await executor.execute(
                    node_id="agent", node_type="AIAgentNode",
                    config=config, context=ctx, workflow=wf,
                )

        # LLM 2회 호출 (tool_call + final)
        assert call_count == 2

        # MarketStatusNode 가 실제로 tool 로 실행됨
        assert len(captured_tool_executions) == 1
        tool_exec = captured_tool_executions[0]
        assert tool_exec["node_type"] == "MarketStatusNode"
        # LLM 이 인자로 전달한 markets=["US"] 가 config 에 병합되어야 함
        assert tool_exec["config"].get("markets") == ["US"]

        # 최종 응답
        assert "open" in result["response"].lower()
        ctx.notify_ai_tool_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_kospi_query_routes_with_correct_market_filter(self):
        """'코스피 지금 열려있어?' 시나리오 — LLM 이 markets=['KOSPI']
        인자로 market_status tool 을 호출하는지 arguments 전달 경로 검증."""

        from programgarden.executor import AIAgentNodeExecutor

        executor = AIAgentNodeExecutor()

        ctx = _make_context(outputs={
            "llm": {"connection": {
                "provider": "openai", "model": "gpt-4o",
                "api_key": "sk-test", "temperature": 0.7,
                "max_tokens": 1000, "streaming": False,
            }},
        })

        nodes = {
            "agent": ResolvedNode("agent", "AIAgentNode", "ai", {}),
            "llm": ResolvedNode("llm", "LLMModelNode", "ai", {}),
            "market_status": ResolvedNode(
                "market_status", "MarketStatusNode", "market",
                {"markets": [], "stay_connected": False},
            ),
        }
        tool_edges = [ResolvedEdge("market_status", "agent", "tool")]
        ai_model_edges = [ResolvedEdge("llm", "agent", "ai_model")]
        wf = _make_resolved_workflow(
            nodes=nodes, tool_edges=tool_edges, ai_model_edges=ai_model_edges,
        )

        config = {
            "user_prompt": "코스피 지금 열려있어?",
            "output_format": "text",
        }

        tool_call_response = _make_litellm_response(
            content="",
            tool_calls=[{
                "id": "call_ms_kospi",
                "type": "function",
                "function": {
                    "name": "market_status",
                    "arguments": '{"markets": ["KOSPI"], "stay_connected": false}',
                },
            }],
        )
        final_response = _make_litellm_response(
            content="코스피는 현재 휴장입니다 (Regular hours closed).",
        )

        call_count = 0
        captured: List[Dict[str, Any]] = []

        async def mock_chat(messages, tools=None):
            nonlocal call_count
            call_count += 1
            return tool_call_response if call_count == 1 else final_response

        async def mock_generic_execute(self, node_id, node_type, config, context, **kwargs):
            captured.append({"config": config})
            return {
                "statuses": [{
                    "market": "KOSPI", "jstatus": "41",
                    "is_regular_open": False,
                }],
                "kospi_is_open": False,
            }

        with patch("programgarden.providers.LLMProvider.chat", side_effect=mock_chat):
            with patch(
                "programgarden.executor.GenericNodeExecutor.execute",
                new=mock_generic_execute,
            ):
                result = await executor.execute(
                    node_id="agent", node_type="AIAgentNode",
                    config=config, context=ctx, workflow=wf,
                )

        assert call_count == 2
        assert len(captured) == 1
        # 자연어 → markets=["KOSPI"] 로 변환되어 노드 config 에 전달됨
        assert captured[0]["config"].get("markets") == ["KOSPI"]
        assert "코스피" in result["response"] or "KOSPI" in result["response"]
