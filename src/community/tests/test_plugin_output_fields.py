"""
67개 플러그인 output_fields 일괄 검증 테스트

- 모든 플러그인에 output_fields 존재
- output_fields 내 type/description 필수값 검증
- output_fields가 비어있지 않은지 검증
"""

import pytest
from programgarden_core.registry import PluginRegistry
from programgarden_core.registry.plugin_registry import PluginSchema


VALID_TYPES = {"float", "int", "str", "bool", "list", "dict"}

# 공통 필드 (output_fields에 포함하면 안 됨)
COMMON_FIELDS = {"symbol", "exchange"}


@pytest.fixture(scope="module")
def all_schemas():
    """모든 플러그인 스키마 로드"""
    PluginRegistry._instance = None
    from programgarden_community.plugins import register_all_plugins
    register_all_plugins()

    registry = PluginRegistry()
    schemas = registry.list_plugins()
    yield schemas

    PluginRegistry._instance = None


class TestAllPluginsHaveOutputFields:
    """67개 플러그인 output_fields 존재 일괄 검증"""

    def test_plugin_count(self, all_schemas):
        """67개 플러그인이 등록되어 있음"""
        assert len(all_schemas) == 67, f"Expected 67, got {len(all_schemas)}"

    def test_all_plugins_have_output_fields(self, all_schemas):
        """모든 플러그인에 output_fields 속성 존재"""
        for schema in all_schemas:
            assert hasattr(schema, "output_fields"), (
                f"{schema.id}: output_fields 속성 없음"
            )

    def test_all_plugins_have_nonempty_output_fields(self, all_schemas):
        """모든 플러그인의 output_fields가 비어있지 않음"""
        empty = [s.id for s in all_schemas if not s.output_fields]
        assert len(empty) == 0, f"output_fields가 비어있는 플러그인: {empty}"


class TestOutputFieldsStructure:
    """output_fields 내부 구조 검증"""

    def test_all_fields_have_type(self, all_schemas):
        """모든 output_fields에 type 키 존재"""
        missing = []
        for schema in all_schemas:
            for field_name, field_meta in schema.output_fields.items():
                if "type" not in field_meta:
                    missing.append(f"{schema.id}.{field_name}")
        assert len(missing) == 0, f"type 누락: {missing}"

    def test_all_fields_have_description(self, all_schemas):
        """모든 output_fields에 description 키 존재"""
        missing = []
        for schema in all_schemas:
            for field_name, field_meta in schema.output_fields.items():
                if "description" not in field_meta:
                    missing.append(f"{schema.id}.{field_name}")
        assert len(missing) == 0, f"description 누락: {missing}"

    def test_all_types_are_valid(self, all_schemas):
        """모든 type 값이 유효한 Python 타입"""
        invalid = []
        for schema in all_schemas:
            for field_name, field_meta in schema.output_fields.items():
                if field_meta.get("type") not in VALID_TYPES:
                    invalid.append(
                        f"{schema.id}.{field_name}: {field_meta.get('type')}"
                    )
        assert len(invalid) == 0, f"유효하지 않은 type: {invalid}"

    def test_no_common_fields_in_output_fields(self, all_schemas):
        """symbol, exchange 등 공통 필드가 output_fields에 포함되지 않음"""
        violations = []
        for schema in all_schemas:
            common_in_output = COMMON_FIELDS & set(schema.output_fields.keys())
            if common_in_output:
                violations.append(f"{schema.id}: {common_in_output}")
        assert len(violations) == 0, f"공통 필드 포함: {violations}"

    def test_descriptions_are_nonempty(self, all_schemas):
        """description이 빈 문자열이 아님"""
        empty = []
        for schema in all_schemas:
            for field_name, field_meta in schema.output_fields.items():
                desc = field_meta.get("description", "")
                if not desc.strip():
                    empty.append(f"{schema.id}.{field_name}")
        assert len(empty) == 0, f"빈 description: {empty}"


class TestToLocalizedDictIncludesOutputFields:
    """to_localized_dict()에서 output_fields 반환 확인"""

    def test_localized_dict_has_output_fields(self, all_schemas):
        """모든 플러그인의 to_localized_dict()에 output_fields 포함"""
        for schema in all_schemas:
            result = schema.to_localized_dict("en")
            assert "output_fields" in result, f"{schema.id}: output_fields 누락"

    def test_localized_dict_output_fields_matches(self, all_schemas):
        """to_localized_dict() output_fields와 원본이 동일"""
        for schema in all_schemas:
            result = schema.to_localized_dict("en")
            assert result["output_fields"] == schema.output_fields, (
                f"{schema.id}: output_fields 불일치"
            )


class TestGetOutputFieldDescription:
    """get_output_field_description() 메서드 검증"""

    def test_all_fields_retrievable(self, all_schemas):
        """모든 output_fields의 description을 get_output_field_description()으로 조회 가능"""
        for schema in all_schemas:
            for field_name, field_meta in schema.output_fields.items():
                desc = schema.get_output_field_description(field_name)
                assert desc == field_meta["description"], (
                    f"{schema.id}.{field_name}: expected '{field_meta['description']}', got '{desc}'"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
