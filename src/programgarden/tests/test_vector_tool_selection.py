"""벡터 기반 도구 선택(Semantic Tool Selection) 테스트.

FastEmbed 벡터 검색 기반 AIAgent 도구 선별 기능 테스트.
모든 외부 호출은 mock 처리.
"""

from __future__ import annotations

import pytest
import numpy as np
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch


# ============================================================
# Helper: 도구 생성
# ============================================================

def _make_tool(name: str, description: str, params: Dict[str, str] | None = None) -> Dict[str, Any]:
    """OpenAI function-call 형식 도구 생성."""
    properties = {}
    if params:
        properties = {k: {"type": "string", "description": v} for k, v in params.items()}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties},
        },
    }


def _make_tools(n: int = 8) -> List[Dict[str, Any]]:
    """n개의 다양한 도구 생성 (벡터 검색 테스트용)."""
    tool_defs = [
        ("get_stock_price", "Get current stock price and market data", {"symbol": "Stock ticker symbol"}),
        ("get_account_balance", "Get trading account balance and positions", {"account_id": "Account identifier"}),
        ("place_order", "Place a new stock buy or sell order", {"symbol": "Ticker", "side": "buy or sell", "quantity": "Number of shares"}),
        ("get_historical_data", "Get historical OHLCV candlestick data", {"symbol": "Ticker", "period": "Time period"}),
        ("calculate_rsi", "Calculate RSI technical indicator", {"data": "Price data array", "period": "RSI period"}),
        ("get_news", "Get latest financial news and headlines", {"query": "Search query for news"}),
        ("send_telegram", "Send a message via Telegram bot", {"message": "Text message to send", "chat_id": "Telegram chat ID"}),
        ("get_exchange_rate", "Get currency exchange rate", {"base": "Base currency", "target": "Target currency"}),
        ("backtest_strategy", "Run backtest on a trading strategy", {"strategy": "Strategy name", "period": "Backtest period"}),
        ("get_fear_greed_index", "Get CNN Fear and Greed market sentiment index", {}),
    ]
    return [_make_tool(*td) for td in tool_defs[:n]]


# ============================================================
# AIAgentToolExecutor mock
# ============================================================

class MockContext:
    def log(self, level, message, node_id):
        pass


def _make_tool_executor(tools: List[Dict[str, Any]]):
    """AIAgentToolExecutor의 벡터 관련 메서드만 테스트하는 간이 인스턴스."""
    from programgarden.executor import AIAgentToolExecutor

    executor = object.__new__(AIAgentToolExecutor)
    executor.context = MockContext()
    executor._all_tools = tools
    executor._build_embedding_index(tools)
    return executor


# ============================================================
# Phase 1: Core 노드 정의 테스트
# ============================================================

class TestAIAgentNodeDefinition:
    """AIAgentNode tool_selection 필드 정의 테스트."""

    def test_tool_selection_default_is_semantic(self):
        from programgarden_core.nodes.ai import AIAgentNode
        node = AIAgentNode(id="test", type="AIAgentNode")
        assert node.tool_selection == "semantic"

    def test_tool_selection_enum_has_semantic(self):
        from programgarden_core.nodes.ai import AIAgentNode
        node = AIAgentNode(id="test", type="AIAgentNode", tool_selection="semantic")
        assert node.tool_selection == "semantic"

    def test_tool_selection_enum_has_all(self):
        from programgarden_core.nodes.ai import AIAgentNode
        node = AIAgentNode(id="test", type="AIAgentNode", tool_selection="all")
        assert node.tool_selection == "all"

    def test_tool_selection_enum_rejects_bm25(self):
        from programgarden_core.nodes.ai import AIAgentNode
        with pytest.raises(Exception):
            AIAgentNode(id="test", type="AIAgentNode", tool_selection="bm25")

    def test_tool_top_k_default(self):
        from programgarden_core.nodes.ai import AIAgentNode
        node = AIAgentNode(id="test", type="AIAgentNode")
        assert node.tool_top_k == 5

    def test_field_schema_tool_selection_enum(self):
        from programgarden_core.nodes.ai import AIAgentNode
        schema = AIAgentNode.get_field_schema()
        ts = schema["tool_selection"]
        assert ts.enum_values == ["all", "semantic"]
        assert "semantic" in ts.enum_labels
        assert "bm25" not in ts.enum_labels
        assert ts.default == "semantic"

    def test_field_schema_tool_top_k_visible_when(self):
        from programgarden_core.nodes.ai import AIAgentNode
        schema = AIAgentNode.get_field_schema()
        tk = schema["tool_top_k"]
        assert tk.visible_when == {"tool_selection": "semantic"}


# ============================================================
# Phase 2: 벡터 인덱스 빌드 테스트
# ============================================================

class TestBuildEmbeddingIndex:
    """_build_embedding_index 메서드 테스트."""

    def test_builds_tool_docs(self):
        tools = _make_tools(3)
        executor = _make_tool_executor(tools)
        assert len(executor._tool_docs) == 3
        assert executor._tool_embeddings is None  # lazy init
        assert executor._embed_model is None

    def test_tool_docs_contain_name_and_description(self):
        tools = [_make_tool("get_price", "Get stock price", {"symbol": "Ticker"})]
        executor = _make_tool_executor(tools)
        doc = executor._tool_docs[0]
        assert "get_price" in doc
        assert "Get stock price" in doc
        assert "symbol" in doc
        assert "Ticker" in doc


# ============================================================
# Phase 3: select_tools 벡터 검색 테스트
# ============================================================

class TestSelectTools:
    """select_tools 벡터 유사도 기반 선별 테스트."""

    def test_returns_all_when_5_or_fewer_tools(self):
        """5개 이하 도구는 전체 반환."""
        tools = _make_tools(5)
        executor = _make_tool_executor(tools)
        result = executor.select_tools("stock price", top_k=3)
        assert len(result) == 5
        assert result == tools

    def test_returns_top_k_when_more_than_5_tools(self):
        """6개 이상 도구에서 top_k개만 반환."""
        tools = _make_tools(8)
        executor = _make_tool_executor(tools)
        result = executor.select_tools("stock price", top_k=3)
        assert len(result) == 3

    def test_returns_all_on_empty_query(self):
        """빈 쿼리 → 전체 반환."""
        tools = _make_tools(8)
        executor = _make_tool_executor(tools)
        result = executor.select_tools("", top_k=3)
        assert len(result) == 8

    def test_returns_all_on_whitespace_query(self):
        """공백 쿼리 → 전체 반환."""
        tools = _make_tools(8)
        executor = _make_tool_executor(tools)
        result = executor.select_tools("   ", top_k=3)
        assert len(result) == 8

    def test_semantic_relevance_stock_price(self):
        """의미적 관련성: 'stock price' 쿼리 → get_stock_price가 상위."""
        tools = _make_tools(8)
        executor = _make_tool_executor(tools)
        result = executor.select_tools("What is the current stock price of AAPL?", top_k=3)
        result_names = [t["function"]["name"] for t in result]
        assert "get_stock_price" in result_names

    def test_semantic_relevance_telegram(self):
        """의미적 관련성: 'send message telegram' → send_telegram 상위."""
        tools = _make_tools(8)
        executor = _make_tool_executor(tools)
        result = executor.select_tools("Send a notification message via telegram", top_k=3)
        result_names = [t["function"]["name"] for t in result]
        assert "send_telegram" in result_names

    def test_semantic_relevance_rsi(self):
        """의미적 관련성: 'RSI indicator' → calculate_rsi 상위."""
        tools = _make_tools(8)
        executor = _make_tool_executor(tools)
        result = executor.select_tools("Calculate the RSI technical indicator for this stock", top_k=3)
        result_names = [t["function"]["name"] for t in result]
        assert "calculate_rsi" in result_names

    def test_fastembed_import_error_fallback(self):
        """fastembed 미설치 시 전체 도구 반환 (fallback)."""
        tools = _make_tools(8)
        executor = _make_tool_executor(tools)
        # 임베딩 초기화 안 된 상태에서 fastembed import 실패 시뮬레이션
        executor._tool_embeddings = None
        executor._embed_model = None

        import builtins
        original_import = builtins.__import__

        def _guard(name, *args, **kwargs):
            if name == "fastembed":
                raise ImportError("mock: fastembed not installed")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=_guard):
            result = executor.select_tools("stock price", top_k=3)
        assert len(result) == 8  # fallback: 전체 반환

    def test_top_k_respects_parameter(self):
        """top_k 파라미터가 정확히 반영되는지 확인."""
        tools = _make_tools(10)
        executor = _make_tool_executor(tools)
        for k in [1, 3, 5, 7]:
            result = executor.select_tools("trading strategy", top_k=k)
            assert len(result) == k

    def test_lazy_init_model_once(self):
        """모델은 첫 호출 시 한 번만 초기화."""
        tools = _make_tools(8)
        executor = _make_tool_executor(tools)
        assert executor._embed_model is None
        executor.select_tools("test query", top_k=3)
        assert executor._embed_model is not None
        model_id = id(executor._embed_model)
        executor.select_tools("another query", top_k=3)
        assert id(executor._embed_model) == model_id  # 동일 인스턴스
