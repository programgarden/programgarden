"""
Pydantic 기반 노드 타입 서버
json_dynamic_widget v12.0.0+6 형식으로 UI 반환
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from typing import Optional, List, Any, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================
# 1. 노드 필드 타입 정의
# ============================================================

class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    TEXT = "text"  # 여러줄 텍스트
    SELECT = "select"  # 드롭다운
    COLOR = "color"
    FILE = "file"


class FieldOption(BaseModel):
    """SELECT 필드의 옵션"""
    label: str
    value: str


class NodeField(BaseModel):
    """노드의 필드 정의"""
    name: str
    label: str
    field_type: FieldType
    default_value: Optional[Any] = None
    placeholder: Optional[str] = None
    required: bool = False
    options: Optional[List[FieldOption]] = None  # SELECT 타입용
    min_value: Optional[float] = None  # 숫자 타입용
    max_value: Optional[float] = None


class NodeCategory(str, Enum):
    INPUT = "input"
    PROCESS = "process"
    OUTPUT = "output"
    CONTROL = "control"
    AI = "ai"


class NodeType(BaseModel):
    """워크플로우 노드 타입 정의"""
    id: str
    name: str
    description: str
    category: NodeCategory
    icon: str  # Material Icon 이름
    color: str  # Hex color
    fields: List[NodeField]
    inputs: int = 1  # 입력 포트 수
    outputs: int = 1  # 출력 포트 수


# ============================================================
# 2. 노드 타입 데이터 정의
# ============================================================

NODE_TYPES: List[NodeType] = [
    NodeType(
        id="text_input",
        name="텍스트 입력",
        description="텍스트 데이터를 입력합니다",
        category=NodeCategory.INPUT,
        icon="text_fields",
        color="#4CAF50",
        inputs=0,
        outputs=1,
        fields=[
            NodeField(
                name="text",
                label="텍스트",
                field_type=FieldType.TEXT,
                placeholder="텍스트를 입력하세요...",
                required=True
            ),
            NodeField(
                name="encoding",
                label="인코딩",
                field_type=FieldType.SELECT,
                default_value="utf-8",
                options=[
                    FieldOption(label="UTF-8", value="utf-8"),
                    FieldOption(label="EUC-KR", value="euc-kr"),
                    FieldOption(label="ASCII", value="ascii"),
                ]
            )
        ]
    ),
    NodeType(
        id="http_request",
        name="HTTP 요청",
        description="HTTP API를 호출합니다",
        category=NodeCategory.INPUT,
        icon="http",
        color="#2196F3",
        inputs=1,
        outputs=1,
        fields=[
            NodeField(
                name="url",
                label="URL",
                field_type=FieldType.STRING,
                placeholder="https://api.example.com/data",
                required=True
            ),
            NodeField(
                name="method",
                label="메서드",
                field_type=FieldType.SELECT,
                default_value="GET",
                options=[
                    FieldOption(label="GET", value="GET"),
                    FieldOption(label="POST", value="POST"),
                    FieldOption(label="PUT", value="PUT"),
                    FieldOption(label="DELETE", value="DELETE"),
                ]
            ),
            NodeField(
                name="timeout",
                label="타임아웃 (초)",
                field_type=FieldType.INTEGER,
                default_value=30,
                min_value=1,
                max_value=300
            )
        ]
    ),
    NodeType(
        id="transform",
        name="데이터 변환",
        description="데이터를 변환합니다",
        category=NodeCategory.PROCESS,
        icon="transform",
        color="#FF9800",
        inputs=1,
        outputs=1,
        fields=[
            NodeField(
                name="transform_type",
                label="변환 유형",
                field_type=FieldType.SELECT,
                required=True,
                options=[
                    FieldOption(label="JSON 파싱", value="json_parse"),
                    FieldOption(label="CSV 파싱", value="csv_parse"),
                    FieldOption(label="텍스트 분할", value="text_split"),
                    FieldOption(label="정규식 추출", value="regex_extract"),
                ]
            ),
            NodeField(
                name="expression",
                label="표현식",
                field_type=FieldType.STRING,
                placeholder="예: $.data.items[*]"
            )
        ]
    ),
    NodeType(
        id="filter",
        name="필터",
        description="조건에 맞는 데이터만 통과시킵니다",
        category=NodeCategory.PROCESS,
        icon="filter_list",
        color="#9C27B0",
        inputs=1,
        outputs=2,  # true/false 출력
        fields=[
            NodeField(
                name="condition",
                label="조건식",
                field_type=FieldType.STRING,
                placeholder="예: value > 10",
                required=True
            ),
            NodeField(
                name="case_sensitive",
                label="대소문자 구분",
                field_type=FieldType.BOOLEAN,
                default_value=True
            )
        ]
    ),
    NodeType(
        id="llm_chat",
        name="LLM 채팅",
        description="AI 모델과 대화합니다",
        category=NodeCategory.AI,
        icon="smart_toy",
        color="#E91E63",
        inputs=1,
        outputs=1,
        fields=[
            NodeField(
                name="model",
                label="모델",
                field_type=FieldType.SELECT,
                default_value="gpt-4",
                options=[
                    FieldOption(label="GPT-4", value="gpt-4"),
                    FieldOption(label="GPT-4 Turbo", value="gpt-4-turbo"),
                    FieldOption(label="GPT-3.5 Turbo", value="gpt-3.5-turbo"),
                    FieldOption(label="Claude 3 Opus", value="claude-3-opus"),
                    FieldOption(label="Claude 3 Sonnet", value="claude-3-sonnet"),
                ]
            ),
            NodeField(
                name="system_prompt",
                label="시스템 프롬프트",
                field_type=FieldType.TEXT,
                placeholder="AI의 역할을 정의하세요..."
            ),
            NodeField(
                name="temperature",
                label="Temperature",
                field_type=FieldType.FLOAT,
                default_value=0.7,
                min_value=0.0,
                max_value=2.0
            ),
            NodeField(
                name="max_tokens",
                label="최대 토큰",
                field_type=FieldType.INTEGER,
                default_value=1000,
                min_value=1,
                max_value=4096
            )
        ]
    ),
    NodeType(
        id="output_display",
        name="출력 표시",
        description="결과를 화면에 표시합니다",
        category=NodeCategory.OUTPUT,
        icon="display_settings",
        color="#607D8B",
        inputs=1,
        outputs=0,
        fields=[
            NodeField(
                name="format",
                label="표시 형식",
                field_type=FieldType.SELECT,
                default_value="text",
                options=[
                    FieldOption(label="텍스트", value="text"),
                    FieldOption(label="JSON", value="json"),
                    FieldOption(label="Markdown", value="markdown"),
                    FieldOption(label="HTML", value="html"),
                ]
            ),
            NodeField(
                name="title",
                label="제목",
                field_type=FieldType.STRING,
                placeholder="출력 결과"
            )
        ]
    ),
    NodeType(
        id="condition",
        name="조건 분기",
        description="조건에 따라 흐름을 분기합니다",
        category=NodeCategory.CONTROL,
        icon="call_split",
        color="#795548",
        inputs=1,
        outputs=2,
        fields=[
            NodeField(
                name="condition",
                label="조건식",
                field_type=FieldType.STRING,
                placeholder="예: input == 'yes'",
                required=True
            )
        ]
    ),
    NodeType(
        id="loop",
        name="반복",
        description="데이터를 반복 처리합니다",
        category=NodeCategory.CONTROL,
        icon="loop",
        color="#00BCD4",
        inputs=1,
        outputs=1,
        fields=[
            NodeField(
                name="loop_type",
                label="반복 유형",
                field_type=FieldType.SELECT,
                default_value="foreach",
                options=[
                    FieldOption(label="For Each", value="foreach"),
                    FieldOption(label="While", value="while"),
                    FieldOption(label="횟수 반복", value="count"),
                ]
            ),
            NodeField(
                name="max_iterations",
                label="최대 반복 횟수",
                field_type=FieldType.INTEGER,
                default_value=100,
                min_value=1,
                max_value=10000
            )
        ]
    ),
]


# ============================================================
# 3. json_dynamic_widget 변환 함수들
# ============================================================

def build_text_widget(text: str, style: Optional[dict] = None) -> dict:
    """Text 위젯 생성"""
    widget = {
        "type": "text",
        "args": {"text": text}
    }
    if style:
        widget["args"]["style"] = style
    return widget


def build_sized_box(height: int = 0, width: int = 0) -> dict:
    """SizedBox 위젯 생성"""
    args = {}
    if height > 0:
        args["height"] = height
    if width > 0:
        args["width"] = width
    return {"type": "sized_box", "args": args}


def build_padding(padding: int, child: dict) -> dict:
    """Padding 위젯 생성"""
    return {
        "type": "padding",
        "args": {
            "padding": padding,
            "child": child
        }
    }


def build_card(child: dict, elevation: int = 2, color: Optional[str] = None) -> dict:
    """Card 위젯 생성"""
    args = {"elevation": elevation, "child": child}
    if color:
        args["color"] = color
    return {"type": "card", "args": args}


def build_column(children: List[dict], cross_axis: str = "stretch", main_size: str = "min") -> dict:
    """Column 위젯 생성"""
    return {
        "type": "column",
        "args": {
            "mainAxisSize": main_size,
            "crossAxisAlignment": cross_axis,
            "children": children
        }
    }


def build_row(children: List[dict], main_axis: str = "start") -> dict:
    """Row 위젯 생성"""
    return {
        "type": "row",
        "args": {
            "mainAxisAlignment": main_axis,
            "children": children
        }
    }


def build_container(child: dict, color: Optional[str] = None, padding: Optional[int] = None, 
                    border_radius: Optional[int] = None, width: Optional[int] = None,
                    height: Optional[int] = None) -> dict:
    """Container 위젯 생성"""
    args = {"child": child}
    if color:
        args["color"] = color
    if padding:
        args["padding"] = padding
    if border_radius:
        args["decoration"] = {
            "borderRadius": border_radius
        }
    if width:
        args["width"] = width
    if height:
        args["height"] = height
    return {"type": "container", "args": args}


def build_icon(icon_name: str, size: int = 24, color: Optional[str] = None) -> dict:
    """Icon 위젯 생성"""
    args = {"icon": icon_name, "size": size}
    if color:
        args["color"] = color
    return {"type": "icon", "args": args}


def build_text_field(field: NodeField) -> dict:
    """TextField/TextFormField 위젯 생성"""
    decoration = {}
    if field.label:
        decoration["labelText"] = field.label
    if field.placeholder:
        decoration["hintText"] = field.placeholder
    
    return {
        "type": "text_form_field",
        "id": f"field_{field.name}",
        "args": {
            "decoration": decoration,
            "maxLines": 3 if field.field_type == FieldType.TEXT else 1
        }
    }


def build_dropdown(field: NodeField) -> dict:
    """Dropdown 위젯 생성"""
    if not field.options:
        return build_text_widget(f"No options for {field.name}")
    
    items = []
    for opt in field.options:
        items.append({
            "type": "dropdown_menu_item",
            "args": {
                "value": opt.value,
                "child": build_text_widget(opt.label)
            }
        })
    
    return {
        "type": "dropdown_button_form_field",
        "id": f"field_{field.name}",
        "args": {
            "decoration": {
                "labelText": field.label
            },
            "value": field.default_value,
            "items": items
        }
    }


def build_checkbox(field: NodeField) -> dict:
    """Checkbox 위젯 생성"""
    return {
        "type": "checkbox_list_tile",
        "id": f"field_{field.name}",
        "args": {
            "title": build_text_widget(field.label),
            "value": field.default_value if field.default_value is not None else False
        }
    }


def build_slider(field: NodeField) -> dict:
    """Slider 위젯 생성 (Float/Integer)"""
    return build_column([
        build_text_widget(f"{field.label}: {field.default_value or 0}"),
        {
            "type": "slider",
            "id": f"field_{field.name}",
            "args": {
                "value": float(field.default_value) if field.default_value else 0.0,
                "min": float(field.min_value) if field.min_value else 0.0,
                "max": float(field.max_value) if field.max_value else 100.0,
                "divisions": 100 if field.field_type == FieldType.FLOAT else int((field.max_value or 100) - (field.min_value or 0))
            }
        }
    ])


def field_to_widget(field: NodeField) -> dict:
    """NodeField를 적절한 위젯으로 변환"""
    if field.field_type == FieldType.SELECT:
        return build_dropdown(field)
    elif field.field_type == FieldType.BOOLEAN:
        return build_checkbox(field)
    elif field.field_type in [FieldType.INTEGER, FieldType.FLOAT] and field.min_value is not None:
        return build_slider(field)
    else:
        return build_text_field(field)


def node_type_to_card(node: NodeType) -> dict:
    """NodeType을 Card 위젯으로 변환"""
    # 헤더: 아이콘 + 이름 + 카테고리
    header = build_row([
        build_container(
            build_icon(node.icon, size=28, color="#FFFFFF"),
            color=node.color,
            padding=8,
            border_radius=8
        ),
        build_sized_box(width=12),
        build_column([
            build_text_widget(node.name, {"fontWeight": "bold", "fontSize": 16}),
            build_text_widget(node.category.value.upper(), {"fontSize": 12, "color": "#666666"})
        ], cross_axis="start"),
    ], main_axis="start")
    
    # 설명
    description = build_padding(8, build_text_widget(node.description, {"color": "#555555"}))
    
    # 입출력 정보
    io_info = build_row([
        build_container(
            build_text_widget(f"입력: {node.inputs}", {"fontSize": 12, "color": "#FFFFFF"}),
            color="#4CAF50",
            padding=6,
            border_radius=4
        ),
        build_sized_box(width=8),
        build_container(
            build_text_widget(f"출력: {node.outputs}", {"fontSize": 12, "color": "#FFFFFF"}),
            color="#2196F3",
            padding=6,
            border_radius=4
        ),
    ], main_axis="start")
    
    # 필드들
    field_widgets = []
    for field in node.fields:
        field_widgets.append(build_sized_box(height=8))
        field_widgets.append(field_to_widget(field))
    
    # 전체 구성
    content_children = [
        header,
        build_sized_box(height=8),
        description,
        build_sized_box(height=8),
        io_info,
    ]
    
    if field_widgets:
        content_children.append(build_sized_box(height=12))
        content_children.append({
            "type": "divider",
            "args": {}
        })
        content_children.append(build_text_widget("필드", {"fontWeight": "bold", "fontSize": 14}))
        content_children.extend(field_widgets)
    
    return build_card(
        build_padding(16, build_column(content_children, cross_axis="stretch")),
        elevation=3
    )


def build_node_types_page() -> dict:
    """노드 타입 목록 페이지 생성 - 간단 버전"""
    
    # 노드 카드들 생성
    node_cards = []
    for node in NODE_TYPES:
        # 간단한 카드 형태
        card = {
            "type": "card",
            "args": {
                "elevation": 2,
                "margin": {"left": 0, "top": 0, "right": 0, "bottom": 12},
                "child": {
                    "type": "padding",
                    "args": {
                        "padding": 16,
                        "child": {
                            "type": "column",
                            "args": {
                                "mainAxisSize": "min",
                                "crossAxisAlignment": "start",
                                "children": [
                                    # 노드 이름
                                    {
                                        "type": "text",
                                        "args": {
                                            "text": f"{node.name}",
                                            "style": {
                                                "fontWeight": "bold",
                                                "fontSize": 18
                                            }
                                        }
                                    },
                                    {"type": "sized_box", "args": {"height": 4}},
                                    # 카테고리
                                    {
                                        "type": "text",
                                        "args": {
                                            "text": f"카테고리: {node.category.value}",
                                            "style": {"fontSize": 12, "color": "#666666"}
                                        }
                                    },
                                    {"type": "sized_box", "args": {"height": 8}},
                                    # 설명
                                    {
                                        "type": "text",
                                        "args": {
                                            "text": node.description
                                        }
                                    },
                                    {"type": "sized_box", "args": {"height": 8}},
                                    # 입출력 정보
                                    {
                                        "type": "text",
                                        "args": {
                                            "text": f"입력: {node.inputs} / 출력: {node.outputs}",
                                            "style": {"fontSize": 12}
                                        }
                                    },
                                    {"type": "sized_box", "args": {"height": 8}},
                                    # 필드 수
                                    {
                                        "type": "text",
                                        "args": {
                                            "text": f"필드: {len(node.fields)}개",
                                            "style": {"fontSize": 12}
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
        node_cards.append(card)
    
    # 전체 페이지 구조
    return {
        "type": "scaffold",
        "args": {
            "appBar": {
                "type": "app_bar",
                "args": {
                    "title": {
                        "type": "text",
                        "args": {"text": "노드 타입 목록"}
                    }
                }
            },
            "body": {
                "type": "safe_area",
                "args": {
                    "child": {
                        "type": "single_child_scroll_view",
                        "args": {
                            "padding": 16,
                            "child": {
                                "type": "column",
                                "args": {
                                    "mainAxisSize": "min",
                                    "crossAxisAlignment": "stretch",
                                    "children": node_cards
                                }
                            }
                        }
                    }
                }
            }
        }
    }


# ============================================================
# 4. HTTP 서버
# ============================================================

class NodeHandler(BaseHTTPRequestHandler):
    def _set_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/api/flutter/page":
            # json_dynamic_widget 형식의 페이지
            self._set_headers()
            page_json = build_node_types_page()
            self.wfile.write(json.dumps(page_json, ensure_ascii=False).encode('utf-8'))
        
        elif parsed_path.path == "/api/nodes":
            # 노드 타입 목록 (Pydantic 모델 JSON)
            self._set_headers()
            nodes_data = [node.model_dump() for node in NODE_TYPES]
            self.wfile.write(json.dumps(nodes_data, ensure_ascii=False).encode('utf-8'))
        
        elif parsed_path.path == "/api/nodes/categories":
            # 카테고리별 노드 목록
            self._set_headers()
            categories = {}
            for node in NODE_TYPES:
                cat = node.category.value
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(node.model_dump())
            self.wfile.write(json.dumps(categories, ensure_ascii=False).encode('utf-8'))
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def run_server(port=8766):
    server_address = ('', port)
    httpd = HTTPServer(server_address, NodeHandler)
    print(f"\n{'='*60}")
    print(f"🚀 Node Types Server (Pydantic + json_dynamic_widget)")
    print(f"{'='*60}")
    print(f"📍 http://localhost:{port}")
    print(f"\n📡 Endpoints:")
    print(f"   GET /api/flutter/page    - json_dynamic_widget UI")
    print(f"   GET /api/nodes           - 노드 타입 목록 (JSON)")
    print(f"   GET /api/nodes/categories - 카테고리별 노드 목록")
    print(f"\n📦 Defined Node Types: {len(NODE_TYPES)}")
    for node in NODE_TYPES:
        print(f"   • {node.name} ({node.id}) - {len(node.fields)} fields")
    print(f"\nPress Ctrl+C to stop")
    print(f"{'='*60}\n")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
