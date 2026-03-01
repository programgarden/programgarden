"""
CheckpointManager - 워크플로우 실행 체크포인트 관리

기존 {workflow_id}_workflow.db에 테이블을 추가하여
실행 상태를 저장/복원합니다.
"""

import json
import hashlib
import logging
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 대형 output 스킵 임계값 (1MB)
MAX_OUTPUT_SIZE = 1_048_576


class CheckpointManager:
    """워크플로우 실행 체크포인트 관리.

    기존 workflow.db에 checkpoint_meta / checkpoint_outputs
    테이블을 추가하여 노드 실행 상태와 outputs를 저장합니다.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_tables()

    # ============================================================
    # 테이블 초기화
    # ============================================================

    def _ensure_tables(self) -> None:
        """checkpoint 테이블 생성 (없으면)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoint_meta (
                    job_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    workflow_type TEXT NOT NULL,
                    completed_nodes TEXT NOT NULL,
                    stats TEXT NOT NULL,
                    context_params TEXT,
                    workflow_json_hash TEXT,
                    workflow_start_datetime TEXT,
                    risk_halt INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoint_outputs (
                    job_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    port_name TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    value_type TEXT NOT NULL DEFAULT 'json',
                    PRIMARY KEY (job_id, node_id, port_name)
                )
            """)
            conn.commit()

    # ============================================================
    # 직렬화/역직렬화
    # ============================================================

    @staticmethod
    def _serialize_value(value: Any) -> Tuple[str, str]:
        """값을 (value_json, value_type)으로 변환.

        WorkflowRiskTracker._serialize_state_value 패턴 재사용.
        """
        if value is None:
            return "null", "null"
        if isinstance(value, bool):
            return json.dumps(value), "bool"
        if isinstance(value, int):
            return str(value), "int"
        if isinstance(value, float):
            return str(value), "float"
        if isinstance(value, Decimal):
            return str(value), "decimal"
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str), "json"
        return str(value), "string"

    @staticmethod
    def _deserialize_value(value_json: Optional[str], value_type: str) -> Any:
        """직렬화된 값을 원래 타입으로 복원."""
        if value_json is None or value_type == "null":
            return None
        if value_type == "bool":
            return json.loads(value_json)
        if value_type == "int":
            return int(value_json)
        if value_type == "float":
            return float(value_json)
        if value_type == "decimal":
            return Decimal(value_json)
        if value_type == "json":
            return json.loads(value_json)
        return value_json

    @staticmethod
    def compute_workflow_hash(definition: Dict[str, Any]) -> str:
        """워크플로우 정의의 해시를 계산 (변경 감지용)."""
        # nodes와 edges만으로 해시 (credentials/notes 제외)
        hashable = {
            "nodes": definition.get("nodes", []),
            "edges": definition.get("edges", []),
        }
        raw = json.dumps(hashable, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ============================================================
    # CRUD
    # ============================================================

    def save_checkpoint(
        self,
        job_id: str,
        workflow_id: str,
        status: str,
        workflow_type: str,
        completed_nodes: List[str],
        stats: Dict[str, Any],
        node_outputs: Dict[str, Dict[str, Any]],
        workflow_json_hash: Optional[str] = None,
        workflow_start_datetime: Optional[str] = None,
        risk_halt: bool = False,
        context_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """체크포인트 저장 (UPSERT)."""
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Meta UPSERT
            conn.execute("""
                INSERT INTO checkpoint_meta
                    (job_id, workflow_id, status, workflow_type,
                     completed_nodes, stats, context_params,
                     workflow_json_hash, workflow_start_datetime,
                     risk_halt, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status,
                    workflow_type=excluded.workflow_type,
                    completed_nodes=excluded.completed_nodes,
                    stats=excluded.stats,
                    context_params=excluded.context_params,
                    workflow_json_hash=excluded.workflow_json_hash,
                    workflow_start_datetime=excluded.workflow_start_datetime,
                    risk_halt=excluded.risk_halt,
                    created_at=excluded.created_at
            """, (
                job_id, workflow_id, status, workflow_type,
                json.dumps(completed_nodes),
                json.dumps(stats, default=str),
                json.dumps(context_params, default=str) if context_params else None,
                workflow_json_hash,
                workflow_start_datetime,
                1 if risk_halt else 0,
                now,
            ))

            # Outputs: 기존 삭제 후 재삽입
            conn.execute(
                "DELETE FROM checkpoint_outputs WHERE job_id = ?",
                (job_id,),
            )

            for node_id, ports in node_outputs.items():
                for port_name, value in ports.items():
                    value_json, value_type = self._serialize_value(value)
                    # 대형 output (>1MB) 스킵
                    if len(value_json) > MAX_OUTPUT_SIZE:
                        logger.warning(
                            f"Checkpoint: 대형 output 스킵 ({node_id}.{port_name}, "
                            f"{len(value_json)} bytes)"
                        )
                        continue
                    conn.execute("""
                        INSERT INTO checkpoint_outputs
                            (job_id, node_id, port_name, value_json, value_type)
                        VALUES (?, ?, ?, ?, ?)
                    """, (job_id, node_id, port_name, value_json, value_type))

            conn.commit()

        logger.debug(
            f"Checkpoint 저장: job={job_id}, "
            f"completed={len(completed_nodes)}, outputs={sum(len(p) for p in node_outputs.values())}"
        )

    def load_checkpoint(self, job_id: str) -> Optional[Dict[str, Any]]:
        """체크포인트 로드 (meta + outputs)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM checkpoint_meta WHERE job_id = ?",
                (job_id,),
            ).fetchone()

            if not row:
                return None

            meta = dict(row)
            meta["completed_nodes"] = json.loads(meta["completed_nodes"])
            meta["stats"] = json.loads(meta["stats"])
            meta["risk_halt"] = bool(meta["risk_halt"])
            if meta["context_params"]:
                meta["context_params"] = json.loads(meta["context_params"])

            # Outputs 로드
            output_rows = conn.execute(
                "SELECT node_id, port_name, value_json, value_type "
                "FROM checkpoint_outputs WHERE job_id = ?",
                (job_id,),
            ).fetchall()

            node_outputs: Dict[str, Dict[str, Any]] = {}
            for orow in output_rows:
                nid = orow["node_id"]
                if nid not in node_outputs:
                    node_outputs[nid] = {}
                node_outputs[nid][orow["port_name"]] = self._deserialize_value(
                    orow["value_json"], orow["value_type"],
                )

            meta["node_outputs"] = node_outputs
            return meta

    def delete_checkpoint(self, job_id: str) -> None:
        """체크포인트 삭제 (정상 완료 시)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM checkpoint_meta WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM checkpoint_outputs WHERE job_id = ?", (job_id,))
            conn.commit()
        logger.debug(f"Checkpoint 삭제: job={job_id}")

    def has_checkpoint(self, job_id: str) -> bool:
        """체크포인트 존재 여부."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM checkpoint_meta WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            return row is not None

    def get_checkpoint_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """체크포인트 요약 정보 (outputs 제외, 경량 조회)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT job_id, workflow_id, status, workflow_type, "
                "completed_nodes, stats, workflow_start_datetime, "
                "risk_halt, created_at FROM checkpoint_meta WHERE job_id = ?",
                (job_id,),
            ).fetchone()

            if not row:
                return None

            info = dict(row)
            info["completed_nodes"] = json.loads(info["completed_nodes"])
            info["stats"] = json.loads(info["stats"])
            info["risk_halt"] = bool(info["risk_halt"])
            return info
