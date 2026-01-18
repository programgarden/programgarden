"""워크플로우 JSON 파일 검증 테스트"""

import json
from pathlib import Path
import pytest
from programgarden_core.nodes.display import DisplayNode


WORKFLOWS_DIR = Path(__file__).parent.parent / "examples" / "workflows"


def get_workflow_files():
    """워크플로우 JSON 파일 목록"""
    return list(WORKFLOWS_DIR.glob("*.json"))


@pytest.mark.parametrize("json_file", get_workflow_files(), ids=lambda f: f.name)
def test_workflow_json_valid(json_file):
    """워크플로우 JSON 파일 유효성 검증"""
    with open(json_file) as f:
        workflow = json.load(f)
    
    assert "nodes" in workflow, "nodes 필드 필수"
    assert "edges" in workflow, "edges 필드 필수"


def test_displaynode_schema_compatibility():
    """DisplayNode 스키마 호환성 검증"""
    display_nodes_tested = 0
    errors = []

    for json_file in get_workflow_files():
        with open(json_file) as f:
            workflow = json.load(f)
        
        for node in workflow.get("nodes", []):
            if node.get("type") == "DisplayNode":
                display_nodes_tested += 1
                try:
                    # DisplayNode 필드만 추출하여 검증
                    node_data = {
                        k: v for k, v in node.items()
                        if k not in ("type", "category", "position")
                    }
                    DisplayNode(**node_data)
                except Exception as e:
                    errors.append((json_file.name, node.get("id"), str(e)))

    print(f"\n검증된 DisplayNode: {display_nodes_tested}개")
    
    if errors:
        for name, node_id, err in errors:
            print(f"  ❌ {name} / {node_id}: {err}")
    
    assert not errors, f"DisplayNode 스키마 오류: {errors}"


def test_new_signal_fields_optional():
    """새 signal_field, side_field는 optional - 기존 워크플로우 호환"""
    # signal_field, side_field 없이 DisplayNode 생성 가능해야 함
    dn = DisplayNode(
        id="test_display",
        chart_type="line",
        title="Test Chart",
        data="{{ nodes.test.data }}",
        x_field="date",
        y_field="value",
    )
    
    assert dn.signal_field is None
    assert dn.side_field is None


def test_signal_fields_with_values():
    """signal_field, side_field 값 설정 테스트"""
    dn = DisplayNode(
        id="test_display",
        chart_type="multi_line",
        title="Signal Chart",
        data="{{ nodes.condition.values }}",
        x_field="date",
        y_field="close",
        series_key="symbol",
        signal_field="signal",
        side_field="side",
    )
    
    assert dn.signal_field == "signal"
    assert dn.side_field == "side"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
