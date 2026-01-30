"""
SQLite Database Tools

SQLiteNode UI를 위한 동적 API 도구 모음:
- 데이터베이스 파일 목록 조회
- 데이터베이스 삭제
- 테이블 목록 조회
- 컬럼 목록 조회

이 모듈의 함수들은 서버에서 API 엔드포인트로 노출됩니다.
"""

import os
import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional


def get_programgarden_data_path(workspace_path: Optional[str] = None) -> Path:
    """
    /app/data/ 폴더 경로를 반환합니다.

    Args:
        workspace_path: 워크스페이스 경로 (None이면 /app/data 사용)

    Returns:
        /app/data/ 폴더의 Path 객체
    """
    data_dir = Path(workspace_path) if workspace_path else Path("/app/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def validate_filename(filename: str) -> bool:
    """
    파일명이 안전한지 검증합니다 (경로 탈출 방지).
    
    Args:
        filename: 검증할 파일명
    
    Returns:
        안전하면 True, 위험하면 False
    """
    # 경로 구분자나 상위 디렉토리 참조 금지
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    # 특수 문자 제한 (알파벳, 숫자, _, -, . 만 허용)
    if not re.match(r'^[\w\-\.]+$', filename):
        return False
    return True


def list_database_files(
    workspace_path: Optional[str] = None,
    file_extension: str = ".db"
) -> Dict[str, Any]:
    """
    programgarden_data/ 폴더의 데이터베이스 파일 목록을 반환합니다.
    
    Args:
        workspace_path: 워크스페이스 경로
        file_extension: 검색할 파일 확장자 (기본: .db)
    
    Returns:
        {"files": [{"name": "...", "size": ..., "modified": ...}, ...]}
    
    Example:
        >>> list_database_files("/workspace")
        {"files": [{"name": "my_strategy.db", "size": 12288, "modified": 1704067200}]}
    """
    data_dir = get_programgarden_data_path(workspace_path)
    
    files = []
    for file_path in data_dir.glob(f"*{file_extension}"):
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "size": stat.st_size,
                "modified": int(stat.st_mtime),
            })
    
    # 수정 시간 기준 내림차순 정렬 (최신 먼저)
    files.sort(key=lambda x: x["modified"], reverse=True)
    
    return {"files": files}


def delete_database_file(
    filename: str,
    workspace_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    데이터베이스 파일을 삭제합니다.
    
    Args:
        filename: 삭제할 파일명 (경로 없이 파일명만)
        workspace_path: 워크스페이스 경로
    
    Returns:
        {"deleted": True} 또는 {"deleted": False, "error": "..."}
    
    Raises:
        ValueError: 파일명이 안전하지 않은 경우
    
    Example:
        >>> delete_database_file("old_strategy.db")
        {"deleted": True}
    """
    # 파일명 검증 (경로 탈출 방지)
    if not validate_filename(filename):
        return {
            "deleted": False,
            "error": "Invalid filename. Only alphanumeric characters, underscore, hyphen, and dot are allowed.",
        }
    
    data_dir = get_programgarden_data_path(workspace_path)
    file_path = data_dir / filename
    
    if not file_path.exists():
        return {
            "deleted": False,
            "error": f"File not found: {filename}",
        }
    
    if not file_path.is_file():
        return {
            "deleted": False,
            "error": f"Not a file: {filename}",
        }
    
    try:
        file_path.unlink()
        return {"deleted": True}
    except Exception as e:
        return {
            "deleted": False,
            "error": str(e),
        }


def list_tables(
    db_name: str,
    workspace_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    SQLite 데이터베이스의 테이블 목록을 반환합니다.
    
    Args:
        db_name: 데이터베이스 파일명
        workspace_path: 워크스페이스 경로
    
    Returns:
        {"tables": ["table1", "table2", ...]}
    
    Example:
        >>> list_tables("my_strategy.db")
        {"tables": ["peak_tracker", "trade_history"]}
    """
    if not validate_filename(db_name):
        return {
            "tables": [],
            "error": "Invalid database name",
        }
    
    data_dir = get_programgarden_data_path(workspace_path)
    db_path = data_dir / db_name
    
    if not db_path.exists():
        return {
            "tables": [],
            "error": f"Database not found: {db_name}",
        }
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 시스템 테이블 제외하고 사용자 테이블만 조회
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return {"tables": tables}
    except Exception as e:
        return {
            "tables": [],
            "error": str(e),
        }


def list_columns(
    db_name: str,
    table_name: str,
    workspace_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    테이블의 컬럼 목록을 반환합니다.
    
    Args:
        db_name: 데이터베이스 파일명
        table_name: 테이블 이름
        workspace_path: 워크스페이스 경로
    
    Returns:
        {"columns": [{"name": "...", "type": "...", "pk": bool, "nullable": bool}, ...]}
    
    Example:
        >>> list_columns("my_strategy.db", "peak_tracker")
        {"columns": [
            {"name": "symbol", "type": "TEXT", "pk": True, "nullable": False},
            {"name": "peak_price", "type": "REAL", "pk": False, "nullable": True}
        ]}
    """
    if not validate_filename(db_name):
        return {
            "columns": [],
            "error": "Invalid database name",
        }
    
    # 테이블명 검증 (SQL 인젝션 방지)
    if not re.match(r'^[\w]+$', table_name):
        return {
            "columns": [],
            "error": "Invalid table name",
        }
    
    data_dir = get_programgarden_data_path(workspace_path)
    db_path = data_dir / db_name
    
    if not db_path.exists():
        return {
            "columns": [],
            "error": f"Database not found: {db_name}",
        }
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # PRAGMA table_info로 컬럼 정보 조회
        cursor.execute(f"PRAGMA table_info({table_name})")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {
                "columns": [],
                "error": f"Table not found: {table_name}",
            }
        
        columns = []
        for row in rows:
            # row: (cid, name, type, notnull, dflt_value, pk)
            columns.append({
                "name": row[1],
                "type": row[2] or "TEXT",
                "pk": bool(row[5]),
                "nullable": not bool(row[3]),
                "default": row[4],
            })
        
        return {"columns": columns}
    except Exception as e:
        return {
            "columns": [],
            "error": str(e),
        }


def create_table(
    db_name: str,
    table_name: str,
    columns: List[Dict[str, Any]],
    workspace_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    새 테이블을 생성합니다.
    
    Args:
        db_name: 데이터베이스 파일명
        table_name: 테이블 이름
        columns: 컬럼 정의 리스트 [{"name": "...", "type": "...", "pk": bool}, ...]
        workspace_path: 워크스페이스 경로
    
    Returns:
        {"created": True} 또는 {"created": False, "error": "..."}
    
    Example:
        >>> create_table("my_strategy.db", "signals", [
        ...     {"name": "id", "type": "INTEGER", "pk": True},
        ...     {"name": "symbol", "type": "TEXT"},
        ...     {"name": "signal", "type": "TEXT"},
        ...     {"name": "created_at", "type": "DATETIME"}
        ... ])
        {"created": True}
    """
    if not validate_filename(db_name):
        return {"created": False, "error": "Invalid database name"}
    
    if not re.match(r'^[\w]+$', table_name):
        return {"created": False, "error": "Invalid table name"}
    
    if not columns:
        return {"created": False, "error": "At least one column is required"}
    
    data_dir = get_programgarden_data_path(workspace_path)
    db_path = data_dir / db_name
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 컬럼 정의 생성
        col_defs = []
        for col in columns:
            name = col.get("name", "")
            col_type = col.get("type", "TEXT")
            is_pk = col.get("pk", False)
            
            if not re.match(r'^[\w]+$', name):
                conn.close()
                return {"created": False, "error": f"Invalid column name: {name}"}
            
            col_def = f"{name} {col_type}"
            if is_pk:
                col_def += " PRIMARY KEY"
            col_defs.append(col_def)
        
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)})"
        cursor.execute(sql)
        conn.commit()
        conn.close()
        
        return {"created": True}
    except Exception as e:
        return {"created": False, "error": str(e)}


# === API 래퍼 함수들 (서버에서 호출) ===

def api_list_databases(workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """
    API: GET /api/sqlite/databases
    
    데이터베이스 파일 목록 조회
    """
    return list_database_files(workspace_path)


def api_delete_database(
    filename: str,
    workspace_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    API: DELETE /api/files/programgarden_data/{filename}
    
    데이터베이스 파일 삭제
    """
    return delete_database_file(filename, workspace_path)


def api_list_tables(
    db_name: str,
    workspace_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    API: GET /api/sqlite/{db_name}/tables
    
    테이블 목록 조회
    """
    return list_tables(db_name, workspace_path)


def api_list_columns(
    db_name: str,
    table_name: str,
    workspace_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    API: GET /api/sqlite/{db_name}/tables/{table_name}/columns
    
    컬럼 목록 조회
    """
    return list_columns(db_name, table_name, workspace_path)


def api_create_table(
    db_name: str,
    table_name: str,
    columns: List[Dict[str, Any]],
    workspace_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    API: POST /api/sqlite/{db_name}/tables
    
    새 테이블 생성
    """
    return create_table(db_name, table_name, columns, workspace_path)
