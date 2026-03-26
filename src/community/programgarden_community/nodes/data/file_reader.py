"""
ProgramGarden Community - FileReaderNode

PDF, TXT, CSV, JSON, MD 파일을 읽어 텍스트/데이터로 변환하는 파서 노드.
노드는 파싱만 담당하며, 파일 소스(Firebase, S3 등)는 노드 밖에서 처리합니다.

사용 예시:
    {
        "id": "doc",
        "type": "FileReaderNode",
        "file_path": "uploads/report.pdf",
        "pages": "1-5"
    }
"""

import base64
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Literal, Optional, TYPE_CHECKING

from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)

from programgarden_community.nodes.data._parsers import (
    detect_format,
    parse_csv,
    parse_docx,
    parse_json,
    parse_pdf,
    parse_txt,
    parse_xlsx,
)

# 하드 리밋
_MAX_FILES = 20
_MAX_PDF_PAGES = 100
_BASE_DIR = Path("/app/data")


class FileReaderNode(BaseNode):
    """
    파일 파서 노드 — PDF, TXT, CSV, JSON, MD 파일을 읽어 텍스트/데이터로 변환합니다.
    노드는 파싱만 담당하며, 파일 소스(Firebase, S3, 로컬 업로드 등)는 노드 밖에서 처리합니다.

    Example DSL:
        {
            "id": "doc",
            "type": "FileReaderNode",
            "file_path": "uploads/report.pdf",
            "pages": "1-5"
        }
    """

    type: Literal["FileReaderNode"] = "FileReaderNode"
    category: NodeCategory = NodeCategory.DATA
    description: str = "i18n:nodes.FileReaderNode.description"
    _img_url: ClassVar[str] = ""

    # === 파일 입력 (복수) ===
    file_paths: List[str] = Field(
        default_factory=list,
        description="i18n:fields.FileReaderNode.file_paths",
    )
    file_data_list: List[str] = Field(
        default_factory=list,
        description="i18n:fields.FileReaderNode.file_data_list",
    )
    file_names: List[str] = Field(
        default_factory=list,
        description="i18n:fields.FileReaderNode.file_names",
    )

    # === 파일 입력 (단일 편의) ===
    file_path: Optional[str] = Field(
        default=None,
        description="i18n:fields.FileReaderNode.file_path",
    )
    file_data: Optional[str] = Field(
        default=None,
        description="i18n:fields.FileReaderNode.file_data",
    )
    file_name: Optional[str] = Field(
        default=None,
        description="i18n:fields.FileReaderNode.file_name",
    )

    # === 파싱 설정 ===
    format: Literal["auto", "pdf", "txt", "csv", "json", "md", "docx", "xlsx"] = Field(
        default="auto",
        description="i18n:fields.FileReaderNode.format",
    )
    encoding: str = Field(
        default="utf-8",
        description="i18n:fields.FileReaderNode.encoding",
    )

    # PDF 전용
    pages: Optional[str] = Field(
        default=None,
        description="i18n:fields.FileReaderNode.pages",
    )
    extract_tables: bool = Field(
        default=False,
        description="i18n:fields.FileReaderNode.extract_tables",
    )

    # CSV 전용
    delimiter: str = Field(
        default=",",
        description="i18n:fields.FileReaderNode.delimiter",
    )
    has_header: bool = Field(
        default=True,
        description="i18n:fields.FileReaderNode.has_header",
    )

    # XLSX 전용
    sheet_name: Optional[str] = Field(
        default=None,
        description="i18n:fields.FileReaderNode.sheet_name",
    )

    # === 보안/제한 ===
    max_file_size_mb: int = Field(
        default=10,
        ge=1,
        le=50,
        description="i18n:fields.FileReaderNode.max_file_size_mb",
    )

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="texts", type="array", description="i18n:outputs.FileReaderNode.texts"),
        OutputPort(name="data_list", type="array", description="i18n:outputs.FileReaderNode.data_list"),
        OutputPort(name="metadata", type="array", description="i18n:outputs.FileReaderNode.metadata"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema,
            FieldType,
            FieldCategory,
            ExpressionMode,
        )

        return {
            "file_paths": FieldSchema(
                name="file_paths",
                type=FieldType.ARRAY,
                description="i18n:fields.FileReaderNode.file_paths",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
            ),
            "file_path": FieldSchema(
                name="file_path",
                type=FieldType.STRING,
                description="i18n:fields.FileReaderNode.file_path",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                placeholder="uploads/report.pdf",
            ),
            "file_data_list": FieldSchema(
                name="file_data_list",
                type=FieldType.ARRAY,
                description="i18n:fields.FileReaderNode.file_data_list",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
            ),
            "file_data": FieldSchema(
                name="file_data",
                type=FieldType.STRING,
                description="i18n:fields.FileReaderNode.file_data",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
            ),
            "file_names": FieldSchema(
                name="file_names",
                type=FieldType.ARRAY,
                description="i18n:fields.FileReaderNode.file_names",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
            ),
            "file_name": FieldSchema(
                name="file_name",
                type=FieldType.STRING,
                description="i18n:fields.FileReaderNode.file_name",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
            ),
            "format": FieldSchema(
                name="format",
                type=FieldType.ENUM,
                description="i18n:fields.FileReaderNode.format",
                default="auto",
                enum_values=["auto", "pdf", "txt", "csv", "json", "md", "docx", "xlsx"],
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "encoding": FieldSchema(
                name="encoding",
                type=FieldType.STRING,
                description="i18n:fields.FileReaderNode.encoding",
                default="utf-8",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "pages": FieldSchema(
                name="pages",
                type=FieldType.STRING,
                description="i18n:fields.FileReaderNode.pages",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                placeholder="1-5",
                visible_when={"format": ["auto", "pdf"]},
            ),
            "extract_tables": FieldSchema(
                name="extract_tables",
                type=FieldType.BOOLEAN,
                description="i18n:fields.FileReaderNode.extract_tables",
                default=False,
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                visible_when={"format": ["auto", "pdf"]},
            ),
            "delimiter": FieldSchema(
                name="delimiter",
                type=FieldType.STRING,
                description="i18n:fields.FileReaderNode.delimiter",
                default=",",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                visible_when={"format": ["auto", "csv"]},
            ),
            "has_header": FieldSchema(
                name="has_header",
                type=FieldType.BOOLEAN,
                description="i18n:fields.FileReaderNode.has_header",
                default=True,
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                visible_when={"format": ["auto", "csv"]},
            ),
            "sheet_name": FieldSchema(
                name="sheet_name",
                type=FieldType.STRING,
                description="i18n:fields.FileReaderNode.sheet_name",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                visible_when={"format": ["auto", "xlsx"]},
            ),
            "max_file_size_mb": FieldSchema(
                name="max_file_size_mb",
                type=FieldType.NUMBER,
                description="i18n:fields.FileReaderNode.max_file_size_mb",
                default=10,
                min=1,
                max=50,
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
        }

    async def execute(self, context: Any) -> Dict[str, Any]:
        """파일 읽기 및 파싱 실행"""
        # 1. 입력 정규화 (단일 → 배열)
        paths, data_items, names = self._normalize_inputs()

        # 2. 파일 수 제한
        total = max(len(paths), len(data_items))
        if total == 0:
            raise ValueError("파일 입력이 없습니다. file_path(s) 또는 file_data를 지정해주세요.")
        if total > _MAX_FILES:
            raise ValueError(f"최대 {_MAX_FILES}개 파일까지 처리할 수 있습니다. (요청: {total}개)")

        # 3. 각 파일 처리
        texts: List[str] = []
        data_list: List[Any] = []
        metadata_list: List[Dict[str, Any]] = []

        max_bytes = self.max_file_size_mb * 1024 * 1024

        for i in range(total):
            file_bytes: bytes
            source_name: Optional[str] = names[i] if i < len(names) else None
            source_path: Optional[str] = None

            if i < len(paths) and paths[i]:
                # 경로 기반
                source_path = paths[i]
                resolved = self._validate_path(source_path)
                file_bytes = resolved.read_bytes()
                if not source_name:
                    source_name = resolved.name
            elif i < len(data_items):
                # base64 기반 (빈 문자열도 유효 — 빈 파일)
                file_bytes = base64.b64decode(data_items[i])
            else:
                raise ValueError(f"파일 #{i+1}: 경로 또는 데이터가 없습니다.")

            # 크기 검증
            if len(file_bytes) > max_bytes:
                size_mb = len(file_bytes) / (1024 * 1024)
                raise ValueError(
                    f"파일 '{source_name or f'#{i+1}'}' 크기({size_mb:.1f}MB)가 "
                    f"제한({self.max_file_size_mb}MB)을 초과합니다."
                )

            # 포맷 감지
            fmt = self.format
            if fmt == "auto":
                fmt = detect_format(
                    file_name=source_name,
                    file_path=source_path,
                    file_bytes=file_bytes,
                )

            # 파싱
            text, data, extra_meta = self._parse_file(file_bytes, fmt)

            # 결과 수집
            texts.append(text)
            data_list.append(data)

            meta: Dict[str, Any] = {
                "file_name": source_name or f"file_{i+1}",
                "format": fmt,
                "size_bytes": len(file_bytes),
                "encoding": self.encoding,
            }
            meta.update(extra_meta)
            metadata_list.append(meta)

        return {
            "texts": texts,
            "data_list": data_list,
            "metadata": metadata_list,
        }

    def _normalize_inputs(self) -> tuple:
        """단일 입력 필드를 배열로 통합"""
        paths = list(self.file_paths)
        data_items = list(self.file_data_list)
        names = list(self.file_names)

        if self.file_path is not None and not paths:
            paths = [self.file_path]
        if self.file_data is not None and not data_items:
            data_items = [self.file_data]
        if self.file_name is not None and not names:
            names = [self.file_name]

        return paths, data_items, names

    def _validate_path(self, file_path: str) -> Path:
        """경로 보안 검증 (/app/data/ 하위만 허용)"""
        base = _BASE_DIR.resolve()
        resolved = (base / file_path).resolve()
        if not str(resolved).startswith(str(base)):
            raise ValueError(f"경로 접근이 거부되었습니다: /app/data/ 외부 경로 ({file_path})")
        if not resolved.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        if not resolved.is_file():
            raise ValueError(f"디렉토리는 읽을 수 없습니다: {file_path}")
        return resolved

    def _parse_file(self, file_bytes: bytes, fmt: str) -> tuple:
        """포맷별 파싱 디스패치"""
        if fmt == "pdf":
            return parse_pdf(
                file_bytes,
                pages=self.pages,
                extract_tables=self.extract_tables,
            )
        elif fmt in ("txt", "md"):
            return parse_txt(file_bytes, encoding=self.encoding)
        elif fmt == "csv":
            return parse_csv(
                file_bytes,
                encoding=self.encoding,
                delimiter=self.delimiter,
                has_header=self.has_header,
            )
        elif fmt == "json":
            return parse_json(file_bytes, encoding=self.encoding)
        elif fmt == "docx":
            return parse_docx(file_bytes)
        elif fmt == "xlsx":
            return parse_xlsx(file_bytes, sheet_name=self.sheet_name)
        else:
            # 알 수 없는 포맷 → txt로 fallback
            return parse_txt(file_bytes, encoding=self.encoding)
