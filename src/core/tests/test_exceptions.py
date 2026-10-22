"""programgarden_core.exceptions 단위 테스트.

MissingDependencyError 는 선택적 heavy extra(portfolio/perf) 미설치·부분설치를
silent no-op 없이 명시 에러로 올리는 계약을 강제한다.
"""

from programgarden_core.exceptions import (
    ExecutionError,
    MissingDependencyError,
    ProgramGardenError,
)


class TestMissingDependencyError:
    def test_subclass_of_execution_error(self):
        assert issubclass(MissingDependencyError, ExecutionError)
        assert issubclass(MissingDependencyError, ProgramGardenError)

    def test_populates_attributes_and_details(self):
        err = MissingDependencyError(
            "quantstats not installed",
            extra="perf",
            package="quantstats",
            install_hint="pip install 'programgarden-community[perf]'",
            transitive=True,
            node_id="perf-1",
        )
        # 인스턴스 속성
        assert err.extra == "perf"
        assert err.package == "quantstats"
        assert err.install_hint == "pip install 'programgarden-community[perf]'"
        assert err.transitive is True
        assert err.node_id == "perf-1"
        # 구조화 details (AI 챗봇 소비)
        assert err.details["code"] == "MISSING_OPTIONAL_DEPENDENCY"
        assert err.details["extra"] == "perf"
        assert err.details["package"] == "quantstats"
        assert err.details["install_hint"] == "pip install 'programgarden-community[perf]'"
        assert err.details["transitive"] is True
        assert str(err) == "quantstats not installed"

    def test_default_transitive_false(self):
        err = MissingDependencyError(
            "pyportfolioopt not installed",
            extra="portfolio",
            package="pyportfolioopt",
        )
        assert err.transitive is False
        assert err.details["transitive"] is False
        assert err.details["install_hint"] is None
        assert err.node_id is None

    def test_extra_details_merge(self):
        err = MissingDependencyError(
            "broken",
            extra="perf",
            details={"hint2": "reinstall"},
        )
        # 기본 code 키는 유지되고 추가 details 는 병합된다
        assert err.details["code"] == "MISSING_OPTIONAL_DEPENDENCY"
        assert err.details["hint2"] == "reinstall"
