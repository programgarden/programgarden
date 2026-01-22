"""
ProgramGarden - SQL Query Builder

SQL 쿼리 빌드 유틸리티:
- select, insert, update, delete, upsert 쿼리 생성
- 파라미터 바인딩 (SQL 인젝션 방지)
"""

from typing import List, Dict, Any, Optional, Tuple
import re


class SQLQueryBuilder:
    """
    SQL 쿼리 빌더
    
    파라미터 바인딩을 사용하여 SQL 인젝션을 방지하면서
    간단한 CRUD 쿼리를 생성합니다.
    """
    
    @staticmethod
    def validate_identifier(name: str) -> str:
        """
        SQL 식별자(테이블명, 컬럼명) 검증
        
        SQL 인젝션 방지를 위해 식별자에 허용되지 않는 문자가 있으면 에러 발생
        
        Args:
            name: 검증할 식별자
            
        Returns:
            검증된 식별자
            
        Raises:
            ValueError: 유효하지 않은 식별자
        """
        if not name:
            raise ValueError("Identifier cannot be empty")
        
        # 허용: 알파벳, 숫자, 언더스코어만
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            raise ValueError(f"Invalid identifier: {name}. Only alphanumeric and underscore allowed.")
        
        return name
    
    @staticmethod
    def build_select(
        table: str,
        columns: Optional[List[str]] = None,
        where_clause: Optional[str] = None,
    ) -> str:
        """
        SELECT 쿼리 생성
        
        Args:
            table: 테이블명
            columns: 조회할 컬럼 목록 (None이면 *)
            where_clause: WHERE 조건절 (파라미터 바인딩 사용: :param_name)
            
        Returns:
            SELECT SQL 쿼리
        """
        table = SQLQueryBuilder.validate_identifier(table)
        
        # columns 검증 및 빌드
        if columns:
            validated_cols = [SQLQueryBuilder.validate_identifier(c) for c in columns]
            cols_str = ", ".join(validated_cols)
        else:
            cols_str = "*"
        
        query = f"SELECT {cols_str} FROM {table}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        return query
    
    @staticmethod
    def build_insert(
        table: str,
        columns: List[str],
    ) -> str:
        """
        INSERT 쿼리 생성
        
        Args:
            table: 테이블명
            columns: 삽입할 컬럼 목록
            
        Returns:
            INSERT SQL 쿼리 (파라미터 플레이스홀더 포함)
        """
        table = SQLQueryBuilder.validate_identifier(table)
        validated_cols = [SQLQueryBuilder.validate_identifier(c) for c in columns]
        
        cols_str = ", ".join(validated_cols)
        placeholders = ", ".join([f":{c}" for c in validated_cols])
        
        return f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})"
    
    @staticmethod
    def build_update(
        table: str,
        columns: List[str],
        where_clause: Optional[str] = None,
    ) -> str:
        """
        UPDATE 쿼리 생성
        
        Args:
            table: 테이블명
            columns: 수정할 컬럼 목록
            where_clause: WHERE 조건절
            
        Returns:
            UPDATE SQL 쿼리
        """
        table = SQLQueryBuilder.validate_identifier(table)
        validated_cols = [SQLQueryBuilder.validate_identifier(c) for c in columns]
        
        set_clause = ", ".join([f"{c} = :{c}" for c in validated_cols])
        
        query = f"UPDATE {table} SET {set_clause}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        return query
    
    @staticmethod
    def build_delete(
        table: str,
        where_clause: Optional[str] = None,
    ) -> str:
        """
        DELETE 쿼리 생성
        
        Args:
            table: 테이블명
            where_clause: WHERE 조건절
            
        Returns:
            DELETE SQL 쿼리
        """
        table = SQLQueryBuilder.validate_identifier(table)
        
        query = f"DELETE FROM {table}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        return query
    
    @staticmethod
    def build_upsert(
        table: str,
        columns: List[str],
        on_conflict: str,
    ) -> str:
        """
        UPSERT (INSERT OR REPLACE) 쿼리 생성
        
        SQLite의 INSERT ... ON CONFLICT ... DO UPDATE 구문 사용
        
        Args:
            table: 테이블명
            columns: 삽입/수정할 컬럼 목록
            on_conflict: 충돌 기준 컬럼
            
        Returns:
            UPSERT SQL 쿼리
        """
        table = SQLQueryBuilder.validate_identifier(table)
        conflict_col = SQLQueryBuilder.validate_identifier(on_conflict)
        validated_cols = [SQLQueryBuilder.validate_identifier(c) for c in columns]
        
        cols_str = ", ".join(validated_cols)
        placeholders = ", ".join([f":{c}" for c in validated_cols])
        
        # ON CONFLICT DO UPDATE: 충돌 컬럼 제외한 나머지 컬럼 업데이트
        update_cols = [c for c in validated_cols if c != conflict_col]
        update_set = ", ".join([f"{c} = excluded.{c}" for c in update_cols])
        
        query = f"""INSERT INTO {table} ({cols_str}) VALUES ({placeholders})
ON CONFLICT({conflict_col}) DO UPDATE SET {update_set}"""
        
        return query
    
    @staticmethod
    def extract_params_from_where(
        where_clause: str,
        provided_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        WHERE 절에서 파라미터 추출
        
        :param_name 형식의 플레이스홀더를 찾아서 
        provided_params에서 매칭되는 값을 반환
        
        Args:
            where_clause: WHERE 조건절
            provided_params: 제공된 파라미터 딕셔너리
            
        Returns:
            파라미터 딕셔너리
        """
        if not where_clause:
            return {}
        
        # :param_name 패턴 찾기
        param_names = re.findall(r':([a-zA-Z_][a-zA-Z0-9_]*)', where_clause)
        
        if not provided_params:
            return {name: None for name in param_names}
        
        return {name: provided_params.get(name) for name in param_names}
