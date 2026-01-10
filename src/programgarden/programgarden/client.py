"""
ProgramGarden - Main Client

Provides user-friendly API
"""

from typing import Optional, List, Dict, Any
import asyncio

from programgarden.resolver import WorkflowResolver, ValidationResult
from programgarden.executor import WorkflowExecutor
from programgarden_core.bases.listener import ExecutionListener
from programgarden_core.models.resource import ResourceLimits


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

    def run(
        self,
        definition: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        resource_limits: Optional[Dict[str, Any]] = None,
        wait: bool = True,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """
        Execute workflow

        Args:
            definition: Workflow definition
            context: Runtime parameters (symbols, dry_run, backtest options, etc.)
            secrets: Sensitive credentials (appkey, appsecret, etc.) - never logged
            resource_limits: Resource limits (max_cpu_percent, max_memory_percent, etc.)
                           If None, auto-detects from system or uses workflow's resource_limits
            wait: Whether to wait for completion (default True)
            timeout: Maximum wait time (seconds)

        Returns:
            Job state

        Example:
            >>> job = pg.run(
            ...     workflow,
            ...     context={"symbols": ["AAPL", "NVDA"]},
            ...     secrets={"credential_id": {"appkey": "...", "appsecret": "..."}},
            ...     resource_limits={"max_cpu_percent": 70},
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
            )
            
            if wait:
                # Wait for completion
                import asyncio
                start_time = asyncio.get_event_loop().time()
                while job.status in ("pending", "running"):
                    await asyncio.sleep(0.1)
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        break
            
            return job.get_state()

        return asyncio.run(_run())

    async def run_async(
        self,
        definition: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        resource_limits: Optional[Dict[str, Any]] = None,
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
            listeners: List of ExecutionListener instances for state callbacks (Option A)

        Returns:
            WorkflowJob instance (can add more listeners via job.add_listener() - Option B)
        
        Example:
            # Option A: Inject at creation
            job = await pg.run_async(workflow, listeners=[MyListener()])
            
            # Option B: Add after creation
            job = await pg.run_async(workflow)
            job.add_listener(MyListener())
            
            # With resource limits
            job = await pg.run_async(
                workflow,
                resource_limits={"max_cpu_percent": 70, "throttle_strategy": "conservative"}
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
    def list_node_types(category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available node types"""
        from programgarden.tools import list_node_types
        return list_node_types(category)

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
