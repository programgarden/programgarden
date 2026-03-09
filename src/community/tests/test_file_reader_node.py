"""
FileReaderNode 단위 테스트

Phase 1: 코어 파서 (PDF/TXT/CSV/JSON/MD) + 복수 파일 + 보안
"""

import asyncio
import base64
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from programgarden_community.nodes.data._parsers import (
    EXTENSION_MAP,
    _parse_page_range,
    detect_format,
    parse_csv,
    parse_json,
    parse_pdf,
    parse_txt,
)
from programgarden_community.nodes.data.file_reader import (
    FileReaderNode,
    _BASE_DIR,
    _MAX_FILES,
)


# ============================================================
# _parsers.py 단위 테스트
# ============================================================


class TestParseTxt:
    """TXT 파서 테스트"""

    def test_basic_text(self):
        text, data, meta = parse_txt(b"Hello World")
        assert text == "Hello World"
        assert data is None
        assert meta["line_count"] == 1

    def test_multiline(self):
        content = b"line1\nline2\nline3\n"
        text, data, meta = parse_txt(content)
        assert text == "line1\nline2\nline3\n"
        assert meta["line_count"] == 3

    def test_empty(self):
        text, data, meta = parse_txt(b"")
        assert text == ""
        assert meta["line_count"] == 0

    def test_utf8_korean(self):
        content = "안녕하세요\n테스트".encode("utf-8")
        text, data, meta = parse_txt(content, encoding="utf-8")
        assert "안녕하세요" in text
        assert meta["line_count"] == 2

    def test_euckr_encoding(self):
        content = "한글 테스트".encode("euc-kr")
        text, data, meta = parse_txt(content, encoding="euc-kr")
        assert text == "한글 테스트"

    def test_markdown(self):
        content = b"# Title\n\n- item 1\n- item 2\n"
        text, data, meta = parse_txt(content)
        assert "# Title" in text
        assert meta["line_count"] == 4


class TestParseCsv:
    """CSV 파서 테스트"""

    def test_basic_with_header(self):
        content = b"name,price\nAAPL,150\nGOOG,2800\n"
        text, data, meta = parse_csv(content)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0] == {"name": "AAPL", "price": "150"}
        assert data[1] == {"name": "GOOG", "price": "2800"}
        assert meta["row_count"] == 2
        assert meta["column_count"] == 2

    def test_without_header(self):
        content = b"AAPL,150\nGOOG,2800\n"
        text, data, meta = parse_csv(content, has_header=False)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0] == ["AAPL", "150"]

    def test_tab_delimiter(self):
        content = b"name\tprice\nAAPL\t150\n"
        text, data, meta = parse_csv(content, delimiter="\t")
        assert data[0] == {"name": "AAPL", "price": "150"}

    def test_empty_csv(self):
        text, data, meta = parse_csv(b"")
        assert data == []
        assert meta["row_count"] == 0

    def test_header_only(self):
        content = b"name,price\n"
        text, data, meta = parse_csv(content)
        assert data == []
        assert meta["row_count"] == 0

    def test_raw_text_preserved(self):
        content = b"a,b\n1,2\n"
        text, data, meta = parse_csv(content)
        assert text == "a,b\n1,2\n"


class TestParseJson:
    """JSON 파서 테스트"""

    def test_object(self):
        content = json.dumps({"key": "value", "num": 42}).encode()
        text, data, meta = parse_json(content)
        assert data == {"key": "value", "num": 42}
        assert meta["key_count"] == 2

    def test_array(self):
        content = json.dumps([1, 2, 3]).encode()
        text, data, meta = parse_json(content)
        assert data == [1, 2, 3]
        assert meta["item_count"] == 3

    def test_nested(self):
        obj = {"stocks": [{"symbol": "AAPL"}, {"symbol": "GOOG"}]}
        content = json.dumps(obj).encode()
        text, data, meta = parse_json(content)
        assert data["stocks"][0]["symbol"] == "AAPL"

    def test_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json(b"not json")

    def test_raw_text_preserved(self):
        content = b'{"a": 1}'
        text, data, meta = parse_json(content)
        assert text == '{"a": 1}'


class TestParsePdf:
    """PDF 파서 테스트 (pypdf mock)"""

    def _make_mock_reader(self, page_texts):
        """pypdf PdfReader mock 생성"""
        mock_reader = MagicMock()
        pages = []
        for t in page_texts:
            page = MagicMock()
            page.extract_text.return_value = t
            pages.append(page)
        mock_reader.pages = pages
        mock_reader.__len__ = lambda s: len(pages)
        return mock_reader

    @patch("pypdf.PdfReader")
    def test_basic_pdf(self, mock_pdf_cls):
        mock_pdf_cls.return_value = self._make_mock_reader(["Page 1 text", "Page 2 text"])
        text, data, meta = parse_pdf(b"%PDF-fake")
        assert "Page 1 text" in text
        assert "Page 2 text" in text
        assert meta["page_count"] == 2
        assert meta["extracted_pages"] == 2
        assert data is None

    @patch("pypdf.PdfReader")
    def test_page_range(self, mock_pdf_cls):
        mock_pdf_cls.return_value = self._make_mock_reader(["P1", "P2", "P3", "P4", "P5"])
        text, data, meta = parse_pdf(b"%PDF-fake", pages="2-4")
        assert "P1" not in text
        assert "P2" in text
        assert "P3" in text
        assert "P4" in text
        assert "P5" not in text
        assert meta["extracted_pages"] == 3

    @patch("pypdf.PdfReader")
    def test_specific_pages(self, mock_pdf_cls):
        mock_pdf_cls.return_value = self._make_mock_reader(["P1", "P2", "P3"])
        text, data, meta = parse_pdf(b"%PDF-fake", pages="1,3")
        assert "P1" in text
        assert "P2" not in text
        assert "P3" in text
        assert meta["extracted_pages"] == 2

    @patch("pypdf.PdfReader")
    def test_empty_page(self, mock_pdf_cls):
        mock_pdf_cls.return_value = self._make_mock_reader(["", "Content"])
        text, data, meta = parse_pdf(b"%PDF-fake")
        assert "Content" in text


class TestParsePageRange:
    """페이지 범위 파싱 테스트"""

    def test_none_returns_all(self):
        assert _parse_page_range(None, 5) == [0, 1, 2, 3, 4]

    def test_single_page(self):
        assert _parse_page_range("3", 5) == [2]

    def test_range(self):
        assert _parse_page_range("2-4", 10) == [1, 2, 3]

    def test_comma_separated(self):
        assert _parse_page_range("1,3,5", 5) == [0, 2, 4]

    def test_mixed(self):
        assert _parse_page_range("1-2,5", 10) == [0, 1, 4]

    def test_out_of_range_clamped(self):
        result = _parse_page_range("1-100", 3)
        assert result == [0, 1, 2]

    def test_page_beyond_total_ignored(self):
        result = _parse_page_range("10", 3)
        assert result == []

    def test_empty_string(self):
        result = _parse_page_range("", 5)
        assert result == [0, 1, 2, 3, 4]


class TestDetectFormat:
    """포맷 자동 감지 테스트"""

    def test_by_file_name(self):
        assert detect_format(file_name="report.pdf") == "pdf"
        assert detect_format(file_name="data.csv") == "csv"
        assert detect_format(file_name="config.json") == "json"
        assert detect_format(file_name="notes.txt") == "txt"
        assert detect_format(file_name="README.md") == "md"

    def test_by_file_path(self):
        assert detect_format(file_path="uploads/report.pdf") == "pdf"
        assert detect_format(file_path="/app/data/data.csv") == "csv"

    def test_file_name_priority_over_path(self):
        # file_name이 file_path보다 우선
        assert detect_format(file_name="data.csv", file_path="report.pdf") == "csv"

    def test_magic_bytes_pdf(self):
        assert detect_format(file_bytes=b"%PDF-1.4 ...") == "pdf"

    def test_fallback_to_txt(self):
        assert detect_format() == "txt"
        assert detect_format(file_name="unknown.xyz") == "txt"
        assert detect_format(file_bytes=b"random bytes") == "txt"

    def test_case_insensitive_extension(self):
        assert detect_format(file_name="Report.PDF") == "pdf"
        assert detect_format(file_name="Data.CSV") == "csv"


# ============================================================
# FileReaderNode 단위 테스트
# ============================================================


class TestFileReaderNodeInit:
    """FileReaderNode 초기화 테스트"""

    def test_default_values(self):
        node = FileReaderNode(id="fr1")
        assert node.type == "FileReaderNode"
        assert node.category.value == "data"
        assert node.format == "auto"
        assert node.encoding == "utf-8"
        assert node.max_file_size_mb == 10
        assert node.delimiter == ","
        assert node.has_header is True
        assert node.extract_tables is False
        assert node.pages is None

    def test_is_tool_enabled(self):
        assert FileReaderNode.is_tool_enabled() is True

    def test_field_schema(self):
        schema = FileReaderNode.get_field_schema()
        assert "file_path" in schema
        assert "file_paths" in schema
        assert "format" in schema
        assert "pages" in schema
        assert "encoding" in schema
        assert "max_file_size_mb" in schema

    def test_outputs(self):
        node = FileReaderNode(id="fr1")
        output_names = [o.name for o in node._outputs]
        assert "texts" in output_names
        assert "data_list" in output_names
        assert "metadata" in output_names


class TestFileReaderNodeNormalize:
    """입력 정규화 테스트"""

    def test_single_file_path(self):
        node = FileReaderNode(id="fr1", file_path="test.txt")
        paths, data_items, names = node._normalize_inputs()
        assert paths == ["test.txt"]

    def test_multiple_file_paths(self):
        node = FileReaderNode(id="fr1", file_paths=["a.txt", "b.csv"])
        paths, data_items, names = node._normalize_inputs()
        assert paths == ["a.txt", "b.csv"]

    def test_single_file_data(self):
        b64 = base64.b64encode(b"hello").decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="test.txt")
        paths, data_items, names = node._normalize_inputs()
        assert len(data_items) == 1
        assert names == ["test.txt"]

    def test_file_paths_takes_priority_over_file_path(self):
        node = FileReaderNode(id="fr1", file_paths=["a.txt"], file_path="b.txt")
        paths, data_items, names = node._normalize_inputs()
        assert paths == ["a.txt"]  # file_paths 우선

    def test_file_data_list_takes_priority(self):
        b64 = base64.b64encode(b"hello").decode()
        node = FileReaderNode(id="fr1", file_data_list=[b64], file_data=b64)
        paths, data_items, names = node._normalize_inputs()
        assert len(data_items) == 1


class TestFileReaderNodeExecute:
    """FileReaderNode execute() 테스트"""

    @pytest.mark.asyncio
    async def test_txt_via_base64(self):
        content = "Hello World\nLine 2"
        b64 = base64.b64encode(content.encode()).decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="test.txt")
        result = await node.execute(None)

        assert result["texts"] == [content]
        assert result["data_list"] == [None]
        assert result["metadata"][0]["format"] == "txt"
        assert result["metadata"][0]["file_name"] == "test.txt"

    @pytest.mark.asyncio
    async def test_csv_via_base64(self):
        content = "name,price\nAAPL,150\nGOOG,2800\n"
        b64 = base64.b64encode(content.encode()).decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="data.csv")
        result = await node.execute(None)

        assert len(result["texts"]) == 1
        data = result["data_list"][0]
        assert len(data) == 2
        assert data[0]["name"] == "AAPL"
        assert result["metadata"][0]["format"] == "csv"
        assert result["metadata"][0]["row_count"] == 2

    @pytest.mark.asyncio
    async def test_json_via_base64(self):
        obj = {"stocks": [{"symbol": "AAPL"}]}
        b64 = base64.b64encode(json.dumps(obj).encode()).decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="data.json")
        result = await node.execute(None)

        data = result["data_list"][0]
        assert data["stocks"][0]["symbol"] == "AAPL"
        assert result["metadata"][0]["format"] == "json"

    @pytest.mark.asyncio
    async def test_md_via_base64(self):
        content = "# Title\n\n- item 1\n"
        b64 = base64.b64encode(content.encode()).decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="notes.md")
        result = await node.execute(None)

        assert "# Title" in result["texts"][0]
        assert result["metadata"][0]["format"] == "md"

    @pytest.mark.asyncio
    async def test_multiple_files_via_base64(self):
        txt_b64 = base64.b64encode(b"text content").decode()
        csv_b64 = base64.b64encode(b"a,b\n1,2\n").decode()
        json_b64 = base64.b64encode(b'{"key": "val"}').decode()

        node = FileReaderNode(
            id="fr1",
            file_data_list=[txt_b64, csv_b64, json_b64],
            file_names=["a.txt", "b.csv", "c.json"],
        )
        result = await node.execute(None)

        assert len(result["texts"]) == 3
        assert len(result["data_list"]) == 3
        assert len(result["metadata"]) == 3

        assert result["metadata"][0]["format"] == "txt"
        assert result["metadata"][1]["format"] == "csv"
        assert result["metadata"][2]["format"] == "json"

        # TXT
        assert result["data_list"][0] is None
        # CSV
        assert isinstance(result["data_list"][1], list)
        # JSON
        assert result["data_list"][2] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_explicit_format_override(self):
        """format 명시 시 자동 감지 무시"""
        content = "not,csv,data"
        b64 = base64.b64encode(content.encode()).decode()
        node = FileReaderNode(
            id="fr1", file_data=b64, file_name="data.csv", format="txt"
        )
        result = await node.execute(None)
        assert result["metadata"][0]["format"] == "txt"
        assert result["data_list"][0] is None  # txt로 파싱 → data 없음

    @pytest.mark.asyncio
    @patch("pypdf.PdfReader")
    async def test_pdf_via_base64(self, mock_pdf_cls):
        """PDF base64 입력 테스트"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF content"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pdf_cls.return_value = mock_reader

        b64 = base64.b64encode(b"%PDF-fake-content").decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="report.pdf")
        result = await node.execute(None)

        assert "PDF content" in result["texts"][0]
        assert result["metadata"][0]["format"] == "pdf"
        assert result["metadata"][0]["page_count"] == 1


class TestFileReaderNodeFilePath:
    """파일 경로 기반 테스트 (tmpdir 사용)"""

    @pytest.mark.asyncio
    async def test_read_txt_file(self, tmp_path):
        """실제 파일 경로로 읽기"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello from file", encoding="utf-8")

        node = FileReaderNode(id="fr1", file_path="test.txt")

        # _BASE_DIR을 tmp_path로 패치
        with patch.object(
            FileReaderNode,
            "_validate_path",
            return_value=test_file,
        ):
            result = await node.execute(None)

        assert result["texts"] == ["Hello from file"]
        assert result["metadata"][0]["file_name"] == "test.txt"

    @pytest.mark.asyncio
    async def test_read_csv_file(self, tmp_path):
        test_file = tmp_path / "data.csv"
        test_file.write_text("name,value\nfoo,1\nbar,2\n", encoding="utf-8")

        node = FileReaderNode(id="fr1", file_path="data.csv")

        with patch.object(
            FileReaderNode,
            "_validate_path",
            return_value=test_file,
        ):
            result = await node.execute(None)

        assert result["metadata"][0]["format"] == "csv"
        assert len(result["data_list"][0]) == 2

    @pytest.mark.asyncio
    async def test_read_multiple_files(self, tmp_path):
        txt = tmp_path / "a.txt"
        txt.write_text("text", encoding="utf-8")
        csvf = tmp_path / "b.csv"
        csvf.write_text("x,y\n1,2\n", encoding="utf-8")

        node = FileReaderNode(id="fr1", file_paths=["a.txt", "b.csv"])

        call_count = 0
        files = [txt, csvf]

        def mock_validate(self_inner, fp):
            nonlocal call_count
            result = files[call_count]
            call_count += 1
            return result

        with patch.object(FileReaderNode, "_validate_path", mock_validate):
            result = await node.execute(None)

        assert len(result["texts"]) == 2
        assert result["metadata"][0]["format"] == "txt"
        assert result["metadata"][1]["format"] == "csv"


class TestFileReaderNodeSecurity:
    """보안 테스트"""

    def test_path_traversal_rejected(self):
        node = FileReaderNode(id="fr1")
        with pytest.raises(ValueError, match="외부 경로"):
            node._validate_path("../../etc/passwd")

    def test_path_traversal_dotdot(self):
        node = FileReaderNode(id="fr1")
        with pytest.raises(ValueError, match="외부 경로"):
            node._validate_path("../../../etc/shadow")

    def test_absolute_path_rejected(self):
        node = FileReaderNode(id="fr1")
        with pytest.raises(ValueError, match="외부 경로"):
            node._validate_path("/etc/passwd")

    @pytest.mark.asyncio
    async def test_oversized_file_rejected(self):
        """파일 크기 제한 초과"""
        # 2MB 데이터를 1MB 제한으로 테스트
        big_data = b"x" * (2 * 1024 * 1024)
        b64 = base64.b64encode(big_data).decode()

        node = FileReaderNode(
            id="fr1", file_data=b64, file_name="big.txt", max_file_size_mb=1
        )

        with pytest.raises(ValueError, match="초과"):
            await node.execute(None)

    @pytest.mark.asyncio
    async def test_max_files_limit(self):
        """최대 파일 수 제한"""
        b64 = base64.b64encode(b"x").decode()
        data_items = [b64] * (_MAX_FILES + 1)
        names = [f"file{i}.txt" for i in range(_MAX_FILES + 1)]

        node = FileReaderNode(
            id="fr1", file_data_list=data_items, file_names=names
        )

        with pytest.raises(ValueError, match=f"최대 {_MAX_FILES}개"):
            await node.execute(None)


class TestFileReaderNodeEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_no_input_raises(self):
        """입력 없으면 에러"""
        node = FileReaderNode(id="fr1")
        with pytest.raises(ValueError, match="파일 입력이 없습니다"):
            await node.execute(None)

    @pytest.mark.asyncio
    async def test_empty_txt_file(self):
        b64 = base64.b64encode(b"").decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="empty.txt")
        result = await node.execute(None)
        assert result["texts"] == [""]
        assert result["metadata"][0]["size_bytes"] == 0

    @pytest.mark.asyncio
    async def test_unknown_format_fallback_to_txt(self):
        """알 수 없는 확장자 → txt fallback"""
        content = "some content"
        b64 = base64.b64encode(content.encode()).decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="data.xyz")
        result = await node.execute(None)
        assert result["texts"] == [content]
        assert result["metadata"][0]["format"] == "txt"

    @pytest.mark.asyncio
    async def test_encoding_error(self):
        """잘못된 인코딩"""
        # UTF-8에서 디코딩 불가능한 바이트
        bad_bytes = bytes([0xff, 0xfe, 0x80])
        b64 = base64.b64encode(bad_bytes).decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="bad.txt")
        with pytest.raises(UnicodeDecodeError):
            await node.execute(None)

    @pytest.mark.asyncio
    async def test_csv_tab_delimiter(self):
        content = "a\tb\n1\t2\n"
        b64 = base64.b64encode(content.encode()).decode()
        node = FileReaderNode(
            id="fr1", file_data=b64, file_name="data.csv", delimiter="\t"
        )
        result = await node.execute(None)
        assert result["data_list"][0][0] == {"a": "1", "b": "2"}

    @pytest.mark.asyncio
    async def test_csv_no_header(self):
        content = "AAPL,150\nGOOG,2800\n"
        b64 = base64.b64encode(content.encode()).decode()
        node = FileReaderNode(
            id="fr1", file_data=b64, file_name="data.csv", has_header=False
        )
        result = await node.execute(None)
        data = result["data_list"][0]
        assert data[0] == ["AAPL", "150"]

    @pytest.mark.asyncio
    async def test_output_is_always_array(self):
        """단일 파일도 배열 출력"""
        b64 = base64.b64encode(b"single file").decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="one.txt")
        result = await node.execute(None)
        assert isinstance(result["texts"], list)
        assert isinstance(result["data_list"], list)
        assert isinstance(result["metadata"], list)
        assert len(result["texts"]) == 1

    @pytest.mark.asyncio
    async def test_metadata_structure(self):
        """메타데이터 필수 필드 확인"""
        content = "test"
        b64 = base64.b64encode(content.encode()).decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="test.txt")
        result = await node.execute(None)

        meta = result["metadata"][0]
        assert "file_name" in meta
        assert "format" in meta
        assert "size_bytes" in meta
        assert "encoding" in meta
        assert meta["file_name"] == "test.txt"
        assert meta["format"] == "txt"
        assert meta["size_bytes"] == 4


class TestFileReaderAutoDetect:
    """자동 포맷 감지 + 파싱 통합 테스트"""

    @pytest.mark.asyncio
    async def test_auto_detect_csv(self):
        b64 = base64.b64encode(b"a,b\n1,2\n").decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="data.csv")
        result = await node.execute(None)
        assert result["metadata"][0]["format"] == "csv"

    @pytest.mark.asyncio
    async def test_auto_detect_json(self):
        b64 = base64.b64encode(b'[1,2,3]').decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="list.json")
        result = await node.execute(None)
        assert result["metadata"][0]["format"] == "json"
        assert result["data_list"][0] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_auto_detect_md(self):
        b64 = base64.b64encode(b"# Hello").decode()
        node = FileReaderNode(id="fr1", file_data=b64, file_name="doc.md")
        result = await node.execute(None)
        assert result["metadata"][0]["format"] == "md"

    @pytest.mark.asyncio
    @patch("pypdf.PdfReader")
    async def test_auto_detect_pdf_by_magic_bytes(self, mock_pdf_cls):
        """확장자 없이 매직 바이트로 PDF 감지"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "detected"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pdf_cls.return_value = mock_reader

        b64 = base64.b64encode(b"%PDF-1.4 content").decode()
        # 확장자 없는 파일명
        node = FileReaderNode(id="fr1", file_data=b64, file_name="document")
        result = await node.execute(None)
        assert result["metadata"][0]["format"] == "pdf"


class TestFileReaderNodeRegistry:
    """노드 등록 테스트"""

    def test_import_from_community(self):
        from programgarden_community.nodes import FileReaderNode as FR
        assert FR.is_tool_enabled() is True

    def test_community_node_list(self):
        from programgarden_community.nodes_registry import get_community_node_list
        nodes = get_community_node_list()
        types = [n["type"] for n in nodes]
        assert "FileReaderNode" in types


class TestExtensionMap:
    """확장자 매핑 테스트"""

    def test_all_supported_extensions(self):
        assert EXTENSION_MAP[".pdf"] == "pdf"
        assert EXTENSION_MAP[".txt"] == "txt"
        assert EXTENSION_MAP[".csv"] == "csv"
        assert EXTENSION_MAP[".json"] == "json"
        assert EXTENSION_MAP[".md"] == "md"

    def test_unsupported_extension(self):
        assert ".xyz" not in EXTENSION_MAP
