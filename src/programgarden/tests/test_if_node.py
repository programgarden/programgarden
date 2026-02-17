"""
IfNode 통합 테스트

테스트 대상:
1. IfNodeExecutor - 12개 연산자별 동작
2. 분기 스킵 로직 - true/false 브랜치 선택
3. 캐스케이딩 스킵 - 다단계 스킵 전파
4. 합류 처리 - 두 브랜치가 만나는 경우
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from programgarden.executor import IfNodeExecutor

# 테스트 타임아웃 (초)
TEST_TIMEOUT = 5


class TestIfNodeExecutorOperators:
    """IfNodeExecutor 연산자별 테스트"""

    @pytest.fixture
    def executor(self):
        return IfNodeExecutor()

    @pytest.fixture
    def mock_context(self):
        ctx = MagicMock()
        ctx.log = MagicMock()
        return ctx

    @pytest.mark.asyncio
    async def test_eq_true(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": "hello", "operator": "==", "right": "hello"},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True
        assert result["_if_branch"] == "true"

    @pytest.mark.asyncio
    async def test_eq_false(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": "hello", "operator": "==", "right": "world"},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is False
        assert result["_if_branch"] == "false"

    @pytest.mark.asyncio
    async def test_ne(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": 5, "operator": "!=", "right": 3},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_gt(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": 100, "operator": ">", "right": 50},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_gt_false(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": 50, "operator": ">", "right": 100},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_gte(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": 100, "operator": ">=", "right": 100},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_lt(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": 50, "operator": "<", "right": 100},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_lte(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": 100, "operator": "<=", "right": 100},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_in(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": "AAPL", "operator": "in", "right": ["AAPL", "TSLA", "GOOG"]},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_not_in(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": "MSFT", "operator": "not_in", "right": ["AAPL", "TSLA"]},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_contains(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": "Hello World", "operator": "contains", "right": "World"},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_not_contains(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": "Hello", "operator": "not_contains", "right": "World"},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_is_empty_true(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": [], "operator": "is_empty"},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_is_empty_false(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": [1, 2, 3], "operator": "is_empty"},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_is_not_empty(self, executor, mock_context):
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": [1, 2, 3], "operator": "is_not_empty"},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_type_coercion_string_numbers(self, executor, mock_context):
        """문자열 숫자와 숫자 비교"""
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": "100", "operator": ">", "right": 50},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_invalid_type_returns_false(self, executor, mock_context):
        """비교 불가능한 타입은 False"""
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": "abc", "operator": ">", "right": 50},
            mock_context,
        ), timeout=TEST_TIMEOUT)
        assert result["result"] is False


class TestIfNodePassthrough:
    """IfNode 데이터 pass-through 테스트"""

    @pytest.fixture
    def executor(self):
        return IfNodeExecutor()

    @pytest.fixture
    def mock_context(self):
        ctx = MagicMock()
        ctx.log = MagicMock()
        return ctx

    @pytest.mark.asyncio
    async def test_true_branch_passes_data(self, executor, mock_context):
        """조건 true → true 포트에 데이터 전달, false는 None"""
        input_data = {"balance": 1500000, "positions": []}
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": 1500000, "operator": ">=", "right": 1000000},
            mock_context,
            input_data=input_data,
        ), timeout=TEST_TIMEOUT)
        assert result["true"] == input_data
        assert result["false"] is None

    @pytest.mark.asyncio
    async def test_false_branch_passes_data(self, executor, mock_context):
        """조건 false → false 포트에 데이터 전달, true는 None"""
        input_data = {"balance": 500000, "positions": []}
        result = await asyncio.wait_for(executor.execute(
            "if1", "IfNode",
            {"left": 500000, "operator": ">=", "right": 1000000},
            mock_context,
            input_data=input_data,
        ), timeout=TEST_TIMEOUT)
        assert result["true"] is None
        assert result["false"] == input_data


class TestIfNodeEvaluateStatic:
    """IfNodeExecutor._evaluate 정적 메서드 테스트"""

    def test_all_operators(self):
        ev = IfNodeExecutor._evaluate
        # 비교 연산
        assert ev(5, "==", 5) is True
        assert ev(5, "==", 3) is False
        assert ev(5, "!=", 3) is True
        assert ev(10, ">", 5) is True
        assert ev(10, ">=", 10) is True
        assert ev(5, "<", 10) is True
        assert ev(10, "<=", 10) is True
        # 포함 연산
        assert ev("a", "in", ["a", "b"]) is True
        assert ev("c", "not_in", ["a", "b"]) is True
        assert ev("hello world", "contains", "world") is True
        assert ev("hello", "not_contains", "world") is True
        # 빈값 연산
        assert ev(None, "is_empty", None) is True
        assert ev([], "is_empty", None) is True
        assert ev("", "is_empty", None) is True
        assert ev([1], "is_not_empty", None) is True
        assert ev("text", "is_not_empty", None) is True

    def test_unknown_operator_returns_false(self):
        assert IfNodeExecutor._evaluate(1, "unknown", 1) is False
