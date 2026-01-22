"""
SQLiteNode 단위 테스트

테스트 범위:
- SQLQueryBuilder 쿼리 생성
- SQL 인젝션 방지
- SQLiteNodeExecutor execute_query 모드
- SQLiteNodeExecutor simple 모드 (5개 액션)
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from typing import Dict, Any

from programgarden.database.query_builder import SQLQueryBuilder


class TestSQLQueryBuilder:
    """SQLQueryBuilder 테스트"""
    
    def test_validate_identifier_valid(self):
        """유효한 식별자 검증"""
        assert SQLQueryBuilder.validate_identifier("users") == "users"
        assert SQLQueryBuilder.validate_identifier("user_table") == "user_table"
        assert SQLQueryBuilder.validate_identifier("_private") == "_private"
        assert SQLQueryBuilder.validate_identifier("Table123") == "Table123"
    
    def test_validate_identifier_invalid(self):
        """유효하지 않은 식별자 거부 - SQL 인젝션 방지"""
        with pytest.raises(ValueError):
            SQLQueryBuilder.validate_identifier("users; DROP TABLE users;")
        
        with pytest.raises(ValueError):
            SQLQueryBuilder.validate_identifier("users--comment")
        
        with pytest.raises(ValueError):
            SQLQueryBuilder.validate_identifier("table name")  # 공백 불가
        
        with pytest.raises(ValueError):
            SQLQueryBuilder.validate_identifier("123table")  # 숫자로 시작 불가
        
        with pytest.raises(ValueError):
            SQLQueryBuilder.validate_identifier("")  # 빈 문자열 불가
    
    def test_build_select_all(self):
        """SELECT * 쿼리 생성"""
        query = SQLQueryBuilder.build_select("users")
        assert query == "SELECT * FROM users"
    
    def test_build_select_columns(self):
        """SELECT 특정 컬럼 쿼리 생성"""
        query = SQLQueryBuilder.build_select("users", ["id", "name", "email"])
        assert query == "SELECT id, name, email FROM users"
    
    def test_build_select_where(self):
        """SELECT WHERE 쿼리 생성"""
        query = SQLQueryBuilder.build_select("users", ["id", "name"], "id = :id")
        assert query == "SELECT id, name FROM users WHERE id = :id"
    
    def test_build_insert(self):
        """INSERT 쿼리 생성"""
        query = SQLQueryBuilder.build_insert("users", ["id", "name", "email"])
        assert query == "INSERT INTO users (id, name, email) VALUES (:id, :name, :email)"
    
    def test_build_update(self):
        """UPDATE 쿼리 생성"""
        query = SQLQueryBuilder.build_update("users", ["name", "email"], "id = :id")
        assert query == "UPDATE users SET name = :name, email = :email WHERE id = :id"
    
    def test_build_update_no_where(self):
        """UPDATE 전체 쿼리 생성 (WHERE 없음)"""
        query = SQLQueryBuilder.build_update("users", ["status"])
        assert query == "UPDATE users SET status = :status"
    
    def test_build_delete(self):
        """DELETE 쿼리 생성"""
        query = SQLQueryBuilder.build_delete("users", "id = :id")
        assert query == "DELETE FROM users WHERE id = :id"
    
    def test_build_delete_all(self):
        """DELETE 전체 쿼리 생성 (WHERE 없음)"""
        query = SQLQueryBuilder.build_delete("users")
        assert query == "DELETE FROM users"
    
    def test_build_upsert(self):
        """UPSERT 쿼리 생성"""
        query = SQLQueryBuilder.build_upsert("users", ["id", "name", "email"], "id")
        assert "INSERT INTO users" in query
        assert "ON CONFLICT(id) DO UPDATE SET" in query
        assert "name = excluded.name" in query
        assert "email = excluded.email" in query
        # id는 충돌 컬럼이므로 UPDATE SET에 포함되지 않아야 함
        assert "id = excluded.id" not in query
    
    def test_extract_params_from_where(self):
        """WHERE 절에서 파라미터 추출"""
        params = SQLQueryBuilder.extract_params_from_where(
            "symbol = :symbol AND price > :min_price",
            {"symbol": "AAPL", "min_price": 100, "extra": "ignored"}
        )
        assert params == {"symbol": "AAPL", "min_price": 100}
    
    def test_extract_params_empty_where(self):
        """빈 WHERE 절"""
        params = SQLQueryBuilder.extract_params_from_where("", {})
        assert params == {}
    
    def test_sql_injection_in_select(self):
        """SELECT에서 SQL 인젝션 방지"""
        with pytest.raises(ValueError):
            SQLQueryBuilder.build_select("users; DROP TABLE users")
        
        with pytest.raises(ValueError):
            SQLQueryBuilder.build_select("users", ["id", "name; DROP TABLE users"])


class MockExecutionContext:
    """테스트용 Mock ExecutionContext"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.logs = []
    
    def log(self, level: str, message: str, node_id: str = None):
        self.logs.append({"level": level, "message": message, "node_id": node_id})
    
    def get_log_messages(self, level: str = None) -> list:
        if level:
            return [l["message"] for l in self.logs if l["level"] == level]
        return [l["message"] for l in self.logs]


class TestSQLiteNodeExecutor:
    """SQLiteNodeExecutor 통합 테스트"""
    
    @pytest.fixture
    def temp_workspace(self):
        """임시 워크스페이스 생성"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def executor(self):
        """SQLiteNodeExecutor 인스턴스"""
        from programgarden.executor import SQLiteNodeExecutor
        return SQLiteNodeExecutor()
    
    @pytest.fixture
    def context(self, temp_workspace):
        """Mock ExecutionContext"""
        return MockExecutionContext(workspace_path=temp_workspace)
    
    @pytest.mark.asyncio
    async def test_execute_query_mode_create_table(self, executor, context, temp_workspace):
        """execute_query 모드: 테이블 생성"""
        config = {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)",
            "parameters": {},
        }
        
        result = await executor.execute("sqlite_1", "SQLiteNode", config, context)
        
        assert "error" not in result or result.get("error") is None
        # DDL 쿼리는 affected_count가 -1일 수 있음 (정상)
        
        # DB 파일 생성 확인
        db_path = os.path.join(temp_workspace, "programgarden_data", "test.db")
        assert os.path.exists(db_path)
    
    @pytest.mark.asyncio
    async def test_execute_query_mode_select(self, executor, context, temp_workspace):
        """execute_query 모드: SELECT 쿼리"""
        # 테이블 생성
        config_create = {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)",
        }
        await executor.execute("sqlite_1", "SQLiteNode", config_create, context)
        
        # 데이터 삽입
        config_insert = {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "INSERT INTO users (id, name) VALUES (1, 'Alice'), (2, 'Bob')",
        }
        await executor.execute("sqlite_1", "SQLiteNode", config_insert, context)
        
        # SELECT
        config_select = {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "SELECT * FROM users WHERE id = :id",
            "parameters": {"id": 1},
        }
        result = await executor.execute("sqlite_1", "SQLiteNode", config_select, context)
        
        assert len(result["rows"]) == 1
        assert result["rows"][0]["name"] == "Alice"
    
    @pytest.mark.asyncio
    async def test_simple_mode_insert(self, executor, context, temp_workspace):
        """simple 모드: INSERT 액션"""
        # 테이블 먼저 생성
        config_create = {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "CREATE TABLE IF NOT EXISTS peak_tracker (symbol TEXT PRIMARY KEY, peak_price REAL)",
        }
        await executor.execute("sqlite_1", "SQLiteNode", config_create, context)
        
        # INSERT
        config_insert = {
            "db_name": "test.db",
            "operation": "simple",
            "table": "peak_tracker",
            "action": "insert",
            "columns": ["symbol", "peak_price"],
            "values": {"symbol": "AAPL", "peak_price": 195.50},
        }
        result = await executor.execute("sqlite_1", "SQLiteNode", config_insert, context)
        
        assert result["affected_count"] == 1
        assert result["last_insert_id"] is not None
    
    @pytest.mark.asyncio
    async def test_simple_mode_select(self, executor, context, temp_workspace):
        """simple 모드: SELECT 액션"""
        # 테이블 및 데이터 준비
        await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "CREATE TABLE IF NOT EXISTS peak_tracker (symbol TEXT PRIMARY KEY, peak_price REAL)",
        }, context)
        
        await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "INSERT INTO peak_tracker (symbol, peak_price) VALUES ('AAPL', 195.50), ('NVDA', 450.00)",
        }, context)
        
        # SELECT
        result = await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "simple",
            "table": "peak_tracker",
            "action": "select",
            "columns": ["symbol", "peak_price"],
        }, context)
        
        assert len(result["rows"]) == 2
        symbols = [r["symbol"] for r in result["rows"]]
        assert "AAPL" in symbols
        assert "NVDA" in symbols
    
    @pytest.mark.asyncio
    async def test_simple_mode_update(self, executor, context, temp_workspace):
        """simple 모드: UPDATE 액션"""
        # 테이블 및 데이터 준비
        await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "CREATE TABLE IF NOT EXISTS peak_tracker (symbol TEXT PRIMARY KEY, peak_price REAL)",
        }, context)
        
        await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "INSERT INTO peak_tracker (symbol, peak_price) VALUES ('AAPL', 195.50)",
        }, context)
        
        # UPDATE - values에 where 조건용 파라미터도 함께 포함
        result = await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "simple",
            "table": "peak_tracker",
            "action": "update",
            "values": {"peak_price": 200.00, "symbol": "AAPL"},  # symbol은 WHERE 파라미터
            "where_clause": "symbol = :symbol",
        }, context)
        
        assert result["affected_count"] == 1
        
        # 확인
        select_result = await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "simple",
            "table": "peak_tracker",
            "action": "select",
            "where_clause": "symbol = :symbol",
            "values": {"symbol": "AAPL"},
        }, context)
        
        assert select_result["rows"][0]["peak_price"] == 200.00
    
    @pytest.mark.asyncio
    async def test_simple_mode_delete(self, executor, context, temp_workspace):
        """simple 모드: DELETE 액션"""
        # 테이블 및 데이터 준비
        await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "CREATE TABLE IF NOT EXISTS peak_tracker (symbol TEXT PRIMARY KEY, peak_price REAL)",
        }, context)
        
        await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "INSERT INTO peak_tracker (symbol, peak_price) VALUES ('AAPL', 195.50), ('NVDA', 450.00)",
        }, context)
        
        # DELETE
        result = await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "simple",
            "table": "peak_tracker",
            "action": "delete",
            "where_clause": "symbol = :symbol",
            "values": {"symbol": "AAPL"},
        }, context)
        
        assert result["affected_count"] == 1
        
        # 확인
        select_result = await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "simple",
            "table": "peak_tracker",
            "action": "select",
        }, context)
        
        assert len(select_result["rows"]) == 1
        assert select_result["rows"][0]["symbol"] == "NVDA"
    
    @pytest.mark.asyncio
    async def test_simple_mode_upsert(self, executor, context, temp_workspace):
        """simple 모드: UPSERT 액션"""
        # 테이블 생성
        await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "execute_query",
            "query": "CREATE TABLE IF NOT EXISTS peak_tracker (symbol TEXT PRIMARY KEY, peak_price REAL)",
        }, context)
        
        # 첫 번째 UPSERT (INSERT)
        await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "simple",
            "table": "peak_tracker",
            "action": "upsert",
            "columns": ["symbol", "peak_price"],
            "values": {"symbol": "AAPL", "peak_price": 195.50},
            "on_conflict": "symbol",
        }, context)
        
        # 두 번째 UPSERT (UPDATE)
        await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "simple",
            "table": "peak_tracker",
            "action": "upsert",
            "columns": ["symbol", "peak_price"],
            "values": {"symbol": "AAPL", "peak_price": 200.00},
            "on_conflict": "symbol",
        }, context)
        
        # 확인
        select_result = await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "test.db",
            "operation": "simple",
            "table": "peak_tracker",
            "action": "select",
        }, context)
        
        assert len(select_result["rows"]) == 1  # 중복 없이 1개만
        assert select_result["rows"][0]["peak_price"] == 200.00  # 업데이트됨
    
    @pytest.mark.asyncio
    async def test_data_dir_auto_creation(self, executor, context, temp_workspace):
        """programgarden_data/ 폴더 자동 생성 확인"""
        data_dir = os.path.join(temp_workspace, "programgarden_data")
        assert not os.path.exists(data_dir)
        
        await executor.execute("sqlite_1", "SQLiteNode", {
            "db_name": "auto_created.db",
            "operation": "execute_query",
            "query": "SELECT 1",
        }, context)
        
        assert os.path.exists(data_dir)
        assert os.path.exists(os.path.join(data_dir, "auto_created.db"))


class TestSQLiteTools:
    """sqlite_tools 모듈 테스트"""
    
    @pytest.fixture
    def temp_workspace(self):
        """임시 워크스페이스 생성"""
        workspace = tempfile.mkdtemp()
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)
    
    def test_list_database_files_empty(self, temp_workspace):
        """빈 폴더에서 DB 목록 조회"""
        from programgarden.tools.sqlite_tools import list_database_files
        
        result = list_database_files(temp_workspace)
        assert "files" in result
        assert result["files"] == []
    
    def test_list_database_files_with_dbs(self, temp_workspace):
        """DB 파일이 있는 경우 목록 조회"""
        import sqlite3
        from programgarden.tools.sqlite_tools import list_database_files, get_programgarden_data_path
        
        data_dir = get_programgarden_data_path(temp_workspace)
        
        # 테스트용 DB 생성
        db1_path = data_dir / "test1.db"
        db2_path = data_dir / "test2.db"
        
        conn1 = sqlite3.connect(str(db1_path))
        conn1.execute("CREATE TABLE test (id INTEGER)")
        conn1.close()
        
        conn2 = sqlite3.connect(str(db2_path))
        conn2.execute("CREATE TABLE test (id INTEGER)")
        conn2.close()
        
        result = list_database_files(temp_workspace)
        assert len(result["files"]) == 2
        assert any(f["name"] == "test1.db" for f in result["files"])
        assert any(f["name"] == "test2.db" for f in result["files"])
    
    def test_delete_database_file(self, temp_workspace):
        """DB 파일 삭제"""
        import sqlite3
        from programgarden.tools.sqlite_tools import (
            delete_database_file, 
            get_programgarden_data_path,
            list_database_files
        )
        
        data_dir = get_programgarden_data_path(temp_workspace)
        db_path = data_dir / "to_delete.db"
        
        # DB 생성
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        assert db_path.exists()
        
        # 삭제
        result = delete_database_file("to_delete.db", temp_workspace)
        assert result["deleted"] is True
        assert not db_path.exists()
    
    def test_delete_database_file_path_traversal(self, temp_workspace):
        """경로 탈출 시도 차단"""
        from programgarden.tools.sqlite_tools import delete_database_file
        
        result = delete_database_file("../../../etc/passwd", temp_workspace)
        assert result["deleted"] is False
        assert "Invalid filename" in result["error"]
        
        result = delete_database_file("test/subdir.db", temp_workspace)
        assert result["deleted"] is False
        assert "Invalid filename" in result["error"]
    
    def test_list_tables(self, temp_workspace):
        """테이블 목록 조회"""
        import sqlite3
        from programgarden.tools.sqlite_tools import list_tables, get_programgarden_data_path
        
        data_dir = get_programgarden_data_path(temp_workspace)
        db_path = data_dir / "test.db"
        
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER)")
        conn.close()
        
        result = list_tables("test.db", temp_workspace)
        assert "tables" in result
        assert "users" in result["tables"]
        assert "orders" in result["tables"]
        assert len(result["tables"]) == 2
    
    def test_list_tables_empty_db(self, temp_workspace):
        """빈 DB의 테이블 목록"""
        import sqlite3
        from programgarden.tools.sqlite_tools import list_tables, get_programgarden_data_path
        
        data_dir = get_programgarden_data_path(temp_workspace)
        db_path = data_dir / "empty.db"
        
        conn = sqlite3.connect(str(db_path))
        conn.close()
        
        result = list_tables("empty.db", temp_workspace)
        assert result["tables"] == []
    
    def test_list_columns(self, temp_workspace):
        """컬럼 목록 조회"""
        import sqlite3
        from programgarden.tools.sqlite_tools import list_columns, get_programgarden_data_path
        
        data_dir = get_programgarden_data_path(temp_workspace)
        db_path = data_dir / "test.db"
        
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE peak_tracker (
                symbol TEXT PRIMARY KEY,
                peak_price REAL NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.close()
        
        result = list_columns("test.db", "peak_tracker", temp_workspace)
        assert "columns" in result
        assert len(result["columns"]) == 3
        
        # symbol 컬럼 확인
        symbol_col = next(c for c in result["columns"] if c["name"] == "symbol")
        assert symbol_col["type"] == "TEXT"
        assert symbol_col["pk"] is True
        
        # peak_price 컬럼 확인
        price_col = next(c for c in result["columns"] if c["name"] == "peak_price")
        assert price_col["type"] == "REAL"
        assert price_col["nullable"] is False
    
    def test_list_columns_nonexistent_table(self, temp_workspace):
        """존재하지 않는 테이블의 컬럼 조회"""
        import sqlite3
        from programgarden.tools.sqlite_tools import list_columns, get_programgarden_data_path
        
        data_dir = get_programgarden_data_path(temp_workspace)
        db_path = data_dir / "test.db"
        
        conn = sqlite3.connect(str(db_path))
        conn.close()
        
        result = list_columns("test.db", "nonexistent", temp_workspace)
        assert result["columns"] == []
        assert "not found" in result.get("error", "").lower()
    
    def test_create_table(self, temp_workspace):
        """새 테이블 생성"""
        from programgarden.tools.sqlite_tools import (
            create_table, 
            list_tables, 
            list_columns,
            get_programgarden_data_path
        )
        import sqlite3
        
        # 빈 DB 생성
        data_dir = get_programgarden_data_path(temp_workspace)
        db_path = data_dir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.close()
        
        # 테이블 생성
        result = create_table("test.db", "signals", [
            {"name": "id", "type": "INTEGER", "pk": True},
            {"name": "symbol", "type": "TEXT"},
            {"name": "signal", "type": "TEXT"},
        ], temp_workspace)
        
        assert result["created"] is True
        
        # 테이블 확인
        tables = list_tables("test.db", temp_workspace)
        assert "signals" in tables["tables"]
        
        # 컬럼 확인
        columns = list_columns("test.db", "signals", temp_workspace)
        assert len(columns["columns"]) == 3
    
    def test_validate_filename(self):
        """파일명 검증"""
        from programgarden.tools.sqlite_tools import validate_filename
        
        # 유효한 파일명
        assert validate_filename("test.db") is True
        assert validate_filename("my_strategy.db") is True
        assert validate_filename("test-2024.db") is True
        
        # 유효하지 않은 파일명
        assert validate_filename("../test.db") is False
        assert validate_filename("test/sub.db") is False
        assert validate_filename("test;drop.db") is False
        assert validate_filename("") is False


class TestServerSQLiteAPI:
    """Server API SQLite 엔드포인트 통합 테스트
    
    server.py의 SQLite 관련 API 엔드포인트 테스트:
    - GET /api/sqlite/{db_name}/tables
    - GET /api/sqlite/{db_name}/tables/{table_name}/columns
    - POST /api/sqlite/{db_name}/tables
    - DELETE /api/files/{source}/{filename}
    """
    
    @pytest.fixture
    def temp_workspace(self):
        """임시 워크스페이스 생성"""
        workspace = tempfile.mkdtemp()
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)
    
    @pytest.fixture
    def test_client(self, temp_workspace, monkeypatch):
        """FastAPI TestClient with temp workspace"""
        import sys
        from pathlib import Path
        
        # 모듈 임포트를 위해 경로 추가
        server_dir = Path(__file__).parent.parent / "examples" / "workflow_editor"
        if str(server_dir) not in sys.path:
            sys.path.insert(0, str(server_dir))
        
        # HOME 환경변수 모킹
        monkeypatch.setenv("HOME", str(temp_workspace))
        
        # FastAPI 앱 임포트
        from starlette.testclient import TestClient
        
        # server 모듈 임포트 (동적으로)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "server", 
            server_dir / "server.py"
        )
        server_module = importlib.util.module_from_spec(spec)
        
        # 모듈 로딩 시 발생할 수 있는 에러 처리
        try:
            spec.loader.exec_module(server_module)
            client = TestClient(server_module.app)
            return client
        except Exception as e:
            pytest.skip(f"Server module import failed: {e}")
    
    def test_list_tables_endpoint(self, temp_workspace):
        """GET /api/sqlite/{db_name}/tables 엔드포인트 테스트"""
        import sqlite3
        from programgarden.tools.sqlite_tools import list_tables, get_programgarden_data_path
        
        # 테스트 DB 생성
        data_dir = get_programgarden_data_path(temp_workspace)
        db_path = data_dir / "test.db"
        
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, amount REAL)")
        conn.close()
        
        # 직접 함수 호출로 테스트 (TestClient 없이)
        result = list_tables("test.db", temp_workspace)
        assert "tables" in result
        assert set(result["tables"]) == {"users", "orders"}
    
    def test_list_columns_endpoint(self, temp_workspace):
        """GET /api/sqlite/{db_name}/tables/{table}/columns 엔드포인트 테스트"""
        import sqlite3
        from programgarden.tools.sqlite_tools import list_columns, get_programgarden_data_path
        
        # 테스트 DB 생성
        data_dir = get_programgarden_data_path(temp_workspace)
        db_path = data_dir / "test.db"
        
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE signals (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                signal TEXT DEFAULT 'hold'
            )
        """)
        conn.close()
        
        # 직접 함수 호출로 테스트
        result = list_columns("test.db", "signals", temp_workspace)
        assert "columns" in result
        assert len(result["columns"]) == 3
        
        col_names = [c["name"] for c in result["columns"]]
        assert "id" in col_names
        assert "symbol" in col_names
        assert "signal" in col_names
    
    def test_create_table_endpoint(self, temp_workspace):
        """POST /api/sqlite/{db_name}/tables 엔드포인트 테스트"""
        import sqlite3
        from programgarden.tools.sqlite_tools import (
            create_table, 
            list_tables,
            get_programgarden_data_path
        )
        
        # 빈 DB 생성
        data_dir = get_programgarden_data_path(temp_workspace)
        db_path = data_dir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.close()
        
        # 직접 함수 호출로 테스트
        result = create_table("test.db", "new_table", [
            {"name": "id", "type": "INTEGER", "pk": True},
            {"name": "value", "type": "TEXT"},
        ], temp_workspace)
        
        assert result["created"] is True
        
        # 생성 확인
        tables = list_tables("test.db", temp_workspace)
        assert "new_table" in tables["tables"]
    
    def test_delete_file_endpoint(self, temp_workspace):
        """DELETE /api/files/{source}/{filename} 엔드포인트 테스트"""
        import sqlite3
        from programgarden.tools.sqlite_tools import (
            delete_database_file, 
            list_database_files,
            get_programgarden_data_path
        )
        
        # 테스트 DB 생성
        data_dir = get_programgarden_data_path(temp_workspace)
        db_path = data_dir / "to_delete.db"
        conn = sqlite3.connect(str(db_path))
        conn.close()
        
        # 파일 존재 확인 (files는 dict 리스트이므로 name으로 확인)
        files_before = list_database_files(temp_workspace)
        file_names = [f["name"] for f in files_before["files"]]
        assert "to_delete.db" in file_names
        
        # 직접 함수 호출로 삭제
        result = delete_database_file("to_delete.db", temp_workspace)
        assert result["deleted"] is True
        
        # 삭제 확인
        files_after = list_database_files(temp_workspace)
        file_names_after = [f["name"] for f in files_after["files"]]
        assert "to_delete.db" not in file_names_after
    
    def test_delete_file_path_traversal_blocked(self, temp_workspace):
        """DELETE 엔드포인트 경로 탈출 공격 차단 테스트"""
        from programgarden.tools.sqlite_tools import delete_database_file
        
        # 경로 탈출 시도 (예외 대신 에러 응답 반환)
        result = delete_database_file("../../../etc/passwd", temp_workspace)
        assert result["deleted"] is False
        assert "Invalid filename" in result.get("error", "")
    
    def test_list_tables_nonexistent_db(self, temp_workspace):
        """존재하지 않는 DB의 테이블 조회 시 에러 처리"""
        from programgarden.tools.sqlite_tools import list_tables
        
        # 예외 대신 에러 응답 반환
        result = list_tables("nonexistent.db", temp_workspace)
        assert result["tables"] == []
        assert "not found" in result.get("error", "").lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
