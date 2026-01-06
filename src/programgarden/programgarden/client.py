"""
ProgramGarden - Main Client

Provides user-friendly API
"""

from typing import Optional, List, Dict, Any
import asyncio

from programgarden.resolver import WorkflowResolver, ValidationResult
from programgarden.executor import WorkflowExecutor


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
        wait: bool = True,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """
        Execute workflow

        Args:
            definition: Workflow definition
            context: Runtime parameters (symbols, dry_run, backtest options, etc.)
            secrets: Sensitive credentials (appkey, appsecret, etc.) - never logged
            wait: Whether to wait for completion (default True)
            timeout: Maximum wait time (seconds)

        Returns:
            Job state

        Example:
            >>> job = pg.run(
            ...     workflow,
            ...     context={"symbols": ["AAPL", "NVDA"]},
            ...     secrets={"credential_id": {"appkey": "...", "appsecret": "..."}},
            ... )
        """
        async def _run():
            job = await self.executor.execute(
                definition,
                context_params=context,
                secrets=secrets,
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
    ):
        """
        Execute workflow asynchronously

        Args:
            definition: Workflow definition
            context: Execution context

        Returns:
            WorkflowJob instance
        """
        return await self.executor.execute(definition, context)

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
