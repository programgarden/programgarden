"""
Executor **kwargs 호환성 테스트

모든 NodeExecutorBase 서브클래스의 execute() 메서드가
**kwargs를 수용하는지 검증합니다.

execute_node()가 workflow, _executors 등 추가 인자를 일괄 전달하므로,
**kwargs가 없는 executor는 TypeError를 유발합니다.
"""

import inspect

import pytest

from programgarden.executor import WorkflowExecutor, NodeExecutorBase


class TestExecutorKwargsCompat:
    """모든 등록된 executor가 **kwargs를 받을 수 있는지 검증"""

    @pytest.fixture
    def all_executors(self):
        """WorkflowExecutor에 등록된 모든 executor 인스턴스"""
        we = WorkflowExecutor()
        return we._init_executors()

    def test_all_executors_accept_kwargs(self, all_executors):
        """
        모든 executor.execute()가 임의의 keyword argument를 수용해야 한다.

        execute_node()가 workflow=, _executors= 등을 일괄 전달하므로,
        VAR_KEYWORD (**kwargs) 파라미터가 없으면 TypeError 발생.
        """
        failures = []

        for node_type, executor in all_executors.items():
            sig = inspect.signature(executor.execute)
            has_var_keyword = any(
                p.kind == inspect.Parameter.VAR_KEYWORD
                for p in sig.parameters.values()
            )
            if not has_var_keyword:
                failures.append(
                    f"{node_type} -> {type(executor).__name__}.execute() 에 **kwargs 누락"
                )

        assert not failures, (
            "다음 executor에 **kwargs가 없습니다. "
            "execute_node()에서 전달하는 추가 인자(workflow, _executors 등)를 "
            "수용하려면 **kwargs를 추가하세요:\n"
            + "\n".join(f"  - {f}" for f in failures)
        )

    def test_base_class_accepts_kwargs(self):
        """NodeExecutorBase.execute()가 **kwargs를 수용해야 한다"""
        sig = inspect.signature(NodeExecutorBase.execute)
        has_var_keyword = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        )
        assert has_var_keyword, "NodeExecutorBase.execute()에 **kwargs가 없습니다"
