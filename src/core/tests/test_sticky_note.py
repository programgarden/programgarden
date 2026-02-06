"""
StickyNote 모델 테스트

워크플로우 메모 (비실행 주석) 기능 검증
"""

import pytest
from pydantic import ValidationError

from programgarden_core.models.workflow import StickyNote, NotePosition, WorkflowDefinition
from programgarden_core.models.edge import Edge


class TestStickyNoteCreation:
    """StickyNote 기본 생성 테스트"""

    def test_basic_creation(self):
        """기본 필드로 생성"""
        note = StickyNote(id="note-1", content="## 메모")
        assert note.id == "note-1"
        assert note.content == "## 메모"
        assert note.color == 0
        assert note.width == 300
        assert note.height == 200
        assert note.position.x == 0.0
        assert note.position.y == 0.0

    def test_full_creation(self):
        """모든 필드 지정"""
        note = StickyNote(
            id="note-2",
            content="# RSI 전략\n- 과매도: < 30",
            color=3,
            width=400,
            height=250,
            position={"x": 100, "y": 200},
        )
        assert note.color == 3
        assert note.width == 400
        assert note.position.x == 100
        assert note.position.y == 200

    def test_empty_content(self):
        """빈 content 허용"""
        note = StickyNote(id="note-1")
        assert note.content == ""


class TestStickyNoteValidation:
    """StickyNote 필드 검증 테스트"""

    def test_color_min_boundary(self):
        """color 최솟값 (0) 허용"""
        note = StickyNote(id="note-1", color=0)
        assert note.color == 0

    def test_color_max_boundary(self):
        """color 최댓값 (7) 허용"""
        note = StickyNote(id="note-1", color=7)
        assert note.color == 7

    def test_color_below_min(self):
        """color 음수 → ValidationError"""
        with pytest.raises(ValidationError):
            StickyNote(id="note-1", color=-1)

    def test_color_above_max(self):
        """color 8 이상 → ValidationError"""
        with pytest.raises(ValidationError):
            StickyNote(id="note-1", color=8)

    def test_width_min_boundary(self):
        """width 최솟값 (100) 허용"""
        note = StickyNote(id="note-1", width=100)
        assert note.width == 100

    def test_width_below_min(self):
        """width 100 미만 → ValidationError"""
        with pytest.raises(ValidationError):
            StickyNote(id="note-1", width=99)

    def test_height_min_boundary(self):
        """height 최솟값 (80) 허용"""
        note = StickyNote(id="note-1", height=80)
        assert note.height == 80

    def test_height_below_min(self):
        """height 80 미만 → ValidationError"""
        with pytest.raises(ValidationError):
            StickyNote(id="note-1", height=79)


class TestStickyNoteSerialization:
    """JSON 직렬화/역직렬화 테스트"""

    def test_json_roundtrip(self):
        """model_dump → 재생성 라운드트립"""
        note = StickyNote(
            id="note-1",
            content="## 테스트",
            color=3,
            width=350,
            height=180,
            position={"x": 50, "y": 100},
        )
        data = note.model_dump()
        restored = StickyNote(**data)
        assert restored == note

    def test_model_dump_structure(self):
        """model_dump 출력 구조 확인"""
        note = StickyNote(id="note-1", content="메모")
        data = note.model_dump()
        assert set(data.keys()) == {"id", "content", "color", "width", "height", "position"}
        assert data["position"] == {"x": 0.0, "y": 0.0}


class TestWorkflowWithNotes:
    """WorkflowDefinition에 notes 필드 통합 테스트"""

    def test_workflow_with_notes(self):
        """notes 포함 워크플로우 생성"""
        workflow = WorkflowDefinition(
            id="test",
            name="테스트",
            nodes=[{"id": "start", "type": "StartNode"}],
            notes=[
                StickyNote(id="note-1", content="전략 설명"),
                StickyNote(id="note-2", content="주의사항"),
            ],
        )
        assert len(workflow.notes) == 2
        assert workflow.notes[0].content == "전략 설명"

    def test_workflow_without_notes(self):
        """notes 없는 워크플로우 → 빈 배열 (하위 호환)"""
        workflow = WorkflowDefinition(id="test", name="테스트", nodes=[])
        assert workflow.notes == []

    def test_notes_not_affect_dag_validation(self):
        """notes는 DAG 검증에 영향 없음"""
        workflow = WorkflowDefinition(
            id="test",
            name="테스트",
            nodes=[{"id": "start", "type": "StartNode"}],
            edges=[],
            notes=[StickyNote(id="note-1", content="메모")],
        )
        errors = workflow.validate_structure()
        # StartNode 관련 에러만 있어야 하고, notes 관련 에러는 없어야 함
        assert all("메모" not in e and "note" not in e.lower() for e in errors)

    def test_workflow_json_roundtrip_with_notes(self):
        """notes 포함 워크플로우 JSON 라운드트립"""
        workflow = WorkflowDefinition(
            id="test",
            name="테스트",
            nodes=[{"id": "start", "type": "StartNode"}],
            notes=[StickyNote(id="note-1", content="## 메모", color=2)],
        )
        data = workflow.model_dump()
        restored = WorkflowDefinition(**data)
        assert len(restored.notes) == 1
        assert restored.notes[0].content == "## 메모"
        assert restored.notes[0].color == 2

    def test_workflow_from_dict_with_notes(self):
        """딕셔너리에서 notes 포함 워크플로우 생성 (클라이언트 JSON 시뮬레이션)"""
        raw = {
            "id": "test",
            "name": "테스트",
            "nodes": [{"id": "start", "type": "StartNode"}],
            "notes": [
                {
                    "id": "note-1",
                    "content": "RSI 전략 메모",
                    "color": 1,
                    "position": {"x": 300, "y": 50},
                }
            ],
        }
        workflow = WorkflowDefinition(**raw)
        assert workflow.notes[0].id == "note-1"
        assert workflow.notes[0].position.x == 300
