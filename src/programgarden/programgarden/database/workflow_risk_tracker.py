"""
WorkflowRiskTracker - Feature-gated 위험관리 데이터 추적기

워크플로우 내 노드/플러그인이 선언한 feature만 선택적으로 활성화하는
2-Layer (Hot/Cold) 위험관리 데이터 인프라.

주요 기능:
- HWM (High Water Mark) 추적: 인메모리 O(1) + 주기적 DB flush
- 슬라이딩 윈도우 메트릭: 변동성, MDD 계산
- 위험 이벤트 감사 이력
- 전략 상태 KV 저장소

Feature 목록:
- "hwm": HWM/drawdown 추적 (Hot + Cold)
- "window": 슬라이딩 윈도우 메트릭 (Hot only)
- "events": 위험 이벤트 감사 이력 (Cold only)
- "state": 전략 상태 KV 저장소 (Cold only)
"""

import asyncio
import json
import logging
import sqlite3
import statistics
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Deque, Dict, FrozenSet, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

VALID_FEATURES: Set[str] = {"hwm", "window", "events", "state"}


# ============================================================
# Dataclasses
# ============================================================

@dataclass
class HWMState:
    """인메모리 HWM 상태"""
    symbol: str
    exchange: str
    hwm_price: Decimal
    hwm_datetime: datetime
    current_price: Decimal
    drawdown_pct: Decimal
    position_qty: int
    position_avg_price: Decimal
    dirty: bool = True


@dataclass
class HWMUpdateResult:
    """update_price 반환 결과"""
    symbol: str
    high_water_mark: Decimal
    current_price: Decimal
    drawdown_pct: Decimal
    hwm_updated: bool


@dataclass
class HWMValidationResult:
    """재시작 시 HWM 검증 결과"""
    symbol: str
    action: str    # "kept" | "reset" | "deleted" | "new"
    reason: str
    old_hwm: Optional[Decimal] = None
    new_hwm: Optional[Decimal] = None


class WorkflowRiskTracker:
    """Feature-gated 위험관리 추적기.

    워크플로우 내 노드/플러그인이 선언한 feature만 활성화.
    아무도 선언하지 않으면 이 클래스 자체가 생성되지 않음.
    """

    FLUSH_INTERVAL = 30          # HWM flush 주기 (초)
    PRICE_WINDOW_SIZE = 300      # 슬라이딩 윈도우 최대 크기
    METRICS_CACHE_TTL = 5        # 메트릭 캐시 TTL (초)

    def __init__(
        self,
        db_path: str,
        job_id: str,
        product: str,
        provider: str,
        trading_mode: str,
        features: Set[str],
    ):
        self.db_path = db_path
        self.job_id = job_id
        self.product = product
        self.provider = provider
        self.trading_mode = trading_mode
        self._features: FrozenSet[str] = frozenset(features & VALID_FEATURES)

        # ━━━ Feature-gated 초기화 ━━━

        # "hwm" → HWM 추적
        self._hwm: Optional[Dict[str, HWMState]] = None
        if "hwm" in self._features:
            self._hwm = {}
            self._init_hwm_table()

        # "window" → 슬라이딩 윈도우
        self._price_window: Optional[Deque[Tuple[str, Decimal, datetime]]] = None
        self._metrics_cache: Optional[Dict[str, Any]] = None
        self._metrics_cache_time: float = 0.0
        if "window" in self._features:
            self._price_window = deque(maxlen=self.PRICE_WINDOW_SIZE)
            self._metrics_cache = {}

        # "events" → 위험 이벤트
        if "events" in self._features:
            self._init_events_table()

        # "state" → 전략 상태 KV
        if "state" in self._features:
            self._init_state_table()

        # Hot → Cold flush
        self._flush_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._consecutive_flush_failures: int = 0

        # DB → 메모리 복원
        if "hwm" in self._features:
            self._load_hwm_from_db()

        logger.info(
            f"RiskTracker 초기화: features={set(self._features)}, "
            f"product={product}, trading_mode={trading_mode}"
        )

    # ============================================================
    # Feature query
    # ============================================================

    def has_feature(self, feature: str) -> bool:
        return feature in self._features

    @property
    def features(self) -> FrozenSet[str]:
        return self._features

    # ============================================================
    # DB 테이블 초기화 (Cold Layer)
    # ============================================================

    def _ensure_db_dir(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _enable_wal_mode(self) -> None:
        """SQLite WAL 모드 활성화 (멀티 워크플로우 동시 접근 지원)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
        except Exception as e:
            logger.warning(f"RiskTracker: WAL 모드 설정 실패: {e}")

    def _init_hwm_table(self) -> None:
        self._ensure_db_dir()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS risk_high_water_mark (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    exchange TEXT,
                    high_water_mark REAL NOT NULL,
                    hwm_datetime TEXT NOT NULL,
                    current_price REAL,
                    current_drawdown_pct REAL,
                    position_qty INTEGER,
                    position_avg_price REAL,
                    trading_mode TEXT NOT NULL DEFAULT 'live',
                    updated_at TEXT NOT NULL,
                    UNIQUE(product, provider, symbol, trading_mode)
                )
            """)

    def _init_events_table(self) -> None:
        self._ensure_db_dir()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS risk_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'warning',
                    symbol TEXT,
                    exchange TEXT,
                    details TEXT,
                    job_id TEXT,
                    node_id TEXT,
                    trading_mode TEXT NOT NULL DEFAULT 'live',
                    created_at TEXT NOT NULL
                )
            """)

    def _init_state_table(self) -> None:
        self._ensure_db_dir()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    state_key TEXT NOT NULL,
                    state_value TEXT,
                    value_type TEXT NOT NULL DEFAULT 'string',
                    trading_mode TEXT NOT NULL DEFAULT 'live',
                    updated_at TEXT NOT NULL,
                    UNIQUE(product, provider, state_key, trading_mode)
                )
            """)

    # ============================================================
    # Feature "hwm" — HWM 추적 (Hot Layer)
    # ============================================================

    def register_symbol(
        self,
        symbol: str,
        exchange: str,
        entry_price: float,
        qty: int,
    ) -> None:
        """매수 체결 시 HWM 등록."""
        if self._hwm is None:
            return

        price = Decimal(str(entry_price))
        now = datetime.now(timezone.utc)

        existing = self._hwm.get(symbol)
        if existing:
            # 추가 매수: 평단가 업데이트, HWM은 유지
            total_qty = existing.position_qty + qty
            total_cost = existing.position_avg_price * existing.position_qty + price * qty
            new_avg = total_cost / total_qty
            existing.position_qty = total_qty
            existing.position_avg_price = new_avg
            existing.dirty = True
        else:
            self._hwm[symbol] = HWMState(
                symbol=symbol,
                exchange=exchange,
                hwm_price=price,
                hwm_datetime=now,
                current_price=price,
                drawdown_pct=Decimal("0"),
                position_qty=qty,
                position_avg_price=price,
                dirty=True,
            )

    def unregister_symbol(self, symbol: str) -> None:
        """전량 청산 시 HWM 제거."""
        if self._hwm is None:
            return
        self._hwm.pop(symbol, None)

    def update_price(
        self,
        symbol: str,
        exchange: str,
        price: float,
        timestamp: Optional[datetime] = None,
    ) -> Optional[HWMUpdateResult]:
        """매 틱 호출. hwm feature 없으면 None 반환."""
        if self._hwm is None:
            return None

        ts = timestamp or datetime.now(timezone.utc)
        dec_price = Decimal(str(price))

        # window feature 연동
        if self._price_window is not None:
            self._price_window.append((symbol, dec_price, ts))

        state = self._hwm.get(symbol)
        if state is None:
            return None

        state.current_price = dec_price
        hwm_updated = False

        if dec_price > state.hwm_price:
            state.hwm_price = dec_price
            state.hwm_datetime = ts
            state.drawdown_pct = Decimal("0")
            hwm_updated = True
        else:
            if state.hwm_price > 0:
                dd = ((state.hwm_price - dec_price) / state.hwm_price * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                state.drawdown_pct = dd

        state.dirty = True

        return HWMUpdateResult(
            symbol=symbol,
            high_water_mark=state.hwm_price,
            current_price=dec_price,
            drawdown_pct=state.drawdown_pct,
            hwm_updated=hwm_updated,
        )

    def get_hwm(self, symbol: str) -> Optional[HWMState]:
        """조회. hwm feature 없으면 None."""
        if self._hwm is None:
            return None
        return self._hwm.get(symbol)

    def get_all_hwm(self) -> Dict[str, HWMState]:
        if self._hwm is None:
            return {}
        return dict(self._hwm)

    def has_hwm_data(self) -> bool:
        """DB에 HWM 데이터가 존재하는지 확인."""
        if "hwm" not in self._features:
            return False
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM risk_high_water_mark "
                    "WHERE product=? AND provider=? AND trading_mode=?",
                    (self.product, self.provider, self.trading_mode),
                ).fetchone()
                return (row[0] or 0) > 0
        except Exception:
            return False

    def check_drawdown_threshold(self, symbol: str, threshold_pct: float) -> bool:
        """drawdown이 threshold를 초과하는지 확인."""
        if self._hwm is None:
            return False
        state = self._hwm.get(symbol)
        if state is None:
            return False
        return float(state.drawdown_pct) > threshold_pct

    # ============================================================
    # Feature "hwm" — Cold Layer (flush)
    # ============================================================

    async def flush_to_db(self) -> int:
        """dirty HWM만 배치 write. 쓴 개수 반환."""
        if self._hwm is None:
            return 0

        async with self._flush_lock:
            dirty_items = [
                s for s in self._hwm.values() if s.dirty
            ]
            if not dirty_items:
                return 0

            now = datetime.now(timezone.utc).isoformat()

            def _write():
                with sqlite3.connect(self.db_path) as conn:
                    for s in dirty_items:
                        conn.execute(
                            """
                            INSERT INTO risk_high_water_mark
                                (product, provider, symbol, exchange,
                                 high_water_mark, hwm_datetime,
                                 current_price, current_drawdown_pct,
                                 position_qty, position_avg_price,
                                 trading_mode, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(product, provider, symbol, trading_mode)
                            DO UPDATE SET
                                exchange=excluded.exchange,
                                high_water_mark=excluded.high_water_mark,
                                hwm_datetime=excluded.hwm_datetime,
                                current_price=excluded.current_price,
                                current_drawdown_pct=excluded.current_drawdown_pct,
                                position_qty=excluded.position_qty,
                                position_avg_price=excluded.position_avg_price,
                                updated_at=excluded.updated_at
                            """,
                            (
                                self.product, self.provider,
                                s.symbol, s.exchange,
                                float(s.hwm_price), s.hwm_datetime.isoformat(),
                                float(s.current_price), float(s.drawdown_pct),
                                s.position_qty, float(s.position_avg_price),
                                self.trading_mode, now,
                            ),
                        )

            await asyncio.get_event_loop().run_in_executor(None, _write)

            for s in dirty_items:
                s.dirty = False

            logger.debug(f"RiskTracker flush: {len(dirty_items)} HWM records")
            return len(dirty_items)

    def _load_hwm_from_db(self) -> None:
        """Cold → Hot 복원."""
        if self._hwm is None:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT symbol, exchange, high_water_mark, hwm_datetime,
                           current_price, current_drawdown_pct,
                           position_qty, position_avg_price
                    FROM risk_high_water_mark
                    WHERE product=? AND provider=? AND trading_mode=?
                    """,
                    (self.product, self.provider, self.trading_mode),
                ).fetchall()

                for row in rows:
                    self._hwm[row["symbol"]] = HWMState(
                        symbol=row["symbol"],
                        exchange=row["exchange"] or "",
                        hwm_price=Decimal(str(row["high_water_mark"])),
                        hwm_datetime=datetime.fromisoformat(row["hwm_datetime"]),
                        current_price=Decimal(str(row["current_price"] or row["high_water_mark"])),
                        drawdown_pct=Decimal(str(row["current_drawdown_pct"] or 0)),
                        position_qty=row["position_qty"] or 0,
                        position_avg_price=Decimal(str(row["position_avg_price"] or 0)),
                        dirty=False,
                    )

                if rows:
                    logger.info(f"RiskTracker: DB에서 {len(rows)}개 HWM 복원")
        except sqlite3.OperationalError:
            # 테이블이 없을 수 있음 (첫 실행 직후)
            pass

    def validate_hwm_on_restart(
        self,
        position_tracker: Any,
    ) -> List[HWMValidationResult]:
        """PositionTracker 포지션과 비교하여 HWM 유효성 검증."""
        if self._hwm is None:
            return []

        results: List[HWMValidationResult] = []

        # 현재 포지션 조회
        try:
            positions = position_tracker.get_workflow_positions()
        except Exception:
            positions = {}

        # position_tracker의 포지션 데이터를 symbol → info 매핑으로 변환
        pos_map: Dict[str, Any] = {}
        if isinstance(positions, dict):
            pos_map = positions
        elif isinstance(positions, list):
            for p in positions:
                sym = getattr(p, "symbol", None) or (p.get("symbol") if isinstance(p, dict) else None)
                if sym:
                    pos_map[sym] = p

        # 기존 HWM 검증
        symbols_to_delete = []
        for symbol, state in self._hwm.items():
            if symbol not in pos_map:
                # 포지션 없음 → 삭제
                symbols_to_delete.append(symbol)
                results.append(HWMValidationResult(
                    symbol=symbol,
                    action="deleted",
                    reason="포지션 없음 (청산됨)",
                    old_hwm=state.hwm_price,
                ))
            else:
                pos = pos_map[symbol]
                pos_qty = getattr(pos, "quantity", None) or (pos.get("quantity") if isinstance(pos, dict) else 0) or 0
                pos_avg = getattr(pos, "avg_price", None) or (pos.get("avg_price") if isinstance(pos, dict) else 0) or 0

                if pos_qty != state.position_qty or abs(float(pos_avg) - float(state.position_avg_price)) > 0.01:
                    # 수량/평단 변동 → 리셋
                    old_hwm = state.hwm_price
                    state.position_qty = int(pos_qty)
                    state.position_avg_price = Decimal(str(pos_avg))
                    state.hwm_price = Decimal(str(pos_avg))
                    state.hwm_datetime = datetime.now(timezone.utc)
                    state.drawdown_pct = Decimal("0")
                    state.dirty = True
                    results.append(HWMValidationResult(
                        symbol=symbol,
                        action="reset",
                        reason=f"수량/평단 변동 (qty={pos_qty}, avg={pos_avg})",
                        old_hwm=old_hwm,
                        new_hwm=state.hwm_price,
                    ))
                else:
                    results.append(HWMValidationResult(
                        symbol=symbol,
                        action="kept",
                        reason="동일 포지션",
                    ))

        for s in symbols_to_delete:
            del self._hwm[s]

        # 신규 종목 (포지션 있지만 HWM 없는 경우)
        for symbol, pos in pos_map.items():
            if symbol not in self._hwm:
                pos_qty = getattr(pos, "quantity", None) or (pos.get("quantity") if isinstance(pos, dict) else 0) or 0
                pos_avg = getattr(pos, "avg_price", None) or (pos.get("avg_price") if isinstance(pos, dict) else 0) or 0
                exchange = getattr(pos, "exchange", None) or (pos.get("exchange") if isinstance(pos, dict) else "") or ""

                if pos_qty > 0:
                    avg_dec = Decimal(str(pos_avg))
                    self._hwm[symbol] = HWMState(
                        symbol=symbol,
                        exchange=exchange,
                        hwm_price=avg_dec,
                        hwm_datetime=datetime.now(timezone.utc),
                        current_price=avg_dec,
                        drawdown_pct=Decimal("0"),
                        position_qty=int(pos_qty),
                        position_avg_price=avg_dec,
                        dirty=True,
                    )
                    results.append(HWMValidationResult(
                        symbol=symbol,
                        action="new",
                        reason="신규 포지션",
                        new_hwm=avg_dec,
                    ))

        return results

    # ============================================================
    # Feature "window" — 슬라이딩 윈도우 메트릭
    # ============================================================

    def add_tick(self, symbol: str, price: float, timestamp: Optional[datetime] = None) -> None:
        """update_price와 독립적으로 tick 추가 (window only)."""
        if self._price_window is None:
            return
        ts = timestamp or datetime.now(timezone.utc)
        self._price_window.append((symbol, Decimal(str(price)), ts))

    def get_volatility(self, symbol: str) -> Optional[Decimal]:
        """5분 변동성 (표준편차). 데이터 30틱 미만 시 None."""
        if self._price_window is None:
            return None

        prices = [float(p) for s, p, t in self._price_window if s == symbol]
        if len(prices) < 30:
            return None

        try:
            stdev = statistics.stdev(prices)
            mean = statistics.mean(prices)
            if mean == 0:
                return Decimal("0")
            cv = (stdev / mean * 100)
            return Decimal(str(cv)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except statistics.StatisticsError:
            return None

    def get_max_drawdown_window(self, symbol: Optional[str] = None) -> Optional[Decimal]:
        """윈도우 내 최대 낙폭(%). symbol=None이면 전체."""
        if self._price_window is None:
            return None

        prices = [
            float(p)
            for s, p, t in self._price_window
            if symbol is None or s == symbol
        ]
        if len(prices) < 2:
            return None

        peak = prices[0]
        max_dd = 0.0
        for p in prices:
            if p > peak:
                peak = p
            dd = (peak - p) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return Decimal(str(max_dd)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def get_tick_count(self, symbol: str, seconds: int = 60) -> int:
        """최근 N초 내 해당 symbol 틱 수."""
        if self._price_window is None:
            return 0

        cutoff = datetime.now(timezone.utc)
        count = 0
        for s, p, t in reversed(self._price_window):
            if (cutoff - t).total_seconds() > seconds:
                break
            if s == symbol:
                count += 1
        return count

    # ============================================================
    # Feature "events" — 위험 이벤트 (Cold Layer)
    # ============================================================

    def record_risk_event(
        self,
        event_type: str,
        severity: str = "warning",
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None,
    ) -> Optional[int]:
        """events feature 없으면 None 반환. 즉시 INSERT."""
        if "events" not in self._features:
            return None

        now = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details, default=str) if details else None

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO risk_events
                        (product, provider, event_type, severity,
                         symbol, exchange, details, job_id, node_id,
                         trading_mode, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.product, self.provider,
                        event_type, severity,
                        symbol, exchange, details_json,
                        self.job_id, node_id,
                        self.trading_mode, now,
                    ),
                )
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"RiskTracker: 이벤트 기록 실패: {e}")
            return None

    def get_risk_events(
        self,
        event_type: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """위험 이벤트 조회."""
        if "events" not in self._features:
            return []

        try:
            conditions = [
                "product=?", "provider=?", "trading_mode=?"
            ]
            params: list = [self.product, self.provider, self.trading_mode]

            if event_type:
                conditions.append("event_type=?")
                params.append(event_type)
            if symbol:
                conditions.append("symbol=?")
                params.append(symbol)

            where = " AND ".join(conditions)
            params.append(limit)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    f"SELECT * FROM risk_events WHERE {where} "
                    f"ORDER BY created_at DESC LIMIT ?",
                    params,
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def get_risk_event_count(
        self,
        event_type: Optional[str] = None,
        since: Optional[str] = None,
    ) -> int:
        """위험 이벤트 수 조회."""
        if "events" not in self._features:
            return 0

        try:
            conditions = ["product=?", "provider=?", "trading_mode=?"]
            params: list = [self.product, self.provider, self.trading_mode]

            if event_type:
                conditions.append("event_type=?")
                params.append(event_type)
            if since:
                conditions.append("created_at>=?")
                params.append(since)

            where = " AND ".join(conditions)

            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM risk_events WHERE {where}",
                    params,
                ).fetchone()
                return row[0] or 0
        except Exception:
            return 0

    # ============================================================
    # Feature "state" — 전략 상태 KV (Cold Layer)
    # ============================================================

    def save_state(self, key: str, value: Any) -> bool:
        """state feature 없으면 False 반환. 즉시 UPSERT."""
        if "state" not in self._features:
            return False

        now = datetime.now(timezone.utc).isoformat()
        value_type, serialized = self._serialize_state_value(value)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO strategy_state
                        (product, provider, state_key, state_value,
                         value_type, trading_mode, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(product, provider, state_key, trading_mode)
                    DO UPDATE SET
                        state_value=excluded.state_value,
                        value_type=excluded.value_type,
                        updated_at=excluded.updated_at
                    """,
                    (
                        self.product, self.provider,
                        key, serialized, value_type,
                        self.trading_mode, now,
                    ),
                )
            return True
        except Exception as e:
            logger.error(f"RiskTracker: 상태 저장 실패 ({key}): {e}")
            return False

    def load_state(self, key: str, default: Any = None) -> Any:
        """state feature 없으면 default 반환."""
        if "state" not in self._features:
            return default

        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT state_value, value_type FROM strategy_state
                    WHERE product=? AND provider=? AND state_key=?
                      AND trading_mode=?
                    """,
                    (self.product, self.provider, key, self.trading_mode),
                ).fetchone()

                if row is None:
                    return default
                return self._deserialize_state_value(row[0], row[1])
        except Exception:
            return default

    def load_states(self, prefix: str) -> Dict[str, Any]:
        """prefix로 시작하는 모든 상태 조회."""
        if "state" not in self._features:
            return {}

        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT state_key, state_value, value_type FROM strategy_state
                    WHERE product=? AND provider=? AND state_key LIKE ?
                      AND trading_mode=?
                    """,
                    (self.product, self.provider, f"{prefix}%", self.trading_mode),
                ).fetchall()

                return {
                    row[0]: self._deserialize_state_value(row[1], row[2])
                    for row in rows
                }
        except Exception:
            return {}

    def delete_state(self, key: str) -> bool:
        """단일 상태 삭제."""
        if "state" not in self._features:
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM strategy_state
                    WHERE product=? AND provider=? AND state_key=?
                      AND trading_mode=?
                    """,
                    (self.product, self.provider, key, self.trading_mode),
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def delete_states(self, prefix: str) -> int:
        """prefix로 시작하는 모든 상태 삭제."""
        if "state" not in self._features:
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM strategy_state
                    WHERE product=? AND provider=? AND state_key LIKE ?
                      AND trading_mode=?
                    """,
                    (self.product, self.provider, f"{prefix}%", self.trading_mode),
                )
                return cursor.rowcount
        except Exception:
            return 0

    def save_snapshot(self, namespace: str, data: Dict[str, Any]) -> bool:
        """네임스페이스 하위에 dict를 일괄 저장."""
        if "state" not in self._features:
            return False

        success = True
        for k, v in data.items():
            if not self.save_state(f"{namespace}.{k}", v):
                success = False
        return success

    def load_snapshot(self, namespace: str) -> Dict[str, Any]:
        """네임스페이스 하위 상태를 dict로 복원."""
        raw = self.load_states(f"{namespace}.")
        prefix_len = len(f"{namespace}.")
        return {k[prefix_len:]: v for k, v in raw.items()}

    # ============================================================
    # State 직렬화/역직렬화
    # ============================================================

    @staticmethod
    def _serialize_state_value(value: Any) -> Tuple[str, str]:
        """값을 (value_type, serialized_string)으로 변환."""
        if isinstance(value, bool):
            return "bool", str(value)
        if isinstance(value, int):
            return "int", str(value)
        if isinstance(value, float):
            return "float", str(value)
        if isinstance(value, Decimal):
            return "decimal", str(value)
        if isinstance(value, (dict, list)):
            return "json", json.dumps(value, default=str)
        return "string", str(value)

    @staticmethod
    def _deserialize_state_value(serialized: Optional[str], value_type: str) -> Any:
        """직렬화된 값을 원래 타입으로 복원."""
        if serialized is None:
            return None

        if value_type == "bool":
            return serialized == "True"
        if value_type == "int":
            return int(serialized)
        if value_type == "float":
            return float(serialized)
        if value_type == "decimal":
            return Decimal(serialized)
        if value_type == "json":
            return json.loads(serialized)
        return serialized

    # ============================================================
    # Flush lifecycle
    # ============================================================

    def start_flush_loop(self) -> None:
        """hwm feature가 있을 때만 flush loop 시작."""
        if "hwm" not in self._features:
            return
        if self._flush_task is not None:
            return

        self._flush_task = asyncio.ensure_future(self._flush_loop())
        logger.debug("RiskTracker: flush loop 시작")

    async def _flush_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.FLUSH_INTERVAL)
                try:
                    count = await self.flush_to_db()
                    if count > 0:
                        self._consecutive_flush_failures = 0
                except Exception as e:
                    self._consecutive_flush_failures += 1
                    if self._consecutive_flush_failures >= 3:
                        logger.critical(
                            f"RiskTracker flush 연속 {self._consecutive_flush_failures}회 실패 "
                            f"- HWM 데이터 손실 위험: {e}"
                        )
                        # sync fallback 시도
                        try:
                            self._flush_to_db_sync()
                            self._consecutive_flush_failures = 0
                            logger.info("RiskTracker: sync fallback flush 성공")
                        except Exception as fe:
                            logger.critical(f"RiskTracker: sync fallback flush도 실패: {fe}")
                    else:
                        logger.error(f"RiskTracker flush 오류 ({self._consecutive_flush_failures}회): {e}")
        except asyncio.CancelledError:
            pass

    def _flush_to_db_sync(self) -> int:
        """동기 flush (async 실패 시 fallback)."""
        if self._hwm is None:
            return 0

        dirty_items = [s for s in self._hwm.values() if s.dirty]
        if not dirty_items:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            for s in dirty_items:
                conn.execute(
                    """
                    INSERT INTO risk_high_water_mark
                        (product, provider, symbol, exchange,
                         high_water_mark, hwm_datetime,
                         current_price, current_drawdown_pct,
                         position_qty, position_avg_price,
                         trading_mode, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(product, provider, symbol, trading_mode)
                    DO UPDATE SET
                        exchange=excluded.exchange,
                        high_water_mark=excluded.high_water_mark,
                        hwm_datetime=excluded.hwm_datetime,
                        current_price=excluded.current_price,
                        current_drawdown_pct=excluded.current_drawdown_pct,
                        position_qty=excluded.position_qty,
                        position_avg_price=excluded.position_avg_price,
                        updated_at=excluded.updated_at
                    """,
                    (
                        self.product, self.provider,
                        s.symbol, s.exchange,
                        float(s.hwm_price), s.hwm_datetime.isoformat(),
                        float(s.current_price), float(s.drawdown_pct),
                        s.position_qty, float(s.position_avg_price),
                        self.trading_mode, now,
                    ),
                )

        for s in dirty_items:
            s.dirty = False
        return len(dirty_items)

    async def stop_flush_loop(self) -> None:
        """최종 flush + loop 중단."""
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None

        # 최종 flush
        try:
            await self.flush_to_db()
        except Exception as e:
            logger.error(f"RiskTracker 최종 flush 오류: {e}")

        logger.debug("RiskTracker: flush loop 종료")

    # ============================================================
    # DB 정리 (HWM 삭제)
    # ============================================================

    def delete_hwm_from_db(self, symbol: str) -> None:
        """DB에서 특정 종목 HWM 삭제."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    DELETE FROM risk_high_water_mark
                    WHERE product=? AND provider=? AND symbol=?
                      AND trading_mode=?
                    """,
                    (self.product, self.provider, symbol, self.trading_mode),
                )
        except Exception as e:
            logger.error(f"RiskTracker: DB HWM 삭제 실패 ({symbol}): {e}")
