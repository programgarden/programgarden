"""
ProgramGarden - 메인 클라이언트

사용자 친화적 API 제공
"""

from typing import Optional, List, Dict, Any
import asyncio

from programgarden.resolver import WorkflowResolver, ValidationResult
from programgarden.executor import WorkflowExecutor


class ProgramGarden:
    """
    ProgramGarden 메인 클라이언트

    노드 기반 DSL 시스템의 진입점.

    Example:
        >>> pg = ProgramGarden()
        >>>
        >>> # 워크플로우 검증
        >>> result = pg.validate(my_workflow)
        >>> if result.is_valid:
        ...     job = pg.run(my_workflow, context={"credential_id": "cred-001"})
    """

    def __init__(self):
        self.resolver = WorkflowResolver()
        self.executor = WorkflowExecutor()

    def validate(self, definition: Dict[str, Any]) -> ValidationResult:
        """
        워크플로우 정의 검증

        Args:
            definition: 워크플로우 정의 (JSON dict)

        Returns:
            ValidationResult
        """
        return self.resolver.validate(definition)

    def run(
        self,
        definition: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        워크플로우 실행

        Args:
            definition: 워크플로우 정의
            context: 실행 컨텍스트 (credential_id, symbols 등)

        Returns:
            Job 상태
        """
        async def _run():
            job = await self.executor.execute(definition, context)
            return job.get_state()

        return asyncio.run(_run())

    async def run_async(
        self,
        definition: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        워크플로우 비동기 실행

        Args:
            definition: 워크플로우 정의
            context: 실행 컨텍스트

        Returns:
            WorkflowJob 인스턴스
        """
        return await self.executor.execute(definition, context)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Job 상태 조회

        Args:
            job_id: Job ID

        Returns:
            Job 상태 또는 None
        """
        job = self.executor.get_job(job_id)
        return job.get_state() if job else None

    def list_jobs(self) -> List[Dict[str, Any]]:
        """
        모든 Job 목록 조회

        Returns:
            Job 상태 목록
        """
        return [job.get_state() for job in self.executor.list_jobs()]

    @staticmethod
    def list_node_types(category: Optional[str] = None) -> List[Dict[str, Any]]:
        """노드 타입 목록 조회"""
        from programgarden.tools import list_node_types
        return list_node_types(category)

    @staticmethod
    def list_plugins(
        category: Optional[str] = None,
        product: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """플러그인 목록 조회"""
        from programgarden.tools import list_plugins
        return list_plugins(category, product)

    @staticmethod
    def list_categories() -> List[Dict[str, Any]]:
        """노드 카테고리 목록 조회"""
        from programgarden.tools import list_categories
        return list_categories()
