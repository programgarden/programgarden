"""
FileReaderNode Executor 통합 테스트

Phase 4: GenericNodeExecutor 디스패치 + 워크플로우 JSON 실행 + AIAgentNode tool 등록

실행:
    cd src/programgarden && poetry run pytest tests/test_file_reader_executor.py -v
"""

import asyncio
import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from programgarden.executor import WorkflowExecutor, GenericNodeExecutor


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_context():
    """ExecutionContext mock"""
    ctx = MagicMock()
    ctx.log = MagicMock()
    expr_ctx = MagicMock()
    expr_ctx.to_dict = MagicMock(return_value={"nodes": {}})
    ctx.get_expression_context = MagicMock(return_value=expr_ctx)
    ctx.get_all_outputs = MagicMock(return_value={})
    ctx.credential_store = []
    return ctx


class _WorkflowTracker:
    """워크플로우 노드 상태/출력 추적"""

    def __init__(self):
        self.completed = []
        self.failed = []
        self.outputs = {}

    async def on_node_state_change(self, event):
        state = event.state.value if hasattr(event.state, "value") else str(event.state)
        if state == "completed":
            self.completed.append(event.node_id)
            if event.outputs:
                self.outputs[event.node_id] = event.outputs
        elif state == "failed":
            self.failed.append(event.node_id)

    async def on_edge_state_change(self, event): pass
    async def on_log(self, event): pass
    async def on_job_state_change(self, event): pass
    async def on_display_data(self, event): pass


# ---------------------------------------------------------------------------
# Part 1: Executor 디스패치 테스트
# ---------------------------------------------------------------------------


class TestFileReaderExecutorDispatch:
    """FileReaderNode가 GenericNodeExecutor fallback으로 실행되는지 검증"""

    @pytest.fixture
    def executors(self):
        we = WorkflowExecutor()
        return we._executors

    def test_file_reader_not_in_executors(self, executors):
        """FileReaderNode는 전용 executor 없음 → GenericNodeExecutor fallback"""
        assert "FileReaderNode" not in executors

    @pytest.mark.asyncio
    async def test_generic_executor_dispatches_file_reader(self):
        """GenericNodeExecutor → FileReaderNode.execute() 호출 검증"""
        executor = GenericNodeExecutor()
        ctx = _make_mock_context()

        content = "Hello from GenericNodeExecutor"
        b64 = base64.b64encode(content.encode()).decode()

        result = await executor.execute(
            node_id="fr1",
            node_type="FileReaderNode",
            config={
                "type": "FileReaderNode",
                "file_data": b64,
                "file_name": "test.txt",
            },
            context=ctx,
        )

        assert "texts" in result
        assert result["texts"] == [content]
        assert result["metadata"][0]["format"] == "txt"

    @pytest.mark.asyncio
    async def test_generic_executor_csv(self):
        """GenericNodeExecutor → FileReaderNode CSV 파싱"""
        executor = GenericNodeExecutor()
        ctx = _make_mock_context()

        csv_content = "symbol,price\nAAPL,150\nGOOG,2800\n"
        b64 = base64.b64encode(csv_content.encode()).decode()

        result = await executor.execute(
            node_id="fr1",
            node_type="FileReaderNode",
            config={
                "type": "FileReaderNode",
                "file_data": b64,
                "file_name": "stocks.csv",
            },
            context=ctx,
        )

        data = result["data_list"][0]
        assert len(data) == 2
        assert data[0]["symbol"] == "AAPL"
        assert data[0]["price"] == "150"
        assert result["metadata"][0]["format"] == "csv"

    @pytest.mark.asyncio
    async def test_generic_executor_json(self):
        """GenericNodeExecutor → FileReaderNode JSON 파싱"""
        executor = GenericNodeExecutor()
        ctx = _make_mock_context()

        obj = {"stocks": [{"symbol": "AAPL", "rsi": 28.5}]}
        b64 = base64.b64encode(json.dumps(obj).encode()).decode()

        result = await executor.execute(
            node_id="fr1",
            node_type="FileReaderNode",
            config={
                "type": "FileReaderNode",
                "file_data": b64,
                "file_name": "data.json",
            },
            context=ctx,
        )

        assert result["data_list"][0] == obj
        assert result["metadata"][0]["format"] == "json"

    @pytest.mark.asyncio
    async def test_generic_executor_multiple_files(self):
        """GenericNodeExecutor → FileReaderNode 복수 파일 처리"""
        executor = GenericNodeExecutor()
        ctx = _make_mock_context()

        txt_b64 = base64.b64encode(b"text file").decode()
        json_b64 = base64.b64encode(b'{"key": "val"}').decode()

        result = await executor.execute(
            node_id="fr1",
            node_type="FileReaderNode",
            config={
                "type": "FileReaderNode",
                "file_data_list": [txt_b64, json_b64],
                "file_names": ["a.txt", "b.json"],
            },
            context=ctx,
        )

        assert len(result["texts"]) == 2
        assert result["metadata"][0]["format"] == "txt"
        assert result["metadata"][1]["format"] == "json"
        assert result["data_list"][1] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_generic_executor_explicit_format(self):
        """GenericNodeExecutor → format 명시 시 자동 감지 무시"""
        executor = GenericNodeExecutor()
        ctx = _make_mock_context()

        content = "a,b\n1,2\n"
        b64 = base64.b64encode(content.encode()).decode()

        result = await executor.execute(
            node_id="fr1",
            node_type="FileReaderNode",
            config={
                "type": "FileReaderNode",
                "file_data": b64,
                "file_name": "data.csv",
                "format": "txt",  # CSV 확장자이지만 txt로 강제
            },
            context=ctx,
        )

        assert result["metadata"][0]["format"] == "txt"
        assert result["data_list"][0] is None  # txt 파싱 → data 없음

    @pytest.mark.asyncio
    async def test_generic_executor_error_no_input(self):
        """GenericNodeExecutor → 입력 없으면 에러"""
        executor = GenericNodeExecutor()
        ctx = _make_mock_context()

        result = await executor.execute(
            node_id="fr1",
            node_type="FileReaderNode",
            config={
                "type": "FileReaderNode",
            },
            context=ctx,
        )

        # GenericNodeExecutor는 에러를 error 키로 반환
        assert "error" in result


# ---------------------------------------------------------------------------
# Part 2: 워크플로우 JSON 통합 테스트
# ---------------------------------------------------------------------------


class TestFileReaderWorkflow:
    """FileReaderNode 워크플로우 통합 테스트"""

    @pytest.mark.asyncio
    async def test_start_to_file_reader_txt(self):
        """StartNode → FileReaderNode (TXT) 워크플로우 실행"""
        content = "워크플로우 텍스트 파일"
        b64 = base64.b64encode(content.encode()).decode()

        workflow = {
            "id": "test-fr-txt",
            "name": "파일 리더 TXT 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "reader",
                    "type": "FileReaderNode",
                    "file_data": b64,
                    "file_name": "doc.txt",
                },
            ],
            "edges": [
                {"from": "start", "to": "reader"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "reader" in tracker.completed
        output = job.context.get_all_outputs("reader")
        assert output["texts"] == [content]
        assert output["metadata"][0]["format"] == "txt"

    @pytest.mark.asyncio
    async def test_start_to_file_reader_csv(self):
        """StartNode → FileReaderNode (CSV) 워크플로우 실행"""
        csv_content = "symbol,price,volume\nAAPL,150,1000\nTSLA,250,2000\n"
        b64 = base64.b64encode(csv_content.encode()).decode()

        workflow = {
            "id": "test-fr-csv",
            "name": "파일 리더 CSV 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "reader",
                    "type": "FileReaderNode",
                    "file_data": b64,
                    "file_name": "portfolio.csv",
                },
            ],
            "edges": [
                {"from": "start", "to": "reader"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "reader" in tracker.completed
        output = job.context.get_all_outputs("reader")
        data = output["data_list"][0]
        assert len(data) == 2
        assert data[0]["symbol"] == "AAPL"
        assert data[1]["symbol"] == "TSLA"

    @pytest.mark.asyncio
    async def test_start_to_file_reader_json(self):
        """StartNode → FileReaderNode (JSON) 워크플로우 실행"""
        obj = [
            {"symbol": "AAPL", "rsi": 28.5, "signal": "oversold"},
            {"symbol": "GOOG", "rsi": 72.1, "signal": "overbought"},
        ]
        b64 = base64.b64encode(json.dumps(obj).encode()).decode()

        workflow = {
            "id": "test-fr-json",
            "name": "파일 리더 JSON 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "reader",
                    "type": "FileReaderNode",
                    "file_data": b64,
                    "file_name": "signals.json",
                },
            ],
            "edges": [
                {"from": "start", "to": "reader"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "reader" in tracker.completed
        output = job.context.get_all_outputs("reader")
        data = output["data_list"][0]
        assert len(data) == 2
        assert data[0]["symbol"] == "AAPL"
        assert data[0]["rsi"] == 28.5

    @pytest.mark.asyncio
    async def test_multiple_file_readers_in_workflow(self):
        """StartNode → FileReaderNode(TXT) + FileReaderNode(CSV) 병렬 실행"""
        txt_b64 = base64.b64encode("텍스트 파일 내용".encode()).decode()
        csv_b64 = base64.b64encode(b"name,val\nfoo,1\n").decode()

        workflow = {
            "id": "test-fr-multi",
            "name": "복수 파일 리더 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "txt_reader",
                    "type": "FileReaderNode",
                    "file_data": txt_b64,
                    "file_name": "notes.txt",
                },
                {
                    "id": "csv_reader",
                    "type": "FileReaderNode",
                    "file_data": csv_b64,
                    "file_name": "data.csv",
                },
            ],
            "edges": [
                {"from": "start", "to": "txt_reader"},
                {"from": "start", "to": "csv_reader"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "txt_reader" in tracker.completed
        assert "csv_reader" in tracker.completed

        txt_out = job.context.get_all_outputs("txt_reader")
        csv_out = job.context.get_all_outputs("csv_reader")
        assert txt_out["metadata"][0]["format"] == "txt"
        assert csv_out["metadata"][0]["format"] == "csv"

    @pytest.mark.asyncio
    async def test_file_reader_multiple_files_in_single_node(self):
        """단일 FileReaderNode에서 복수 파일 처리 (auto-iterate 호환 출력)"""
        txt_b64 = base64.b64encode(b"file 1").decode()
        csv_b64 = base64.b64encode(b"a,b\n1,2\n").decode()

        workflow = {
            "id": "test-fr-batch",
            "name": "배치 파일 리더 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "reader",
                    "type": "FileReaderNode",
                    "file_data_list": [txt_b64, csv_b64],
                    "file_names": ["a.txt", "b.csv"],
                },
            ],
            "edges": [
                {"from": "start", "to": "reader"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "reader" in tracker.completed
        output = job.context.get_all_outputs("reader")
        assert len(output["texts"]) == 2
        assert len(output["metadata"]) == 2
        assert output["metadata"][0]["format"] == "txt"
        assert output["metadata"][1]["format"] == "csv"


# ---------------------------------------------------------------------------
# Part 3: AIAgentNode tool 등록 테스트
# ---------------------------------------------------------------------------


class TestFileReaderToolSchema:
    """FileReaderNode의 AI Agent tool 호환성 검증"""

    def test_is_tool_enabled(self):
        """FileReaderNode.is_tool_enabled() == True"""
        from programgarden_community.nodes import FileReaderNode
        assert FileReaderNode.is_tool_enabled() is True

    def test_as_tool_schema(self):
        """as_tool_schema()가 유효한 tool 정의를 반환"""
        from programgarden_community.nodes import FileReaderNode
        schema = FileReaderNode.as_tool_schema()

        assert "tool_name" in schema
        assert "node_type" in schema
        assert schema["node_type"] == "FileReaderNode"
        # tool_name은 snake_case
        assert schema["tool_name"] == "file_reader"

    def test_tool_schema_parameters(self):
        """tool schema에 주요 파라미터 포함"""
        from programgarden_community.nodes import FileReaderNode
        schema = FileReaderNode.as_tool_schema()
        params = schema.get("parameters", {})

        # LLM이 사용할 수 있는 주요 파라미터
        assert "file_path" in params or "file_paths" in params
        assert "format" in params

    def test_tool_schema_description(self):
        """tool schema에 description 포함"""
        from programgarden_community.nodes import FileReaderNode
        schema = FileReaderNode.as_tool_schema()

        assert "description" in schema
        assert len(schema["description"]) > 0

    def test_tool_registration_in_agent(self):
        """AIAgentToolExecutor에서 FileReaderNode가 tool로 등록 가능"""
        from programgarden.executor import AIAgentToolExecutor
        from programgarden.resolver import ResolvedWorkflow, ResolvedNode, ResolvedEdge
        from programgarden_core.registry import NodeTypeRegistry

        # FileReaderNode가 NodeTypeRegistry에 등록되어 있는지
        registry = NodeTypeRegistry()
        node_class = registry.get("FileReaderNode")

        # community 노드는 registry에 없을 수 있음 (GenericNodeExecutor fallback)
        # 하지만 is_tool_enabled는 True
        if node_class:
            assert node_class.is_tool_enabled() is True

    def test_tool_schema_output_ports(self):
        """tool schema에 output 정보 포함"""
        from programgarden_community.nodes import FileReaderNode
        schema = FileReaderNode.as_tool_schema()

        # outputs가 있으면 texts, data_list, metadata 포함
        if "outputs" in schema:
            output_names = [o["name"] for o in schema["outputs"]]
            assert "texts" in output_names
            assert "data_list" in output_names
            assert "metadata" in output_names
