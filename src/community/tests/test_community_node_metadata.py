"""
트랙 A — community-side 노드 메타데이터 enforcement.

core 의 test_node_schema_ai_fields.py / test_node_version_metadata.py 는 community
미설치 시 trivially pass(또는 community 를 import 조차 안 함)하므로, 신규 community
노드의 8 ClassVar(5 AI-meta + 3 version)을 **실효 강제**하지 못한다. 본 테스트가
community 내부에서 등록 community 노드 전수를 순회해 그 강제를 대체한다.

- core → community 역참조 없음(community 는 core 만 참조).
- 3 version ClassVar 은 `cls.__dict__` 직접 선언(상속 fallback 차단).
- 5 AI-meta ClassVar 존재 + shape.
- PerformanceReportNode 등 신규 노드 누락 시 즉시 fail.
"""

import re

import pytest

import programgarden_community.nodes as community_nodes
from programgarden_community.nodes_registry import get_community_node_list

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# 등록/노출 community 노드 클래스 전수 (__all__ 기준)
NODE_CLASSES = [getattr(community_nodes, name) for name in community_nodes.__all__]


def test_all_listed_types_are_exported():
    """get_community_node_list() 의 모든 type 이 nodes.__all__ 로 노출된다(등록 드리프트 차단)."""
    exported = {cls.__name__ for cls in NODE_CLASSES}
    listed = {entry["type"] for entry in get_community_node_list()}
    assert listed <= exported, f"registered-but-unexported nodes: {listed - exported}"


def test_at_least_five_nodes():
    """PerformanceReportNode 추가로 최소 5개."""
    assert len(NODE_CLASSES) >= 5


@pytest.mark.parametrize("cls", NODE_CLASSES, ids=[c.__name__ for c in NODE_CLASSES])
class TestNodeMetadataEnforcement:
    # --- version metadata (직접 선언 강제) ---
    def test_version_classvars_declared_directly(self, cls):
        for attr in ("_version", "_updated_at", "_change_note"):
            assert attr in cls.__dict__, f"{cls.__name__}: {attr} must be declared on the class body (no inherited fallback)"

    def test_version_formats(self, cls):
        assert SEMVER.match(cls._version), f"{cls.__name__}._version not SemVer: {cls._version!r}"
        assert ISO_DATE.match(cls._updated_at), f"{cls.__name__}._updated_at not ISO date: {cls._updated_at!r}"
        note = cls._change_note
        assert note is None or (isinstance(note, str) and len(note) <= 120), \
            f"{cls.__name__}._change_note must be None or str<=120: {note!r}"

    # --- AI metadata (5 ClassVar) ---
    def test_usage(self, cls):
        usage = cls._usage
        assert isinstance(usage, dict)
        for key in ("when_to_use", "when_not_to_use", "typical_scenarios"):
            assert key in usage and isinstance(usage[key], list) and usage[key], \
                f"{cls.__name__}._usage.{key} missing/empty"

    def test_features(self, cls):
        assert isinstance(cls._features, list) and len(cls._features) >= 2, \
            f"{cls.__name__}._features needs >=2 bullets"

    def test_anti_patterns(self, cls):
        aps = cls._anti_patterns
        assert isinstance(aps, list) and aps, f"{cls.__name__}._anti_patterns empty"
        for ap in aps:
            assert {"pattern", "reason", "alternative"} <= set(ap), \
                f"{cls.__name__}._anti_patterns item missing keys: {ap}"

    def test_examples(self, cls):
        examples = cls._examples
        assert isinstance(examples, list) and len(examples) >= 2, \
            f"{cls.__name__}._examples needs >=2"
        for ex in examples:
            assert "workflow_snippet" in ex and isinstance(ex["workflow_snippet"], dict), \
                f"{cls.__name__}._examples item missing workflow_snippet"
            assert ex["workflow_snippet"].get("nodes"), \
                f"{cls.__name__} snippet missing nodes"

    def test_node_guide(self, cls):
        guide = cls._node_guide
        assert isinstance(guide, dict)
        for key in ("input_handling", "output_consumption", "common_combinations", "pitfalls"):
            assert key in guide, f"{cls.__name__}._node_guide.{key} missing"
        assert isinstance(guide["common_combinations"], list)
        assert isinstance(guide["pitfalls"], list)
