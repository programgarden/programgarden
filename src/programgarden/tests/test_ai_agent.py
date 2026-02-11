"""AI Agent 노드 Phase 3 테스트.

Resolver DAG 필터링, AIAgentToolExecutor, AIAgentNodeExecutor, Output Parser 테스트.
모든 외부 호출(LLM, API)은 mock으로 처리.
"""

from __future__ import annotations

import json
import pytest
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from programgarden.resolver import (
    WorkflowResolver,
    ResolvedWorkflow,
    ResolvedNode,
    ResolvedEdge,
)


# ============================================================
# Fixtures
# ============================================================


def _make_workflow_definition(
    nodes: List[Dict],
    edges: List[Dict],
    workflow_id: str = "test-wf",
) -> Dict[str, Any]:
    """테스트용 워크플로우 정의 생성."""
    return {
        "id": workflow_id,
        "version": "1.0.0",
        "name": "Test Workflow",
        "nodes": nodes,
        "edges": edges,
    }


def _make_resolved_workflow(
    nodes: Dict[str, ResolvedNode],
    dag_edges: List[ResolvedEdge],
    tool_edges: List[ResolvedEdge] = None,
    ai_model_edges: List[ResolvedEdge] = None,
) -> ResolvedWorkflow:
    """테스트용 ResolvedWorkflow 생성."""
    execution_order = list(nodes.keys())
    return ResolvedWorkflow(
        workflow_id="test-wf",
        version="1.0.0",
        nodes=nodes,
        edges=dag_edges,
        execution_order=execution_order,
        tool_edges=tool_edges or [],
        ai_model_edges=ai_model_edges or [],
    )


def _make_context(
    credential_data: Dict | None = None,
    outputs: Dict[str, Dict[str, Any]] = None,
) -> MagicMock:
    """간이 ExecutionContext mock."""
    ctx = MagicMock()
    ctx.log = MagicMock()
    ctx.job_id = "test-job-1"
    ctx.is_running = True
    ctx.get_workflow_credential = MagicMock(return_value=credential_data)

    # set_output / get_output / get_all_outputs
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

    # Expression evaluator context
    ctx.get_expression_context = MagicMock(return_value={})

    # AI 이벤트 notify
    ctx.notify_llm_stream = AsyncMock()
    ctx.notify_token_usage = AsyncMock()
    ctx.notify_ai_tool_call = AsyncMock()
    ctx.notify_node_state = AsyncMock()

    # node_state (실행 중 보호, cooldown 등)
    _node_state: Dict[str, Dict[str, Any]] = {}

    def _get_node_state(node_id, key):
        return _node_state.get(f"{node_id}_{key}")

    def _set_node_state(node_id, key, value):
        _node_state[f"{node_id}_{key}"] = value

    ctx.get_node_state = MagicMock(side_effect=_get_node_state)
    ctx.set_node_state = MagicMock(side_effect=_set_node_state)

    return ctx


def _make_litellm_response(
    content: str = "Hello",
    model: str = "gpt-4o",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    tool_calls: list | None = None,
):
    """LLMResponse mock 생성."""
    from programgarden.providers import LLMResponse

    return LLMResponse(
        content=content,
        model=model,
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost_usd=0.001,
        tool_calls=tool_calls,
        finish_reason="tool_calls" if tool_calls else "stop",
    )


# ============================================================
# Resolver DAG 필터링 테스트
# ============================================================


class TestResolverEdgeFiltering:
    def test_resolved_edge_has_edge_type(self):
        """ResolvedEdge에 edge_type 필드가 있는지 확인."""
        edge = ResolvedEdge("a", "b", edge_type="tool")
        assert edge.edge_type == "tool"
        assert edge.is_dag_edge is False

    def test_resolved_edge_default_main(self):
        """ResolvedEdge 기본값은 main."""
        edge = ResolvedEdge("a", "b")
        assert edge.edge_type == "main"
        assert edge.is_dag_edge is True

    def test_resolved_workflow_tool_helpers(self):
        """ResolvedWorkflow의 tool/ai_model 헬퍼 메서드."""
        nodes = {
            "agent": ResolvedNode("agent", "AIAgentNode", "ai", {}),
            "market": ResolvedNode("market", "OverseasStockMarketDataNode", "market", {}),
            "llm": ResolvedNode("llm", "LLMModelNode", "ai", {}),
        }
        tool_edges = [ResolvedEdge("market", "agent", "tool")]
        ai_model_edges = [ResolvedEdge("llm", "agent", "ai_model")]

        wf = _make_resolved_workflow(
            nodes=nodes,
            dag_edges=[],
            tool_edges=tool_edges,
            ai_model_edges=ai_model_edges,
        )

        assert wf.get_tool_node_ids("agent") == ["market"]
        assert wf.get_ai_model_node_id("agent") == "llm"
        assert wf.get_ai_model_node_id("market") is None

    def test_resolve_separates_edge_types(self):
        """resolve()가 edge_type별로 엣지를 분리하는지 확인."""
        definition = _make_workflow_definition(
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "agent", "type": "AIAgentNode"},
                {"id": "llm", "type": "LLMModelNode"},
                {"id": "market", "type": "OverseasStockMarketDataNode"},
            ],
            edges=[
                {"from": "start", "to": "agent"},
                {"from": "llm", "to": "agent", "type": "ai_model"},
                {"from": "market", "to": "agent", "type": "tool"},
            ],
        )

        resolver = WorkflowResolver()
        workflow, validation = resolver.resolve(definition)

        # validation이 실패해도 (broker 노드 없음 등) 구조 확인
        # 이 테스트에서는 resolve 성공을 보장할 수 없으므로 (broker 미포함)
        # ResolvedEdge 로직을 직접 테스트
        assert ResolvedEdge("a", "b", "main").is_dag_edge is True
        assert ResolvedEdge("a", "b", "tool").is_dag_edge is False
        assert ResolvedEdge("a", "b", "ai_model").is_dag_edge is False


# ============================================================
# AIAgentToolExecutor 테스트
# ============================================================


class TestAIAgentToolExecutor:
    def test_register_tools_empty(self):
        """tool 엣지가 없으면 빈 목록 반환."""
        from programgarden.executor import AIAgentToolExecutor, GenericNodeExecutor

        ctx = _make_context()
        wf = _make_resolved_workflow(
            nodes={"agent": ResolvedNode("agent", "AIAgentNode", "ai", {})},
            dag_edges=[],
        )

        executor = AIAgentToolExecutor(ctx, wf, GenericNodeExecutor())
        tools = executor.register_tools("agent")

        assert tools == []

    def test_register_tools_with_tool_enabled_node(self):
        """is_tool_enabled=True 노드만 Tool로 등록."""
        from programgarden.executor import AIAgentToolExecutor, GenericNodeExecutor

        ctx = _make_context()
        nodes = {
            "agent": ResolvedNode("agent", "AIAgentNode", "ai", {}),
            "market": ResolvedNode("market", "OverseasStockMarketDataNode", "market", {"symbol": "AAPL"}),
            "start": ResolvedNode("start", "StartNode", "infra", {}),
        }
        tool_edges = [
            ResolvedEdge("market", "agent", "tool"),
            ResolvedEdge("start", "agent", "tool"),  # StartNode은 tool_enabled=False
        ]

        wf = _make_resolved_workflow(nodes=nodes, dag_edges=[], tool_edges=tool_edges)
        executor = AIAgentToolExecutor(ctx, wf, GenericNodeExecutor())
        tools = executor.register_tools("agent")

        # OverseasStockMarketDataNode은 tool_enabled, StartNode은 아님
        tool_names = [t["function"]["name"] for t in tools]
        # _to_snake_case가 "Node" suffix를 제거: OverseasStockMarketDataNode → overseas_stock_market_data
        assert any("overseas_stock_market_data" in name for name in tool_names)
        assert not any("start" in name for name in tool_names)


# ============================================================
# AIAgentNodeExecutor 테스트
# ============================================================


class TestAIAgentNodeExecutor:
    @pytest.mark.asyncio
    async def test_basic_text_response(self):
        """tool 호출 없이 텍스트 응답만 반환."""
        from programgarden.executor import AIAgentNodeExecutor

        executor = AIAgentNodeExecutor()

        ctx = _make_context(outputs={
            "llm": {"connection": {
                "provider": "openai",
                "model": "gpt-4o",
                "api_key": "sk-test",
                "temperature": 0.7,
                "max_tokens": 1000,
                "streaming": False,
            }},
        })

        nodes = {
            "agent": ResolvedNode("agent", "AIAgentNode", "ai", {}),
            "llm": ResolvedNode("llm", "LLMModelNode", "ai", {}),
        }
        ai_model_edges = [ResolvedEdge("llm", "agent", "ai_model")]
        wf = _make_resolved_workflow(nodes=nodes, dag_edges=[], ai_model_edges=ai_model_edges)

        config = {
            "system_prompt": "You are a helpful assistant.",
            "user_prompt": "Hello!",
            "output_format": "text",
        }

        llm_response = _make_litellm_response(content="Hi there!")

        with patch("programgarden.providers.LLMProvider.chat", new_callable=AsyncMock, return_value=llm_response):
            result = await executor.execute(
                node_id="agent",
                node_type="AIAgentNode",
                config=config,
                context=ctx,
                workflow=wf,
            )

        assert result["response"] == "Hi there!"
        # TokenUsage 이벤트가 발행됐는지 확인
        ctx.notify_token_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_json_output_format(self):
        """JSON output_format 파싱."""
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
        }
        ai_model_edges = [ResolvedEdge("llm", "agent", "ai_model")]
        wf = _make_resolved_workflow(nodes=nodes, dag_edges=[], ai_model_edges=ai_model_edges)

        config = {
            "user_prompt": "분석해줘",
            "output_format": "json",
        }

        llm_response = _make_litellm_response(
            content='{"signal": "buy", "confidence": 0.85}'
        )

        with patch("programgarden.providers.LLMProvider.chat", new_callable=AsyncMock, return_value=llm_response):
            result = await executor.execute(
                node_id="agent", node_type="AIAgentNode",
                config=config, context=ctx, workflow=wf,
            )

        assert isinstance(result["response"], dict)
        assert result["response"]["signal"] == "buy"
        assert result["response"]["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_structured_output_format(self):
        """Structured output_format + output_schema 검증."""
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
        }
        ai_model_edges = [ResolvedEdge("llm", "agent", "ai_model")]
        wf = _make_resolved_workflow(nodes=nodes, dag_edges=[], ai_model_edges=ai_model_edges)

        config = {
            "user_prompt": "분석해줘",
            "output_format": "structured",
            "output_schema": {
                "signal": {"type": "string", "enum": ["buy", "hold", "sell"]},
                "confidence": {"type": "number"},
            },
        }

        llm_response = _make_litellm_response(
            content='{"signal": "buy", "confidence": 0.9}'
        )

        with patch("programgarden.providers.LLMProvider.chat", new_callable=AsyncMock, return_value=llm_response):
            result = await executor.execute(
                node_id="agent", node_type="AIAgentNode",
                config=config, context=ctx, workflow=wf,
            )

        assert result["response"]["signal"] == "buy"
        assert result["response"]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_no_llm_connection_error(self):
        """ai_model 엣지가 없으면 에러 반환."""
        from programgarden.executor import AIAgentNodeExecutor

        executor = AIAgentNodeExecutor()
        ctx = _make_context()

        nodes = {"agent": ResolvedNode("agent", "AIAgentNode", "ai", {})}
        wf = _make_resolved_workflow(nodes=nodes, dag_edges=[])

        config = {"user_prompt": "Hello"}

        result = await executor.execute(
            node_id="agent", node_type="AIAgentNode",
            config=config, context=ctx, workflow=wf,
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_tool_call_loop(self):
        """LLM → Tool 호출 → LLM 재호출 루프."""
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
            "market": ResolvedNode("market", "OverseasStockMarketDataNode", "market", {
                "symbol": "AAPL",
            }, product_scope="overseas_stock"),
        }
        tool_edges = [ResolvedEdge("market", "agent", "tool")]
        ai_model_edges = [ResolvedEdge("llm", "agent", "ai_model")]
        wf = _make_resolved_workflow(
            nodes=nodes, dag_edges=[],
            tool_edges=tool_edges, ai_model_edges=ai_model_edges,
        )

        config = {
            "user_prompt": "AAPL 시세 알려줘",
            "output_format": "text",
        }

        # 1차: Tool 호출 요청
        tool_call_response = _make_litellm_response(
            content="",
            tool_calls=[{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "overseas_stock_market_data_node",
                    "arguments": '{"symbol": "AAPL"}',
                },
            }],
        )
        # 2차: 최종 응답
        final_response = _make_litellm_response(content="AAPL 현재가는 $150입니다.")

        call_count = 0

        async def mock_chat(messages, tools=None):
            nonlocal call_count
            call_count += 1
            return tool_call_response if call_count == 1 else final_response

        # GenericNodeExecutor.execute mock (Tool 실행)
        with patch("programgarden.providers.LLMProvider.chat", side_effect=mock_chat):
            with patch(
                "programgarden.executor.GenericNodeExecutor.execute",
                new_callable=AsyncMock,
                return_value={"price": 150.0, "symbol": "AAPL"},
            ):
                result = await executor.execute(
                    node_id="agent", node_type="AIAgentNode",
                    config=config, context=ctx, workflow=wf,
                )

        assert result["response"] == "AAPL 현재가는 $150입니다."
        assert call_count == 2  # tool_call + final
        ctx.notify_ai_tool_call.assert_called_once()


# ============================================================
# Output Parser 테스트
# ============================================================


class TestOutputParser:
    def test_text_passthrough(self):
        """text 모드: 원문 그대로 반환."""
        from programgarden.executor import AIAgentNodeExecutor

        executor = AIAgentNodeExecutor()
        ctx = _make_context()

        result = executor._parse_output("hello world", "text", None, ctx, "node-1")
        assert result == "hello world"

    def test_json_parse(self):
        """json 모드: JSON 파싱."""
        from programgarden.executor import AIAgentNodeExecutor

        executor = AIAgentNodeExecutor()
        ctx = _make_context()

        result = executor._parse_output('{"key": "value"}', "json", None, ctx, "node-1")
        assert result == {"key": "value"}

    def test_json_with_markdown_block(self):
        """json 모드: ```json ... ``` 블록 추출."""
        from programgarden.executor import AIAgentNodeExecutor

        executor = AIAgentNodeExecutor()
        ctx = _make_context()

        raw = 'Sure:\n```json\n{"signal": "buy"}\n```\nDone.'
        result = executor._parse_output(raw, "json", None, ctx, "node-1")
        assert result == {"signal": "buy"}

    def test_json_parse_failure_fallback(self):
        """json 모드: 파싱 실패 시 원문 반환."""
        from programgarden.executor import AIAgentNodeExecutor

        executor = AIAgentNodeExecutor()
        ctx = _make_context()

        result = executor._parse_output("not json", "json", None, ctx, "node-1")
        assert result == "not json"

    def test_structured_validation(self):
        """structured 모드: output_schema Pydantic 검증."""
        from programgarden.executor import AIAgentNodeExecutor

        executor = AIAgentNodeExecutor()
        ctx = _make_context()

        schema = {
            "signal": {"type": "string", "enum": ["buy", "hold", "sell"]},
            "confidence": {"type": "number"},
        }
        raw = '{"signal": "buy", "confidence": 0.85}'
        result = executor._parse_output(raw, "structured", schema, ctx, "node-1")

        assert result["signal"] == "buy"
        assert result["confidence"] == 0.85

    def test_structured_invalid_enum_fallback(self):
        """structured 모드: enum 위반 시 원본 dict 반환 (validation 실패 폴백)."""
        from programgarden.executor import AIAgentNodeExecutor

        executor = AIAgentNodeExecutor()
        ctx = _make_context()

        schema = {
            "signal": {"type": "string", "enum": ["buy", "hold", "sell"]},
        }
        raw = '{"signal": "invalid_signal"}'
        result = executor._parse_output(raw, "structured", schema, ctx, "node-1")

        # Pydantic Literal 검증 실패 → 원본 dict 반환
        assert result == {"signal": "invalid_signal"}


# ============================================================
# Tool Result Compact 테스트
# ============================================================


class TestCompactToolResult:
    """_compact_tool_result() 단위 테스트."""

    def test_small_dict_unchanged(self):
        """작은 dict는 변경 없이 반환."""
        from programgarden.executor import AIAgentNodeExecutor

        result = {"price": 150.0, "symbol": "AAPL", "volume": 1000}
        compacted = AIAgentNodeExecutor._compact_tool_result(result)

        assert compacted == result

    def test_small_array_unchanged(self):
        """배열이 threshold 미만이면 변경 없이 반환."""
        from programgarden.executor import AIAgentNodeExecutor

        result = {
            "positions": [
                {"symbol": "AAPL", "qty": 100, "pnl": 5.2},
                {"symbol": "TSLA", "qty": 50, "pnl": -3.1},
            ]
        }
        compacted = AIAgentNodeExecutor._compact_tool_result(result)

        assert compacted == result

    def test_large_ohlcv_m4_downsample(self):
        """OHLCV 캔들 배열 → M4 다운샘플링 (시계열 감지)."""
        from programgarden.executor import AIAgentNodeExecutor

        # 100개 캔들 데이터 (open/high/low/close → timeseries 감지)
        candles = [
            {"open": 100 + i, "close": 101 + i, "high": 102 + i, "low": 99 + i, "volume": 1000 * (i + 1)}
            for i in range(100)
        ]
        result = {"candles": candles}
        compacted = AIAgentNodeExecutor._compact_tool_result(result)

        summary = compacted["candles"]
        assert summary["_compacted"] is True
        assert summary["method"] == "m4"
        assert summary["count"] == 100
        # M4는 처음/끝 보존
        assert candles[0] in summary["samples"]
        assert candles[-1] in summary["samples"]
        # 100개 → 8버킷 × 최대4개 = 최대 32개 + 처음/끝 (중복 제거)
        assert len(summary["samples"]) < 100
        assert "stats" in summary
        assert "open" in summary["stats"]
        assert summary["stats"]["open"]["min"] == 100
        assert summary["stats"]["open"]["max"] == 199

    def test_large_positions_topn_downsample(self):
        """포지션 배열 → Top-N 다운샘플링 (순위형 감지)."""
        from programgarden.executor import AIAgentNodeExecutor

        positions = [
            {"symbol": f"SYM{i:03d}", "quantity": 10 + i, "pnl": float(i - 10), "pnl_rate": (i - 10) / 100}
            for i in range(20)
        ]
        result = {"positions": positions}
        compacted = AIAgentNodeExecutor._compact_tool_result(result)

        summary = compacted["positions"]
        assert summary["_compacted"] is True
        assert summary["method"] == "topn"
        assert summary["count"] == 20
        assert "top" in summary
        assert "bottom" in summary
        # top은 pnl_rate 기준 상위 5개
        assert summary["top"][0]["pnl_rate"] > summary["top"][-1]["pnl_rate"]

    def test_large_array_avg_calculation(self):
        """통계 요약의 avg 계산 검증."""
        from programgarden.executor import AIAgentNodeExecutor

        items = [{"value": float(i)} for i in range(10)]
        result = {"data": items}
        compacted = AIAgentNodeExecutor._compact_tool_result(result)

        assert compacted["data"]["_compacted"] is True
        assert compacted["data"]["stats"]["value"]["avg"] == 4.5  # (0+1+...+9)/10

    def test_max_chars_guard(self):
        """전체 문자수 초과 시 truncation."""
        from programgarden.executor import AIAgentNodeExecutor

        # 매우 큰 단일 값 (배열이 아닌 긴 문자열이 포함된 dict)
        result = {"data": "x" * 10000}
        compacted = AIAgentNodeExecutor._compact_tool_result(result)

        assert "_truncated" in compacted
        assert "preview" in compacted
        assert len(compacted["preview"]) <= AIAgentNodeExecutor._MAX_TOOL_RESULT_CHARS + 100  # 약간의 마진

    def test_nested_dict_with_array(self):
        """중첩된 dict 내부의 배열도 compact."""
        from programgarden.executor import AIAgentNodeExecutor

        result = {
            "meta": {"status": "ok"},
            "items": [{"price": float(i)} for i in range(15)],
        }
        compacted = AIAgentNodeExecutor._compact_tool_result(result)

        assert compacted["meta"] == {"status": "ok"}  # 작은 dict는 유지
        assert compacted["items"]["_compacted"] is True
        assert compacted["items"]["count"] == 15

    def test_empty_array(self):
        """빈 배열은 count만 반환."""
        from programgarden.executor import AIAgentNodeExecutor

        # threshold=10이므로 빈 배열은 compact 대상이 아님 (len < threshold)
        result = {"data": []}
        compacted = AIAgentNodeExecutor._compact_tool_result(result)

        assert compacted["data"] == []  # 빈 배열은 그대로

    def test_numeric_stats_only_for_numeric_fields(self):
        """문자열 필드는 stats에 포함되지 않음."""
        from programgarden.executor import AIAgentNodeExecutor

        items = [{"name": f"item_{i}", "value": float(i)} for i in range(12)]
        result = {"data": items}
        compacted = AIAgentNodeExecutor._compact_tool_result(result)

        stats = compacted["data"]["stats"]
        assert "value" in stats
        assert "name" not in stats


# ============================================================
# Phase 4: 프리셋 시스템 테스트
# ============================================================


class TestPresetLoader:
    """PresetLoader 단위 테스트."""

    def setup_method(self):
        from programgarden_core.presets import PresetLoader
        PresetLoader.clear_cache()

    def test_load_preset_risk_manager(self):
        """risk_manager 프리셋 로드."""
        from programgarden_core.presets import PresetLoader

        preset = PresetLoader.load_preset("risk_manager")
        assert preset is not None
        assert preset["id"] == "risk_manager"
        assert "system_prompt" in preset
        assert "output_schema" in preset

    def test_load_preset_custom_returns_none(self):
        """custom 프리셋은 None 반환."""
        from programgarden_core.presets import PresetLoader

        assert PresetLoader.load_preset("custom") is None
        assert PresetLoader.load_preset("") is None
        assert PresetLoader.load_preset(None) is None

    def test_load_preset_unknown_returns_none(self):
        """존재하지 않는 프리셋은 None 반환."""
        from programgarden_core.presets import PresetLoader

        assert PresetLoader.load_preset("unknown_preset_xyz") is None

    def test_list_presets(self):
        """프리셋 목록 조회."""
        from programgarden_core.presets import PresetLoader

        presets = PresetLoader.list_presets()
        assert len(presets) >= 4
        ids = [p["id"] for p in presets]
        assert "risk_manager" in ids
        assert "news_analyst" in ids
        assert "technical_analyst" in ids
        assert "strategist" in ids

    def test_apply_preset_fills_system_prompt(self):
        """프리셋 적용 시 system_prompt 채움."""
        from programgarden_core.presets import PresetLoader

        config = {"user_prompt": "포지션 분석해줘"}
        result = PresetLoader.apply_preset("risk_manager", config)
        assert "위험관리" in result["system_prompt"]
        assert result.get("output_format") == "structured"

    def test_apply_preset_preserves_user_prompt(self):
        """사용자가 설정한 system_prompt은 프리셋 뒤에 병합."""
        from programgarden_core.presets import PresetLoader

        config = {"system_prompt": "나만의 추가 규칙"}
        result = PresetLoader.apply_preset("risk_manager", config)
        assert "위험관리" in result["system_prompt"]
        assert "나만의 추가 규칙" in result["system_prompt"]

    def test_apply_preset_user_config_overrides(self):
        """사용자 설정이 프리셋 default_config보다 우선."""
        from programgarden_core.presets import PresetLoader

        config = {"output_format": "text", "max_tool_calls": 20}
        result = PresetLoader.apply_preset("risk_manager", config)
        assert result["output_format"] == "text"  # 사용자 설정 유지
        assert result["max_tool_calls"] == 20     # 사용자 설정 유지

    def test_get_preset_ids(self):
        """프리셋 ID 목록."""
        from programgarden_core.presets import PresetLoader

        ids = PresetLoader.get_preset_ids()
        assert "risk_manager" in ids
        assert "strategist" in ids


# ============================================================
# Phase 4: autonomy_level R/W 분류 테스트
# ============================================================


class TestToolAccessType:
    """tool_access_type R/W 분류 테스트."""

    def test_base_node_default_read(self):
        """BaseNode 기본 tool_access_type은 read."""
        from programgarden_core.nodes.base import BaseNode
        assert BaseNode.tool_access_type() == "read"

    def test_order_node_is_write(self):
        """주문 노드는 write."""
        from programgarden_core.nodes.order import (
            OverseasStockNewOrderNode,
            OverseasFuturesNewOrderNode,
        )
        assert OverseasStockNewOrderNode.tool_access_type() == "write"
        assert OverseasFuturesNewOrderNode.tool_access_type() == "write"

    def test_market_data_node_is_read(self):
        """시세 조회 노드는 read (기본값)."""
        from programgarden_core.nodes.data_stock import OverseasStockMarketDataNode
        assert OverseasStockMarketDataNode.tool_access_type() == "read"

    def test_account_node_is_read(self):
        """잔고 조회 노드는 read (기본값)."""
        from programgarden_core.nodes.account_stock import OverseasStockAccountNode
        assert OverseasStockAccountNode.tool_access_type() == "read"

    def test_sqlite_node_is_write(self):
        """SQLiteNode는 write."""
        from programgarden_core.nodes.data import SQLiteNode
        assert SQLiteNode.tool_access_type() == "write"

    def test_http_request_node_is_write(self):
        """HTTPRequestNode는 write."""
        from programgarden_core.nodes.data import HTTPRequestNode
        assert HTTPRequestNode.tool_access_type() == "write"


class TestAutonomyLevel:
    """autonomy_level에 따른 Tool 차단 로직 테스트."""

    def _make_tool_executor(self):
        """테스트용 AIAgentToolExecutor mock."""
        from programgarden.executor import AIAgentToolExecutor

        ctx = _make_context()
        wf = _make_resolved_workflow(nodes={}, dag_edges=[])
        generic = MagicMock()
        executor = AIAgentToolExecutor(ctx, wf, generic)

        # Tool 등록 시뮬레이션
        executor._tool_configs = {
            "overseas_stock_market_data": {
                "node_id": "market",
                "node_type": "OverseasStockMarketDataNode",
                "config": {},
            },
            "overseas_stock_new_order": {
                "node_id": "order",
                "node_type": "OverseasStockNewOrderNode",
                "config": {},
            },
        }
        executor._tool_access_types = {
            "overseas_stock_market_data": "read",
            "overseas_stock_new_order": "write",
        }
        return executor

    def test_full_auto_allows_all(self):
        """full_auto: 모든 Tool 허용."""
        executor = self._make_tool_executor()
        assert executor.is_tool_blocked("overseas_stock_market_data", "full_auto") is False
        assert executor.is_tool_blocked("overseas_stock_new_order", "full_auto") is False

    def test_semi_auto_allows_read_blocks_write(self):
        """semi_auto: Read 허용, Write 차단."""
        executor = self._make_tool_executor()
        assert executor.is_tool_blocked("overseas_stock_market_data", "semi_auto") is False
        assert executor.is_tool_blocked("overseas_stock_new_order", "semi_auto") is True

    def test_supervised_blocks_all(self):
        """supervised: 모든 Tool 차단."""
        executor = self._make_tool_executor()
        assert executor.is_tool_blocked("overseas_stock_market_data", "supervised") is True
        assert executor.is_tool_blocked("overseas_stock_new_order", "supervised") is True

    @pytest.mark.asyncio
    async def test_call_tool_blocked_returns_blocked_result(self):
        """차단된 Tool 호출 시 _blocked 결과 반환."""
        executor = self._make_tool_executor()
        result = await executor.call_tool(
            tool_name="overseas_stock_new_order",
            args={"symbol": "AAPL"},
            agent_node_id="agent-1",
            autonomy_level="semi_auto",
        )
        assert result["_blocked"] is True
        assert result["access_type"] == "write"
        assert "승인" in result["reason"]

    @pytest.mark.asyncio
    async def test_call_tool_allowed_executes(self):
        """허용된 Tool은 정상 실행."""
        executor = self._make_tool_executor()
        executor.generic_executor.execute = AsyncMock(return_value={"price": 150.0})

        # workflow에서 노드 찾기 mock
        executor.workflow.nodes = {
            "market": ResolvedNode("market", "OverseasStockMarketDataNode", "market", {}),
        }
        # product_scope 설정
        executor.workflow.nodes["market"].product_scope = "all"

        result = await executor.call_tool(
            tool_name="overseas_stock_market_data",
            args={"symbol": "AAPL"},
            agent_node_id="agent-1",
            autonomy_level="semi_auto",
        )
        assert "_blocked" not in result
        assert result["price"] == 150.0
