"""
ProgramGarden Community - 데이터 노드

파일 읽기/파싱 등 데이터 처리 노드.

사용 방법:
    from programgarden_community.nodes.data import FileReaderNode
"""

from programgarden_community.nodes.data.file_reader import FileReaderNode

__all__ = [
    "FileReaderNode",
]
