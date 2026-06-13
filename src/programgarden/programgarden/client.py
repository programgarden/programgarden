"""
ProgramGarden - Main Client

Provides user-friendly API
"""

from typing import Optional, List, Dict, Any, Awaitable, TypeVar
import asyncio
import concurrent.futures

from programgarden.resolver import WorkflowResolver, ValidationResult
from programgarden.executor import WorkflowExecutor
from programgarden_core.bases.listener import ExecutionListener
from programgarden_core.models.resource import ResourceLimits

_T = TypeVar("_T")


def _run_coro_sync(coro: Awaitable[_T]) -> _T:
    """Run an awaitable to completion from synchronous code without disturbing
    the caller thread's event-loop state.

    ``asyncio.run()`` creates a fresh loop and, on exit, calls
    ``asyncio.set_event_loop(None)`` — leaving the *main thread* with no current
    loop. Any later ``asyncio.get_event_loop()`` in the same process then raises
    "There is no current event loop", which leaks across test boundaries as a
    spurious failure (global-state pollution).

    Running the coroutine inside a dedicated worker thread keeps that loop
    lifecycle entirely off the caller thread, so the caller's loop state is
    untouched. It also makes the sync wrappers safe to call from within an
    already-running loop (where a direct ``asyncio.run`` would raise). The
    coroutine itself still enforces its own timeout, so this adds no unbounded
    wait.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


class ProgramGarden:
    """
    ProgramGarden Main Client

    Entry point for the node-based DSL system.

    Example:
        >>> pg = ProgramGarden()
        >>>
        >>> # Validate workflow
        >>> result = pg.validate(my_workflow)
        >>> if result.is_valid:
        ...     job = pg.run(my_workflow, context={"credential_id": "cred-001"})
        
        >>> # With resource limits
        >>> job = pg.run(
        ...     my_workflow,
        ...     resource_limits={"max_cpu_percent": 70, "max_memory_percent": 75}
        ... )
    """

    def __init__(self):
        self.resolver = WorkflowResolver()
        self.executor = WorkflowExecutor()

    def validate(self, definition: Dict[str, Any]) -> ValidationResult:
        """
        Validate workflow definition

        Args:
            definition: Workflow definition (JSON dict)

        Returns:
            ValidationResult
        """
        return self.resolver.validate(definition)

    def validate_deep(
        self,
        definition: Dict[str, Any],
        *,
        fixtures: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0,
        semantic_rules: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Deep-validate a workflow via virtual full-execution (never raises).

        Runs the workflow once, end-to-end, in ``deep_validate`` mode (a strict
        superset of ``dry_run``): no real order is ever placed, no notification is
        dispatched, realtime/data nodes return schema-shaped fixtures so the flow
        completes without waiting for live events or hitting the broker network,
        and node failures are accumulated rather than aborting on the first one.
        The result blocks (``is_valid=False``) if any node errors or the flow
        does not run to completion.

        Args:
            definition: Workflow definition (JSON dict).
            fixtures: Optional per-node fixture overrides, keyed by node id or
                node type (merged shallowly on top of the default fixture).
            timeout: Hard timeout (seconds) for the single validation pass.
            semantic_rules: Optional per-rule severity config for the configurable
                semantic/safety layer (R1~R4). ``None`` (default) skips the layer;
                pass ``programgarden.semantic_rules.STRICT_SEMANTIC_SEVERITIES`` (or
                a ``{rule_id: "error"|"warning"|"off"}`` dict) to opt in. See
                ``WorkflowExecutor.deep_validate`` for details.

        Returns:
            ValidationResult — ``errors`` carry structured per-node ErrorInfo;
            ``is_valid`` is True only when nothing failed and the flow completed.

        Example:
            >>> pg = ProgramGarden()
            >>> result = pg.validate_deep(workflow)
            >>> if not result.is_valid:
            ...     for err in result.errors:
            ...         print(err.short())
        """
        return _run_coro_sync(
            self.executor.deep_validate(
                definition,
                fixtures=fixtures,
                timeout=timeout,
                semantic_rules=semantic_rules,
            )
        )

    def run(
        self,
        definition: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        resource_limits: Optional[Dict[str, Any]] = None,
        storage_dir: Optional[str] = None,
        wait: bool = True,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute workflow

        Args:
            definition: Workflow definition
            context: Runtime parameters (symbols, dry_run, backtest options, etc.)
            secrets: Sensitive credentials (appkey, appsecret, etc.) - never logged
            resource_limits: Resource limits (max_cpu_percent, max_memory_percent, etc.)
                           If None, auto-detects from system or uses workflow's resource_limits
            storage_dir: DB/파일 저장 디렉토리. None 이면 /app/data 기본값 (GKE/Docker PVC 마운트 포인트). 로컬에서 /app/data mkdir 권한 부재 시 ./app/data 로 폴백.
            wait: Whether to wait for completion (default True)
            timeout: Maximum wait time (seconds), None for no limit

        Returns:
            Job state

        Example:
            >>> job = pg.run(
            ...     workflow,
            ...     context={"symbols": ["AAPL", "NVDA"]},
            ...     secrets={"credential_id": {"appkey": "...", "appsecret": "..."}},
            ...     storage_dir="./my_data",
            ... )

            # Dry run (검증용): 주문/Realtime/알림 노드 실제 호출 없이 시뮬레이션
            >>> job = pg.run(
            ...     workflow,
            ...     context={"dry_run": True},
            ...     wait=True,
            ...     timeout=60,
            ... )
        """
        # Parse resource_limits if provided
        limits = None
        if resource_limits:
            limits = ResourceLimits(**resource_limits)

        async def _run():
            job = await self.executor.execute(
                definition,
                context_params=context,
                secrets=secrets,
                resource_limits=limits,
                storage_dir=storage_dir,
            )

            if wait:
                # Wait for completion. Use the running loop's clock (get_running_loop
                # is always valid here — we are inside the coroutine) rather than
                # get_event_loop, which is deprecated and loop-state sensitive.
                loop = asyncio.get_running_loop()
                start_time = loop.time() if timeout else None
                while job.status in ("pending", "running"):
                    await asyncio.sleep(0.1)
                    if timeout and loop.time() - start_time > timeout:
                        break

            return job.get_state()

        return _run_coro_sync(_run())

    async def run_async(
        self,
        definition: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        resource_limits: Optional[Dict[str, Any]] = None,
        storage_dir: Optional[str] = None,
        listeners: Optional[List[ExecutionListener]] = None,
    ):
        """
        Execute workflow asynchronously

        Args:
            definition: Workflow definition
            context: Execution context parameters
            secrets: Sensitive credentials (appkey, appsecret, etc.) - never logged
            resource_limits: Resource limits (max_cpu_percent, max_memory_percent, etc.)
                           If None, auto-detects from system or uses workflow's resource_limits
            storage_dir: DB/파일 저장 디렉토리. None 이면 /app/data 기본값 (GKE/Docker PVC 마운트 포인트). 로컬에서 /app/data mkdir 권한 부재 시 ./app/data 로 폴백.
            listeners: List of ExecutionListener instances for state callbacks (Option A)

        Returns:
            WorkflowJob instance (can add more listeners via job.add_listener() - Option B)

        Example:
            # Option A: Inject at creation
            job = await pg.run_async(workflow, listeners=[MyListener()])

            # Option B: Add after creation
            job = await pg.run_async(workflow)
            job.add_listener(MyListener())

            # With custom storage directory
            job = await pg.run_async(
                workflow,
                storage_dir="./my_data",
            )
        """
        # Parse resource_limits if provided
        limits = None
        if resource_limits:
            limits = ResourceLimits(**resource_limits)

        return await self.executor.execute(
            definition,
            context_params=context,
            secrets=secrets,
            resource_limits=limits,
            storage_dir=storage_dir,
            listeners=listeners,
        )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Job state

        Args:
            job_id: Job ID

        Returns:
            Job state or None
        """
        job = self.executor.get_job(job_id)
        return job.get_state() if job else None

    def list_jobs(self) -> List[Dict[str, Any]]:
        """
        List all Jobs

        Returns:
            List of Job states
        """
        return [job.get_state() for job in self.executor.list_jobs()]

    @staticmethod
    def list_node_types(category: Optional[str] = None, include_dynamic: bool = True) -> List[Dict[str, Any]]:
        """List available node types"""
        from programgarden.tools import list_node_types
        return list_node_types(category, include_dynamic=include_dynamic)

    @staticmethod
    def list_plugins(
        category: Optional[str] = None,
        product: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List available plugins"""
        from programgarden.tools import list_plugins
        return list_plugins(category, product)

    @staticmethod
    def list_categories() -> List[Dict[str, Any]]:
        """List node categories"""
        from programgarden.tools import list_categories
        return list_categories()
