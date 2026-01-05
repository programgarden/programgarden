"""
ProgramGarden - WorkflowExecutor

워크플로우 실행 엔진
- validate() → compile() → execute() 라이프사이클
- Stateful 장기 실행 지원
- Graceful Restart 지원
"""

from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime
import asyncio
import uuid

from programgarden.resolver import WorkflowResolver, ResolvedWorkflow, ValidationResult
from programgarden.context import ExecutionContext


class NodeExecutorBase:
    """노드 실행기 베이스 클래스"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """
        노드 실행

        Returns:
            출력 포트별 값 딕셔너리
        """
        raise NotImplementedError


class StartNodeExecutor(NodeExecutorBase):
    """StartNode 실행기"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        context.log("info", "Workflow started", node_id)
        return {"start": True}


class ScheduleNodeExecutor(NodeExecutorBase):
    """ScheduleNode 실행기"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        # 스케줄 트리거 (실제 구현에서는 크론 스케줄러 사용)
        cron = config.get("cron", "*/5 * * * *")
        context.log("info", f"Schedule triggered: {cron}", node_id)
        return {"trigger": True}


class WatchlistNodeExecutor(NodeExecutorBase):
    """WatchlistNode 실행기"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        symbols = config.get("symbols", [])
        context.log("info", f"Watchlist symbols: {symbols}", node_id)
        return {"symbols": symbols}


class BrokerNodeExecutor(NodeExecutorBase):
    """BrokerNode 실행기"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        provider = config.get("provider", "ls-sec.co.kr")
        product = config.get("product", "overseas_stock")
        context.log("info", f"Broker connected: {provider} ({product})", node_id)
        return {"connection": {"provider": provider, "product": product}}


class ConditionNodeExecutor(NodeExecutorBase):
    """ConditionNode 실행기 (플러그인 기반)"""

    async def execute(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        plugin: Optional[Callable] = None,
        plugin_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # 입력 데이터 수집
        symbols = context.get_input(node_id, "symbols") or []
        price_data = context.get_input(node_id, "price_data") or {}

        # 플러그인 실행 (있는 경우)
        passed_symbols = []
        values = {}

        if plugin:
            # 플러그인 실행 로직
            for symbol in symbols:
                # TODO: 실제 플러그인 실행
                passed_symbols.append(symbol)
                values[symbol] = {"result": True}
        else:
            # 플러그인 없으면 모든 종목 통과
            passed_symbols = symbols

        context.log(
            "info",
            f"Condition evaluated: {len(passed_symbols)}/{len(symbols)} passed",
            node_id,
        )

        return {
            "result": len(passed_symbols) > 0,
            "passed_symbols": passed_symbols,
            "failed_symbols": [s for s in symbols if s not in passed_symbols],
            "values": values,
        }


class WorkflowExecutor:
    """
    워크플로우 실행 엔진

    Stateful 장기 실행:
    - 24시간 연속 실행 지원
    - 포지션/잔고 상태 유지
    - Graceful Restart 지원
    """

    def __init__(self):
        self.resolver = WorkflowResolver()
        self._jobs: Dict[str, "WorkflowJob"] = {}
        self._executors: Dict[str, NodeExecutorBase] = self._init_executors()

    def _init_executors(self) -> Dict[str, NodeExecutorBase]:
        """노드 타입별 실행기 초기화"""
        return {
            "StartNode": StartNodeExecutor(),
            "ScheduleNode": ScheduleNodeExecutor(),
            "WatchlistNode": WatchlistNodeExecutor(),
            "BrokerNode": BrokerNodeExecutor(),
            "ConditionNode": ConditionNodeExecutor(),
            # TODO: 나머지 노드 실행기 구현
        }

    def validate(self, definition: Dict[str, Any]) -> ValidationResult:
        """
        워크플로우 검증

        Args:
            definition: 워크플로우 정의 (JSON dict)
        """
        return self.resolver.validate(definition)

    def compile(
        self,
        definition: Dict[str, Any],
        context_params: Optional[Dict[str, Any]] = None,
    ) -> tuple[Optional[ResolvedWorkflow], ValidationResult]:
        """
        워크플로우 컴파일 (실행 객체 변환)

        Args:
            definition: 워크플로우 정의
            context_params: 실행 컨텍스트 파라미터
        """
        return self.resolver.resolve(definition, context_params)

    async def execute(
        self,
        definition: Dict[str, Any],
        context_params: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
    ) -> "WorkflowJob":
        """
        워크플로우 실행

        Args:
            definition: 워크플로우 정의
            context_params: 실행 컨텍스트 파라미터
            job_id: Job ID (없으면 자동 생성)
        """
        # 컴파일
        resolved, validation = self.compile(definition, context_params)
        if not validation.is_valid:
            raise ValueError(f"Workflow validation failed: {validation.errors}")

        # Job 생성
        job_id = job_id or f"job-{uuid.uuid4().hex[:8]}"
        context = ExecutionContext(
            job_id=job_id,
            workflow_id=resolved.workflow_id,
            context_params=context_params or {},
        )

        job = WorkflowJob(
            job_id=job_id,
            workflow=resolved,
            context=context,
            executor=self,
        )

        self._jobs[job_id] = job

        # 실행 시작
        await job.start()

        return job

    async def execute_node(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        context: ExecutionContext,
        plugin: Optional[Callable] = None,
        plugin_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """단일 노드 실행"""
        executor = self._executors.get(node_type)

        if not executor:
            context.log("warning", f"No executor for node type: {node_type}", node_id)
            return {}

        # ConditionNode는 플러그인 파라미터 추가
        if node_type == "ConditionNode":
            return await executor.execute(
                node_id=node_id,
                node_type=node_type,
                config=config,
                context=context,
                plugin=plugin,
                plugin_params=plugin_params,
            )

        return await executor.execute(
            node_id=node_id,
            node_type=node_type,
            config=config,
            context=context,
        )

    def get_job(self, job_id: str) -> Optional["WorkflowJob"]:
        """Job 조회"""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List["WorkflowJob"]:
        """모든 Job 목록"""
        return list(self._jobs.values())


class WorkflowJob:
    """
    워크플로우 실행 인스턴스

    Stateful: 포지션/잔고 상태 유지
    """

    def __init__(
        self,
        job_id: str,
        workflow: ResolvedWorkflow,
        context: ExecutionContext,
        executor: WorkflowExecutor,
    ):
        self.job_id = job_id
        self.workflow = workflow
        self.context = context
        self.executor = executor

        # 상태
        self.status = "pending"
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        # 통계
        self.stats = {
            "conditions_evaluated": 0,
            "orders_placed": 0,
            "orders_filled": 0,
            "errors_count": 0,
        }

        # 실행 태스크
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """실행 시작"""
        self.status = "running"
        self.started_at = datetime.utcnow()
        self.context.start()

        # 비동기 실행
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        """워크플로우 실행 루프"""
        try:
            # 토폴로지 순서대로 노드 실행
            for node_id in self.workflow.execution_order:
                if not self.context.is_running:
                    break

                # 일시정지 대기
                while self.context.is_paused:
                    await asyncio.sleep(0.1)

                node = self.workflow.nodes.get(node_id)
                if not node:
                    continue

                # 입력 연결 (엣지에서 값 가져오기)
                for edge in self.workflow.edges:
                    if edge.to_node_id == node_id:
                        value = self.context.get_output(
                            edge.from_node_id,
                            edge.from_port,
                        )
                        if value is not None:
                            # 입력 값을 노드에 연결
                            input_port = edge.to_port or "input"
                            self.context.set_output(
                                f"_input_{node_id}",
                                input_port,
                                value,
                            )

                # 노드 실행
                outputs = await self.executor.execute_node(
                    node_id=node_id,
                    node_type=node.node_type,
                    config=node.config,
                    context=self.context,
                    plugin=node.plugin,
                    plugin_params=node.plugin_params,
                )

                # 출력 저장
                for port_name, value in outputs.items():
                    self.context.set_output(node_id, port_name, value)

            self.status = "completed"
            self.completed_at = datetime.utcnow()

        except Exception as e:
            self.status = "failed"
            self.stats["errors_count"] += 1
            self.context.log("error", str(e))

    async def pause(self) -> None:
        """일시정지"""
        self.status = "paused"
        self.context.pause()

    async def resume(self) -> None:
        """재개"""
        self.status = "running"
        self.context.resume()

    async def cancel(self) -> None:
        """취소"""
        self.status = "cancelled"
        self.context.stop()
        if self._task:
            self._task.cancel()

    def get_state(self) -> Dict[str, Any]:
        """상태 스냅샷"""
        return {
            "job_id": self.job_id,
            "workflow_id": self.workflow.workflow_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stats": self.stats,
            "logs": self.context.get_logs(limit=50),
        }
