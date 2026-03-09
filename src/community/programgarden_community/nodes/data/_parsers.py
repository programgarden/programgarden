"""
FileReaderNode 내부 파서 모듈

포맷별 파일 파싱 함수. 외부에서 직접 사용하지 않음.
각 파서는 (text, data, extra_metadata) 튜플을 반환합니다.
"""

import csv
import io
import json
from typing import Any, Dict, List, Optional, Tuple


def parse_pdf(
    file_bytes: bytes,
    pages: Optional[str] = None,
    extract_tables: bool = False,
) -> Tuple[str, Any, Dict[str, Any]]:
    """
    PDF 파싱 (pypdf 사용)

    Args:
        file_bytes: PDF 파일 바이트
        pages: 페이지 범위 ("1-5", "1,3,5", None=전체)
        extract_tables: 테이블 추출 여부 (pdfplumber 필요)

    Returns:
        (text, data, extra_metadata)
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError(
            "PDF 파싱에 pypdf가 필요합니다. "
            "설치: pip install pypdf"
        )

    reader = PdfReader(io.BytesIO(file_bytes))
    total_pages = len(reader.pages)

    # 페이지 범위 파싱
    page_indices = _parse_page_range(pages, total_pages)

    # 텍스트 추출
    texts = []
    for idx in page_indices:
        page = reader.pages[idx]
        text = page.extract_text() or ""
        texts.append(text)

    full_text = "\n".join(texts)

    # 테이블 추출 (pdfplumber)
    table_data = None
    if extract_tables:
        table_data = _extract_pdf_tables(file_bytes, page_indices)

    extra = {
        "page_count": total_pages,
        "extracted_pages": len(page_indices),
    }

    return full_text, table_data, extra


def _parse_page_range(pages: Optional[str], total: int) -> List[int]:
    """
    페이지 범위 문자열 → 0-based 인덱스 리스트

    Examples:
        "1-5" → [0,1,2,3,4]
        "1,3,5" → [0,2,4]
        "2-4,7" → [1,2,3,6]
        None → [0..total-1]
    """
    if not pages:
        return list(range(total))

    indices = set()
    for part in pages.split(","):
        part = part.strip()
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = max(1, int(start_str.strip()))
            end = min(total, int(end_str.strip()))
            for i in range(start, end + 1):
                indices.add(i - 1)  # 0-based
        else:
            page_num = int(part)
            if 1 <= page_num <= total:
                indices.add(page_num - 1)

    return sorted(indices)


def _extract_pdf_tables(
    file_bytes: bytes, page_indices: List[int]
) -> Optional[List[List[List[str]]]]:
    """pdfplumber로 PDF 테이블 추출"""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "PDF 테이블 추출에 pdfplumber가 필요합니다. "
            "설치: pip install pdfplumber"
        )

    tables = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for idx in page_indices:
            if idx < len(pdf.pages):
                page_tables = pdf.pages[idx].extract_tables()
                if page_tables:
                    tables.extend(page_tables)

    return tables if tables else None


def parse_txt(
    file_bytes: bytes,
    encoding: str = "utf-8",
) -> Tuple[str, Any, Dict[str, Any]]:
    """TXT/MD 파싱"""
    text = file_bytes.decode(encoding)
    line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return text, None, {"line_count": line_count}


def parse_csv(
    file_bytes: bytes,
    encoding: str = "utf-8",
    delimiter: str = ",",
    has_header: bool = True,
) -> Tuple[str, Any, Dict[str, Any]]:
    """CSV 파싱 → 구조화 데이터 (list[dict]) + 원본 텍스트"""
    text = file_bytes.decode(encoding)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        return text, [], {"row_count": 0, "column_count": 0}

    if has_header and len(rows) > 1:
        headers = rows[0]
        data = [dict(zip(headers, row)) for row in rows[1:]]
        row_count = len(data)
    elif has_header and len(rows) == 1:
        # 헤더만 있는 경우
        data = []
        row_count = 0
    else:
        data = rows
        row_count = len(rows)

    column_count = len(rows[0]) if rows else 0

    return text, data, {"row_count": row_count, "column_count": column_count}


def parse_json(
    file_bytes: bytes,
    encoding: str = "utf-8",
) -> Tuple[str, Any, Dict[str, Any]]:
    """JSON 파싱 → 파싱된 객체 + 원본 텍스트"""
    text = file_bytes.decode(encoding)
    data = json.loads(text)

    extra: Dict[str, Any] = {}
    if isinstance(data, list):
        extra["item_count"] = len(data)
    elif isinstance(data, dict):
        extra["key_count"] = len(data)

    return text, data, extra


# 포맷 → 확장자 매핑
EXTENSION_MAP = {
    ".pdf": "pdf",
    ".txt": "txt",
    ".csv": "csv",
    ".json": "json",
    ".md": "md",
}

# PDF 매직 바이트
_PDF_MAGIC = b"%PDF-"


def detect_format(
    file_name: Optional[str] = None,
    file_path: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
) -> str:
    """
    파일 포맷 자동 감지

    우선순위:
    1. file_name 확장자
    2. file_path 확장자
    3. 매직 바이트 (PDF)
    4. txt fallback
    """
    import os

    # 1. file_name 확장자
    if file_name:
        ext = os.path.splitext(file_name)[1].lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

    # 2. file_path 확장자
    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

    # 3. 매직 바이트
    if file_bytes and file_bytes[:5] == _PDF_MAGIC:
        return "pdf"

    # 4. fallback
    return "txt"
