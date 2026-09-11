"""
WorkflowPositionTracker - 워크플로우 포지션 FIFO 추적

워크플로우에서 발생한 주문과 수동 주문을 분리하여 추적하고,
FIFO 방식으로 포지션을 관리합니다.

주요 기능:
- 워크플로우 주문 기록 (매수/매도)
- FIFO 기반 포지션 청산 처리
- 실시간 평가 수익률 계산
- 이상 거래 감지 및 신뢰도 점수 계산
"""

import sqlite3
import asyncio
import logging
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple, Callable, Awaitable
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 계약 승수(contract multiplier) 역산 안정화 파라미터 ──
# 브로커 pnl_amount 를 (현재가−평단)×수량 으로 나눠 승수를 역산할 때, 분모가
# 작으면(현재가≈평단) 반올림 오차가 증폭돼 mult 가 폭주한다. 아래 가드로 오염을
# 막고, 실패 시 심볼별 최근 성공값 캐시(없으면 1.0)로 폴백한다.
#
# _MULT_MIN_REL_GAP: |현재가−평단|/평단 이 이 값 미만이면 역산 생략. 0.1% 로 둔다 —
#   검증한 폭주 케이스(평단 8547.67, 현재가차 1.0 → 상대차 ≈0.0117%)를 잡아야 하므로
#   0.01% 는 부족(0.0117% > 0.01%)하고 0.1% 여야 확실히 걸린다.
# _MULT_MIN/_MULT_MAX: 표준 선물 승수는 0.5~수천 범위. 이 밴드 밖 역산값은 거부.
# _MULT_INT_SNAP_REL: 선물 승수는 정수 관행이라, 역산값이 최근접 정수와 상대오차
#   이 값 이내면 정수로 스냅(수수료 혼입/반올림 왜곡 완화).
_MULT_MIN_REL_GAP = Decimal("0.001")   # 0.1%
_MULT_MIN = Decimal("0.5")
_MULT_MAX = Decimal("10000")
_MULT_INT_SNAP_REL = Decimal("0.02")   # 2%


@dataclass
class PositionInfo:
    """포지션 정보"""
    symbol: str
    exchange: str
    quantity: Decimal  # 소수점(fractional) 잔고 대응 — 가격류와의 Decimal 혼합 산술 안전
    avg_price: Decimal
    classification: str  # "workflow" | "manual" | "unknown_api"


@dataclass
class LotInfo:
    """FIFO 로트 정보"""
    id: int
    symbol: str
    exchange: str
    fill_datetime: str  # YYYYMMDD_HHMMSSsss
    buy_price: Decimal
    original_qty: int
    remaining_qty: int
    classification: str


@dataclass
class AnomalyResult:
    """이상 거래 감지 결과"""
    pattern: str  # "sell_without_buy" | "quantity_imbalance" | "unknown_api_ratio"
    symbol: str
    description: str
    severity: int  # 감점 점수


@dataclass
class PendingFill:
    """버퍼링된 체결 정보"""
    order_no: str
    order_date: str
    symbol: str
    exchange: str
    side: str
    quantity: int
    price: float
    fill_time: str
    commda_code: str
    received_at: datetime
    execution_id: Optional[str | int] = None
    # Account average purchase price for this symbol at the moment of the fill,
    # read from the broker snapshot before it refreshes. Used only to estimate a
    # workflow sell's residual tail (see _process_sell_fifo); None → no estimate.
    account_avg_price: Optional[float] = None


class ExecutionIdentityConflictError(ValueError):
    """An explicit execution identity was replayed with different fill facts."""


# LS 통신매체코드(CommdaCode / MdaCode) — 출처: src/finance/docs/cidbq02400_contract.md:74-77
# "The published media map is 00=branch, 22=iPhone, 23=Android, 41=API, 43=Robo API,
#  85=HTS, 96=final settlement, LP=loss cut, SK=CashCall and SO=conditional order.
#  The example uses 40, which the table does not map. Preserve it as returned;
#  do not classify it by guessing a nearby code."
# '40' 은 표에 없지만 우리 OPEN API 주문이 실제로 받는 값이다(dev verified_fills 실측 4건 +
# 2026-09-12 해외주식 AS1 실측: 우리 매도 주문 244 → 40) — 표의 41/43 과 함께 API 묶음으로 둔다.
# 🔴 해외주식 AS1 실측(2026-09-12, 실계좌 NIO 1주씩): HTS → 85(표와 일치) · iPhone 투혼앱 → **51**
# (표의 22 아님) · 투혼 웹 → **03**(표에 없음). 표는 해외선물 TR 문서라 해외주식 푸시와 앱/웹 코드가
# 다르다. 관측된 값만 사람 채널에 추가한다 — 표에 없고 관측도 안 된 값은 여전히 "other".
MEDIA_CODES_HUMAN = frozenset({"85", "22", "23", "00", "51", "03"})   # HTS · iPhone(표) · Android(표) · 지점 · 투혼앱(실측) · 투혼웹(실측)
MEDIA_CODES_API = frozenset({"40", "41", "43"})                       # OPEN API(실측) · API · Robo API


def media_channel(commda_code: str | None) -> str:
    """Map a broker media code to "human" | "api" | "unknown" | "other".

    unknown = blank/None (the frame said nothing); other = a code the published
    table does not attribute to a person or an API client (96/LP/SK/SO …) or one
    the table does not list at all. Neither is ever asserted to be a person.
    """
    code = (commda_code or "").strip()
    if not code:
        return "unknown"
    if code in MEDIA_CODES_HUMAN:
        return "human"
    if code in MEDIA_CODES_API:
        return "api"
    return "other"


class WorkflowPositionTracker:
    """
    워크플로우 포지션 FIFO 추적기
    
    워크플로우 주문과 수동 주문을 분리하고 FIFO 방식으로 포지션을 관리합니다.
    """
    
    # 버퍼 타임아웃 (초)
    FILL_BUFFER_TIMEOUT = 2.0
    
    def __init__(
        self,
        db_path: str,
        job_id: str,
        broker_node_id: str,
        product: str = "overseas_stock",
        provider: str = "ls",
        trading_mode: str = "live",
    ):
        """
        Args:
            db_path: SQLite DB 경로
            job_id: Job ID
            broker_node_id: BrokerNode ID (로그용)
            product: 상품 유형 ("overseas_stock" | "overseas_futures")
            provider: 증권사 ("ls" | "kiwoom" | ...)
            trading_mode: 거래 모드 ("paper" | "live")
        """
        self.db_path = db_path
        self.job_id = job_id
        self.broker_node_id = broker_node_id  # 로그용으로 유지
        self.product = product
        self.provider = provider
        self.trading_mode = trading_mode

        # 체결 원장이 바뀔 때마다 증가한다. 읽는 쪽(개인 지표 캐시)이 "가격 틱은
        # 체결을 바꾸지 않는다"는 이유로 결과를 잠시 재사용하는데, 시간만 보고
        # 재사용하면 **막 들어온 체결을 놓친다**. 2026-09-10 실측: SNDL 체결이
        # 02:17:31.674 에 기록됐는데 봉투는 0.5초 전(02:17:31.189)에 계산된 값이
        # 그대로 굳어, 원장에 체결이 1건 있는데도 체결 주문 수가 0 으로 저장됐다.
        # 버퍼 처리처럼 컨텍스트를 거치지 않는 쓰기 경로까지 덮으려면 원장 자신이
        # 세는 게 맞다.
        self.fill_revision = 0

        # 체결 버퍼 (Race Condition 방어)
        # Every arrival without an execution ID remains a separate event. An
        # order can have multiple partial executions before its ACK is recorded.
        self._pending_fills: Dict[int, PendingFill] = {}
        self._next_pending_fill = 0
        self._buffer_lock = asyncio.Lock()

        # 심볼별 계약 승수(contract multiplier) 캐시.
        # 브로커 스냅샷의 pnl_amount 에서 역산한다(선물 승수 반영). 현재가≈평단이라
        # 역산 불가한 틱에서는 이 캐시(최근 성공값)로 폴백해 FIFO 산술을 스케일한다.
        self._multiplier_cache: Dict[str, Decimal] = {}

        # 체결 확정 콜백. 원장에 **새로** 기록된 체결마다 정확히 1회 발화한다 —
        # 즉시/버퍼/타임아웃 경로가 모두 _process_fill_internal 을 거치므로 한 곳에서
        # 부른다. 리플레이(동일 execution identity 재도착)는 그 앞에서 조기 반환하므로
        # 재발화하지 않는다. 컨텍스트가 이걸 on_order_fill 리스너로 연결한다.
        self._on_fill_classified: Optional[
            Callable[["PendingFill", str], Awaitable[None]]
        ] = None

        # DB 초기화
        self._init_db()

    def set_fill_classified_callback(
        self,
        callback: Optional[Callable[["PendingFill", str], Awaitable[None]]],
    ) -> None:
        """Register an async callback fired once per newly recorded fill.

        The callback receives ``(fill: PendingFill, classification: str)`` where
        classification is one of "workflow" | "manual" | "unknown_api" | "other".
        It must not mutate ledger state; exceptions raised by it are caught and
        logged so they never break FIFO recording.
        """
        self._on_fill_classified = callback

    def lookup_order_identity(
        self,
        order_no: str,
        order_date: str,
    ) -> Optional[Tuple[Optional[str], Optional[str]]]:
        """Return ``(job_id, node_id)`` for a recorded workflow order, else None.

        Scoped to this ledger's product/provider/trading mode and the order date.
        Matches the exact order number first, then the normalized form (so
        zero-padding differences between the order ACK and the fill still map).
        A fill that is not one of our workflow orders returns None (node_id then
        stays None on the emitted event).
        """
        try:
            norm = self._normalize_identifier(order_no)
        except ValueError:
            norm = None
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT order_no, job_id, node_id FROM workflow_orders
                    WHERE product = ? AND provider = ? AND trading_mode = ? AND order_date = ?
                    """,
                    (self.product, self.provider, self.trading_mode, order_date),
                ).fetchall()
        except Exception as e:
            logger.warning(f"lookup_order_identity failed: {e}")
            return None
        for row_order_no, job_id, node_id in rows:
            if row_order_no == order_no:
                return (job_id, node_id)
            if norm is not None:
                try:
                    if self._normalize_identifier(row_order_no) == norm:
                        return (job_id, node_id)
                except ValueError:
                    continue
        return None
    
    def _init_db(self) -> None:
        """데이터베이스 테이블 초기화"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # WAL 모드: 멀티 워크플로우 동시 접근 시 SQLITE_BUSY 방지
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            # 워크플로우 주문 기록
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    order_no TEXT NOT NULL,
                    order_date TEXT NOT NULL,
                    symbol TEXT,
                    exchange TEXT,
                    side TEXT,
                    quantity INTEGER,
                    price REAL,
                    job_id TEXT,
                    node_id TEXT,
                    trading_mode TEXT NOT NULL DEFAULT 'live',
                    created_at TEXT,
                    UNIQUE(order_no, order_date)
                )
            """)

            # 워크플로우 포지션 로트 (FIFO용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_position_lots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    exchange TEXT,
                    fill_datetime TEXT,
                    buy_price REAL,
                    original_qty INTEGER,
                    remaining_qty INTEGER,
                    classification TEXT,
                    order_no TEXT,
                    order_date TEXT,
                    trading_mode TEXT NOT NULL DEFAULT 'live',
                    created_at TEXT
                )
            """)

            # 체결 내역
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    order_no TEXT,
                    order_date TEXT,
                    symbol TEXT,
                    exchange TEXT,
                    side TEXT,
                    quantity INTEGER,
                    price REAL,
                    fill_datetime TEXT,
                    classification TEXT,
                    commda_code TEXT,
                    realized_pnl REAL,
                    trading_mode TEXT NOT NULL DEFAULT 'live',
                    created_at TEXT,
                    execution_id TEXT,
                    normalized_order_no TEXT,
                    execution_payload TEXT
                )
            """)

            # 상품+증권사 메타데이터 (현재 거래 모드 추적용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broker_metadata (
                    product TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    paper_trading INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (product, provider)
                )
            """)

            # 인덱스 생성 (trading_mode 포함)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_fifo_v2 ON workflow_position_lots(trading_mode, symbol, fill_datetime)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_lookup_v2 ON workflow_orders(trading_mode, order_no, order_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_remaining_v2 ON workflow_position_lots(trading_mode, symbol, remaining_qty)")

            # Additive migration: old rows have no evidence of execution identity.
            # Never infer or backfill one from timestamps, prices, or quantities.
            columns = {row[1] for row in cursor.execute("PRAGMA table_info(trade_history)")}
            for column in ("execution_id", "normalized_order_no", "execution_payload"):
                if column not in columns:
                    cursor.execute(f"ALTER TABLE trade_history ADD COLUMN {column} TEXT")
            # Additive columns for the account-average-price sell estimate. A
            # workflow sell that empties the strategy's own lots and still has a
            # tail records that tail here (the residual quantity, the account
            # average purchase price it was estimated against, the source label,
            # and the estimated PnL). realized_pnl stays FIFO-matched only; these
            # never enter _execution_facts / conflict detection. NULL on every
            # row that carries no estimate (buys, fully matched sells, old rows).
            for column, coltype in (("unmatched_qty", "REAL"),
                                    ("estimate_basis_price", "REAL"),
                                    ("estimate_source", "TEXT"),
                                    ("estimated_pnl", "REAL")):
                if column not in columns:
                    cursor.execute(f"ALTER TABLE trade_history ADD COLUMN {column} {coltype}")
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_trade_history_execution_v1
                ON trade_history(product, provider, trading_mode, order_date,
                                 normalized_order_no, execution_id)
                WHERE execution_id IS NOT NULL
            """)

            conn.commit()

    def update_trading_mode(self, trading_mode: str) -> None:
        """
        현재 거래 모드를 broker_metadata에 기록합니다.

        모의투자 ↔ 실전투자 전환 시 데이터를 초기화하지 않고,
        trading_mode 컬럼으로 분리 저장하여 각 모드의 수익률을 독립적으로 유지합니다.

        Args:
            trading_mode: 거래 모드 ("paper" | "live")
        """
        paper_trading_int = 1 if trading_mode == "paper" else 0
        identifier = f"{self.product}/{self.provider}"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT paper_trading FROM broker_metadata
                WHERE product = ? AND provider = ?
            """, (self.product, self.provider))

            row = cursor.fetchone()

            if row is None:
                cursor.execute("""
                    INSERT INTO broker_metadata (product, provider, paper_trading, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (self.product, self.provider, paper_trading_int, datetime.now().isoformat()))
                conn.commit()
                mode_label = "모의투자" if trading_mode == "paper" else "실전투자"
                logger.info(f"[{identifier}] Initial trading mode: {mode_label}")
                return

            prev_paper_trading = row[0]

            if prev_paper_trading != paper_trading_int:
                prev_mode = "모의투자" if prev_paper_trading == 1 else "실전투자"
                new_mode = "모의투자" if trading_mode == "paper" else "실전투자"

                cursor.execute("""
                    UPDATE broker_metadata
                    SET paper_trading = ?, updated_at = ?
                    WHERE product = ? AND provider = ?
                """, (paper_trading_int, datetime.now().isoformat(), self.product, self.provider))
                conn.commit()

                logger.info(f"[{identifier}] 거래 모드 전환: {prev_mode} → {new_mode} (데이터 보존)")

    def record_order(
        self,
        order_no: str,
        order_date: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        price: float,
        job_id: str,
        node_id: str,
    ) -> None:
        """
        워크플로우 주문 기록
        
        주문 API 응답 후 호출하여 주문번호를 기록합니다.
        나중에 체결 시 이 정보로 워크플로우 주문 여부를 판단합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            symbol: 종목코드
            exchange: 거래소
            side: 매매구분 ("buy" | "sell")
            quantity: 수량
            price: 가격
            job_id: Job ID
            node_id: Node ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO workflow_orders
                (product, provider, order_no, order_date, symbol, exchange, side, quantity, price, job_id, node_id, trading_mode, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.product, self.provider,
                order_no, order_date, symbol, exchange, side, quantity, price,
                job_id, node_id, self.trading_mode, datetime.now().isoformat()
            ))
            conn.commit()
        
        # 버퍼에서 매칭되는 체결 확인 (이벤트 루프가 있는 경우에만)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._process_buffered_fill(order_no, order_date))
        except RuntimeError:
            # 동기 환경에서는 버퍼 처리 생략 (체결이 먼저 올 일 없음)
            pass
        
        logger.debug(f"Recorded workflow order: {order_no} ({symbol} {side} {quantity}@{price})")
    
    async def _process_buffered_fill(self, order_no: str, order_date: str) -> None:
        """Process all buffered partial fills after recording their order."""
        notifications: list = []
        async with self._buffer_lock:
            for key, fill in list(self._pending_fills.items()):
                if fill.order_date != order_date:
                    continue
                matches = fill.order_no == order_no
                if self._normalize_identifier(fill.execution_id) is not None:
                    matches = self._normalize_identifier(fill.order_no) == self._normalize_identifier(order_no)
                if matches:
                    await self._process_fill_internal(fill, "workflow", notifications)
                    self._pending_fills.pop(key)
        await self._emit_fill_notifications(notifications)
    
    async def record_fill(
        self,
        order_no: str,
        order_date: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        price: float,
        fill_time: str,
        commda_code: str,
        *,
        execution_id: Optional[str | int] = None,
        account_avg_price: Optional[float] = None,
    ) -> str:
        """
        체결 기록 및 FIFO 처리
        
        체결 이벤트 수신 시 호출합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            symbol: 종목코드
            exchange: 거래소
            side: 매매구분 ("buy" | "sell")
            quantity: 수량
            price: 체결가
            fill_time: 체결시각 (HHMMSSsss)
            commda_code: 매체구분코드 (40=OPEN API). 프레임에서 온 값을 그대로
                받는다 — 우리 주문과 일치하면 매체코드와 무관하게 workflow 로,
                일치하지 않는 fill 만 매체코드로 manual(HTS)/unknown_api 를 가른다.
            account_avg_price: Optional account average purchase price for this
                symbol at fill time. Only a workflow sell whose own lots run out
                uses it, to estimate the residual tail. None → no estimate.
            execution_id: Optional broker execution identity. Positive numeric
                strings/integers ignore padding; opaque strings retain case.
                None, blank, and zero mean no identity and retain legacy replay
                behavior. Numeric floats/negative IDs are rejected. Never derive
                this value from order IDs, timestamps, quantities, or prices.

        Explicit identity is scoped to this ledger, product, provider, mode,
        order date and normalized order number. Exact replay returns the first
        stored classification without mutating FIFO/history. Changed symbol,
        exchange, side, quantity, price, fill time or source code raises
        ExecutionIdentityConflictError. Callers must supply consistent broker
        timestamp/field semantics; no timestamp or currency inference occurs.
        This is a persistence prerequisite, not broker-history/TC3 integration.
            
        Returns:
            분류 결과: "workflow" | "manual" | "unknown_api" | "other" | "pending"
        """
        fill = PendingFill(
            order_no=order_no, order_date=order_date, symbol=symbol,
            exchange=exchange, side=side, quantity=quantity, price=price,
            fill_time=fill_time, commda_code=commda_code, received_at=datetime.now(),
            execution_id=execution_id, account_avg_price=account_avg_price,
        )
        identity = self._execution_key(fill)
        notifications: list = []
        result: Optional[str] = None
        async with self._buffer_lock:
            if identity is not None:
                for pending in self._pending_fills.values():
                    if self._execution_key(pending) == identity:
                        self._assert_same_execution(pending, fill)
                        return "pending"
                with sqlite3.connect(self.db_path) as conn:
                    previous = self._find_execution(conn.cursor(), fill)
                if previous is not None:
                    return previous

            # A fill that matches one of our recorded workflow orders is ours,
            # whatever communication-media code the broker stamped on it — the
            # recorded order is the authoritative ownership signal, so it is
            # checked first. (Now that the real media code is forwarded instead
            # of a hardcoded '40', our own OPEN-API fills may not carry '40'; the
            # old media-first ordering would then misfile them as manual.)
            if self._is_workflow_fill(fill):
                result = await self._process_fill_internal(fill, "workflow", notifications)
            else:
                # No matching order. Classify by the published media table
                # (MEDIA_CODES_* above) — never by "not 40":
                #   human (85 HTS / 22 iPhone / 23 Android / 00 branch) → "manual"
                #   other (96/LP/SK/SO or unlisted)                    → "other"
                #   api (40/41/43) or blank                            → buffer below
                channel = media_channel(commda_code)
                if channel == "human":
                    result = await self._process_fill_internal(fill, "manual", notifications)
                elif channel == "other":
                    # A code the table does not attribute — more of these exist than
                    # we have measured (only 40/51/85/03 are live-observed so far).
                    # Log it so the table can grow from evidence, never from guesses.
                    logger.info("Unlisted media code %r on fill %s/%s — classified other",
                                commda_code, order_date, order_no)
                    result = await self._process_fill_internal(fill, "other", notifications)
                else:
                    # An API code or an empty media code ("medium unknown"): buffer to
                    # give a lagging order record a chance to arrive, then
                    # _process_timeout_fill files it as workflow (matched) or unknown_api
                    # (unmatched). An unknown medium is never asserted to be a person's
                    # HTS trade, so it floors to unknown_api rather than manual.
                    self._next_pending_fill += 1
                    key = self._next_pending_fill
                    self._pending_fills[key] = fill
        # Emit any confirmed-fill notifications now that _buffer_lock is released.
        if result is not None:
            await self._emit_fill_notifications(notifications)
            return result
        asyncio.create_task(self._process_timeout_fill(key))
        logger.debug(f"Buffered fill (waiting for order): {key}")
        return "pending"

    async def _process_timeout_fill(self, key: int) -> None:
        """Expire one arrival, without consuming a later partial's timeout."""
        await asyncio.sleep(self.FILL_BUFFER_TIMEOUT)
        notifications: list = []
        async with self._buffer_lock:
            if key in self._pending_fills:
                fill = self._pending_fills[key]
                classification = "workflow" if self._is_workflow_fill(fill) else "unknown_api"
                if classification == "unknown_api":
                    logger.warning("Fill expired before its order was recorded; classifying as unknown_api")
                await self._process_fill_internal(fill, classification, notifications)
                self._pending_fills.pop(key)
        await self._emit_fill_notifications(notifications)

    @staticmethod
    def _normalize_identifier(value: Optional[str | int]) -> Optional[str]:
        """Normalize proven IDs only; never invent an ID for missing/zero data."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError("Execution/order identity must be a string or integer")
        text = str(value).strip()
        if not text:
            return None
        if re.fullmatch(r"[0-9]+", text):
            return text.lstrip("0") or None
        if re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", text):
            raise ValueError("Numeric execution/order identity must be a positive integer")
        return text

    def _execution_key(self, fill: PendingFill) -> Optional[Tuple[str, ...]]:
        execution_id = self._normalize_identifier(fill.execution_id)
        if execution_id is None:
            return None
        order_no = self._normalize_identifier(fill.order_no)
        if order_no is None or not fill.order_date:
            raise ValueError("Explicit execution identity requires an order number and date")
        return (self.product, self.provider, self.trading_mode, fill.order_date, order_no, execution_id)

    @staticmethod
    def _execution_facts(fill: PendingFill) -> Dict[str, Any]:
        # Decimal equality avoids false conflicts for quantity/price formatting,
        # while the first supplied values are retained in execution_payload.
        quantity, price = Decimal(str(fill.quantity)), Decimal(str(fill.price))
        if not quantity.is_finite() or not price.is_finite():
            raise ValueError("Explicit execution quantity and price must be finite")
        return {
            "symbol": fill.symbol, "exchange": fill.exchange, "side": fill.side,
            "quantity": quantity, "price": price, "fill_time": fill.fill_time,
            "commda_code": fill.commda_code,
        }

    def _assert_same_execution(self, previous: PendingFill, fill: PendingFill) -> None:
        if self._execution_facts(previous) != self._execution_facts(fill):
            raise ExecutionIdentityConflictError("Conflicting fill facts for an existing execution identity")

    def _find_execution(self, cursor: sqlite3.Cursor, fill: PendingFill) -> Optional[str]:
        identity = self._execution_key(fill)
        if identity is None:
            return None
        facts = self._execution_facts(fill)
        cursor.execute("""
            SELECT classification, execution_payload FROM trade_history
            WHERE product = ? AND provider = ? AND trading_mode = ?
              AND order_date = ? AND normalized_order_no = ? AND execution_id = ?
        """, identity)
        row = cursor.fetchone()
        if row is None:
            return None
        stored = json.loads(row[1])
        stored.pop("reported_execution_id")
        stored["quantity"] = Decimal(stored["quantity"])
        stored["price"] = Decimal(stored["price"])
        if stored != facts:
            raise ExecutionIdentityConflictError("Conflicting fill facts for an existing execution identity")
        return row[0]

    def _is_workflow_fill(self, fill: PendingFill) -> bool:
        identity = self._execution_key(fill)
        if identity is None:
            return self._check_workflow_order(fill.order_no, fill.order_date)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT order_no FROM workflow_orders
                WHERE product = ? AND provider = ? AND trading_mode = ? AND order_date = ?
            """, identity[:4])
            return any(self._normalize_identifier(row[0]) == identity[4] for row in rows)

    async def _process_fill_internal(
        self, fill: PendingFill, classification: str, notifications: list
    ) -> str:
        """Gate explicit replay before atomically mutating FIFO and history.

        A newly confirmed fill is *queued* into ``notifications`` (a caller-owned
        list) instead of being emitted here — the caller emits it via
        ``_emit_fill_notifications`` AFTER releasing ``_buffer_lock``. Emitting
        under the lock would await the listener chain (a network POST in the
        pg-worker forwarder, ``request_timeout`` seconds) while holding
        ``_buffer_lock``, serializing every other broker fill push behind it.
        Replays return early and queue nothing (no re-fire)."""
        fill_datetime = f"{fill.order_date}_{fill.fill_time}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            previous = self._find_execution(cursor, fill)
            if previous is not None:
                return previous
            identity = self._execution_key(fill)
            payload = None
            if identity is not None:
                facts = self._execution_facts(fill)
                payload = json.dumps({
                    **facts, "quantity": str(fill.quantity), "price": str(fill.price),
                    "reported_execution_id": fill.execution_id,
                }, sort_keys=True)
            realized_pnl = 0.0
            estimate = None

            if fill.side == "buy":
                # 매수: 새 로트 생성
                cursor.execute("""
                    INSERT INTO workflow_position_lots
                    (product, provider, symbol, exchange, fill_datetime, buy_price, original_qty, remaining_qty,
                     classification, order_no, order_date, trading_mode, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.product, self.provider,
                    fill.symbol, fill.exchange, fill_datetime, fill.price,
                    fill.quantity, fill.quantity, classification,
                    fill.order_no, fill.order_date, self.trading_mode, datetime.now().isoformat()
                ))
            else:
                # 매도: FIFO 청산 (현재 trading_mode 내에서만)
                realized_pnl, estimate = self._process_sell_fifo(
                    cursor, fill.symbol, fill.quantity, fill.price, classification,
                    account_avg_price=fill.account_avg_price,
                )

            # 체결 내역 저장
            cursor.execute("""
                INSERT INTO trade_history
                (product, provider, order_no, order_date, symbol, exchange, side, quantity, price,
                 fill_datetime, classification, commda_code, realized_pnl, trading_mode, created_at,
                 execution_id, normalized_order_no, execution_payload,
                 unmatched_qty, estimate_basis_price, estimate_source, estimated_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.product, self.provider,
                fill.order_no, fill.order_date, fill.symbol, fill.exchange,
                fill.side, fill.quantity, fill.price, fill_datetime,
                classification, fill.commda_code, realized_pnl, self.trading_mode, datetime.now().isoformat(),
                identity[5] if identity else None, identity[4] if identity else None, payload,
                estimate["unmatched_qty"] if estimate else None,
                estimate["estimate_basis_price"] if estimate else None,
                estimate["estimate_source"] if estimate else None,
                estimate["estimated_pnl"] if estimate else None,
            ))

            conn.commit()

        # 원장이 실제로 바뀌었다 — 이 값을 캐시 키에 실은 소비자는 다음 읽기에서
        # 반드시 다시 계산한다.
        self.fill_revision += 1

        logger.debug(f"Processed fill: {fill.symbol} {fill.side} {fill.quantity}@{fill.price} [{classification}] ({self.trading_mode})")

        # 새 체결이 원장에 확정됐다 → on_order_fill 통지를 큐잉한다(1회 발화).
        # 실제 emit 은 caller 가 _buffer_lock 을 놓은 뒤 _emit_fill_notifications
        # 로 수행한다(락 안에서 리스너 network POST 를 await 하지 않기 위함).
        # 리플레이는 위에서 previous 반환으로 이미 걸러졌으므로 여기 오지 않는다.
        if self._on_fill_classified is not None:
            notifications.append((fill, classification))

        return classification

    async def _emit_fill_notifications(self, notifications: list) -> None:
        """Emit queued on_order_fill notifications OUTSIDE ``_buffer_lock``.

        Each caller collects confirmed fills into its own list under the lock
        (via ``_process_fill_internal``) and drains them here once the lock is
        released, so a slow listener never blocks other broker fill pushes.
        """
        if self._on_fill_classified is None:
            return
        for fill, classification in notifications:
            try:
                await self._on_fill_classified(fill, classification)
            except Exception as cb_err:
                logger.warning(f"Fill-classified callback error: {cb_err}")

    def _process_sell_fifo(
        self,
        cursor: sqlite3.Cursor,
        symbol: str,
        quantity: int,
        sell_price: float,
        classification: str,
        account_avg_price: Optional[float] = None,
    ) -> Tuple[float, Optional[Dict[str, Any]]]:
        """
        FIFO 매도 처리

        fill_datetime 순으로 정렬하여 선입선출 방식으로 청산합니다.

        classification 이 'workflow' 인 매도는 **workflow 로트만** 소진한다. 수동/타
        API 로트를 먹으면 이 전략이 열지 않은 포지션의 손익까지 실현한 셈이 되기
        때문이다. workflow 로트가 바닥난 뒤 남는 수량(remaining)은 이 전략이 여기서
        사지 않은 물량을 판 것이므로, 계좌 평균매입가(account_avg_price)가 주어지면
        그 잔량을 추정손익으로 매도 행에 기록한다(realized_pnl 은 FIFO 매칭분만 유지).
        non-workflow 매도는 종전과 동일하게 분류 무관 로트를 FIFO 소진한다.

        Args:
            cursor: DB 커서
            symbol: 종목코드
            quantity: 매도 수량
            sell_price: 매도가
            classification: 분류 ("workflow" 면 workflow 로트만 소진)
            account_avg_price: 계좌 평균매입가 (workflow 매도의 잔량 추정용, 없으면 추정 없음)

        Returns:
            (실현 손익 FIFO 매칭분, 추정 정보 dict 또는 None)
        """
        remaining_to_sell = quantity
        total_realized_pnl = 0.0

        # fill_datetime 순으로 정렬 (FIFO, 현재 trading_mode 내에서만).
        # workflow 매도는 workflow 로트로 소진 대상을 좁힌다.
        if classification == "workflow":
            cursor.execute("""
                SELECT id, buy_price, remaining_qty, classification
                FROM workflow_position_lots
                WHERE symbol = ? AND remaining_qty > 0 AND trading_mode = ?
                  AND classification = 'workflow'
                ORDER BY fill_datetime ASC
            """, (symbol, self.trading_mode))
        else:
            cursor.execute("""
                SELECT id, buy_price, remaining_qty, classification
                FROM workflow_position_lots
                WHERE symbol = ? AND remaining_qty > 0 AND trading_mode = ?
                ORDER BY fill_datetime ASC
            """, (symbol, self.trading_mode))

        lots = cursor.fetchall()

        for lot_id, buy_price, remaining_qty, lot_classification in lots:
            if remaining_to_sell <= 0:
                break

            sell_qty = min(remaining_to_sell, remaining_qty)
            new_remaining = remaining_qty - sell_qty

            # 로트 업데이트
            cursor.execute("""
                UPDATE workflow_position_lots
                SET remaining_qty = ?
                WHERE id = ?
            """, (new_remaining, lot_id))

            # 실현 손익 계산
            pnl = (sell_price - buy_price) * sell_qty
            total_realized_pnl += pnl

            remaining_to_sell -= sell_qty

            logger.debug(f"FIFO sell: lot {lot_id} ({lot_classification}), "
                        f"qty={sell_qty}, pnl={pnl:.2f}")

        estimate: Optional[Dict[str, Any]] = None
        if remaining_to_sell > 0:
            if (classification == "workflow" and account_avg_price is not None
                    and account_avg_price > 0):
                # 이 전략이 여기서 사지 않은 잔량 — 같은 종목을 계좌의 다른 경로로
                # 사둔 것으로 보고 계좌 평균매입가 기준 추정손익을 기록한다.
                # realized_pnl(FIFO 매칭분)에는 넣지 않고 별도 컬럼으로만 남긴다.
                estimated_pnl = (sell_price - account_avg_price) * remaining_to_sell
                estimate = {
                    "unmatched_qty": float(remaining_to_sell),
                    "estimate_basis_price": float(account_avg_price),
                    "estimate_source": "account_balance_avg_price",
                    "estimated_pnl": float(estimated_pnl),
                }
                logger.debug(f"Estimated sell tail: {symbol} qty={remaining_to_sell} "
                             f"@avg={account_avg_price} est_pnl={estimated_pnl:.2f}")
            else:
                logger.warning(f"Sell without enough position: {symbol} remaining={remaining_to_sell}")

        return total_realized_pnl, estimate
    
    def _check_workflow_order(self, order_no: str, order_date: str) -> bool:
        """워크플로우 주문 여부 확인 (현재 trading_mode 기준)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM workflow_orders
                WHERE order_no = ? AND order_date = ? AND trading_mode = ?
            """, (order_no, order_date, self.trading_mode))
            return cursor.fetchone() is not None
    
    def get_workflow_positions(
        self,
        start_date: Optional[str] = None,
    ) -> Dict[str, PositionInfo]:
        """
        현재 워크플로우 포지션 조회 (start_date 필터 지원)
        
        Args:
            start_date: 필터 시작일 (YYYYMMDD), None이면 전체 기간
        
        Returns:
            종목별 워크플로우 포지션 {symbol: PositionInfo}
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 날짜 필터 조건
            date_filter = ""
            params: list = [self.trading_mode]
            if start_date:
                # fill_datetime 형식: YYYYMMDD_HHMMSSsss
                date_filter = " AND fill_datetime >= ?"
                params.append(f"{start_date}_000000000")

            cursor.execute(f"""
                SELECT symbol, exchange, buy_price, remaining_qty, classification
                FROM workflow_position_lots
                WHERE remaining_qty > 0 AND classification = 'workflow' AND trading_mode = ?
                {date_filter}
            """, params)
            
            positions: Dict[str, PositionInfo] = {}
            
            for symbol, exchange, buy_price, remaining_qty, classification in cursor.fetchall():
                # SQLite 가 소수점 체결 lot 을 REAL 로 돌려줄 수 있어 Decimal 로
                # 통일한다 (Decimal * float 는 TypeError).
                lot_qty = Decimal(str(remaining_qty))
                if symbol in positions:
                    # 같은 종목: 평균단가 재계산
                    pos = positions[symbol]
                    total_qty = pos.quantity + lot_qty
                    total_cost = (pos.avg_price * pos.quantity) + (Decimal(str(buy_price)) * lot_qty)
                    pos.quantity = total_qty
                    pos.avg_price = total_cost / total_qty
                else:
                    positions[symbol] = PositionInfo(
                        symbol=symbol,
                        exchange=exchange or "",
                        quantity=lot_qty,
                        avg_price=Decimal(str(buy_price)),
                        classification=classification,
                    )
            
            return positions
    
    def get_other_positions(
        self,
        all_positions: Dict[str, Any],
    ) -> Dict[str, PositionInfo]:
        """
        워크플로우 제외 포지션 조회
        
        Args:
            all_positions: 전체 보유 포지션 (브로커 API에서 조회)
            
        Returns:
            워크플로우 제외 포지션 {symbol: PositionInfo}
        """
        workflow_positions = self.get_workflow_positions()
        other_positions: Dict[str, PositionInfo] = {}
        
        for symbol, pos_data in all_positions.items():
            total_qty = Decimal(str(pos_data.get("quantity", 0) or pos_data.get("qty", 0) or 0))
            avg_price = pos_data.get("avg_price", 0) or pos_data.get("buy_price", 0)
            exchange = pos_data.get("exchange", "")

            workflow_qty = workflow_positions.get(symbol, PositionInfo(symbol, "", Decimal(0), Decimal(0), "")).quantity
            other_qty = total_qty - workflow_qty
            
            if other_qty > 0:
                other_positions[symbol] = PositionInfo(
                    symbol=symbol,
                    exchange=exchange,
                    quantity=other_qty,
                    avg_price=Decimal(str(avg_price)),
                    classification="other",
                )
        
        return other_positions
    
    def _infer_multipliers(
        self,
        all_positions: Dict[str, Any],
        prices: Dict[str, Decimal],
    ) -> Dict[str, Tuple[Decimal, Decimal]]:
        """브로커 스냅샷에서 심볼별 ``(계약 승수, 방향 부호)`` 를 역산한다.

        선물 평가손익은 ``mult × side_sign × qty × (현재가 − 평단)`` 이므로
        (side_sign: long=+1, short=−1), 브로커가 실은 승수 반영 ``pnl_amount`` 에서:

            mult = pnl_amount / ((current − avg) × qty × side_sign)

        - side_sign 은 스냅샷 방향 라벨(``direction`` 또는 ``side``)에서 항상 얻는다
          (역산 성공 여부와 무관). 호출부는 이 부호로 FIFO 롱-only 산식의 pnl 부호를
          보정한다 → 숏도 올바른 부호.
        - mult(양수 크기)는 아래 가드를 모두 통과할 때만 채택하고, 실패 시 심볼별
          최근 성공값 캐시(없으면 1.0)로 폴백한다:
            · pnl_amount 없/0(placeholder) → 역산 생략
            · |현재가−평단|/평단 < _MULT_MIN_REL_GAP → 분모가 작아 불안정 → 생략
            · mult 이 [_MULT_MIN, _MULT_MAX] 밖 → 거부 (라벨 오류로 부호가 뒤집혀
              음수가 나오는 경우도 여기서 거부됨)
            · 최근접 정수와 상대오차 ≤ _MULT_INT_SNAP_REL → 정수로 스냅
        주식(승수 1)은 자연히 1.0 으로 역산된다.
        """
        result: Dict[str, Tuple[Decimal, Decimal]] = {}
        for symbol, pos_data in (all_positions or {}).items():
            if not isinstance(pos_data, dict):
                continue

            # 방향 부호는 라벨에서 항상 결정 (역산 실패해도 유지)
            direction = str(
                pos_data.get("direction") or pos_data.get("side") or "long"
            ).lower()
            side_sign = Decimal(-1) if direction.startswith("short") else Decimal(1)

            mult: Optional[Decimal] = None
            pnl_raw = pos_data.get("pnl_amount")
            # 명시적 0.0 은 여러 빌더가 넣는 placeholder 이므로 역산에서 제외.
            if pnl_raw:
                try:
                    pnl_amount = Decimal(str(pnl_raw))
                    qty = pos_data.get("quantity", 0) or pos_data.get("qty", 0)
                    avg_raw = pos_data.get("avg_price", 0) or pos_data.get("buy_price", 0)
                    cur = prices.get(symbol)
                    if cur is None:
                        cur_raw = pos_data.get("current_price")
                        cur = Decimal(str(cur_raw)) if cur_raw is not None else None
                    if cur is not None and qty:
                        avg_d = Decimal(str(avg_raw))
                        qty_d = Decimal(str(qty))
                        cur_d = cur if isinstance(cur, Decimal) else Decimal(str(cur))
                        if avg_d > 0:
                            rel_gap = abs(cur_d - avg_d) / avg_d
                            if rel_gap >= _MULT_MIN_REL_GAP:
                                denom = (cur_d - avg_d) * qty_d * side_sign
                                if denom != 0:
                                    cand = pnl_amount / denom
                                    if _MULT_MIN <= cand <= _MULT_MAX:
                                        # 정수 근사 스냅 (선물 승수는 정수 관행)
                                        nearest = cand.to_integral_value(rounding=ROUND_HALF_UP)
                                        if nearest >= 1 and abs(cand - nearest) / nearest <= _MULT_INT_SNAP_REL:
                                            cand = Decimal(nearest)
                                        mult = cand
                                        self._multiplier_cache[symbol] = cand
                except (TypeError, ValueError, ArithmeticError):
                    pass  # 역산 실패 → 캐시/기본 폴백

            if mult is None:
                mult = self._multiplier_cache.get(symbol, Decimal(1))
            result[symbol] = (mult, side_sign)
        return result

    def calculate_pnl(
        self,
        current_prices: Dict[str, Any],  # Decimal 또는 float
        all_positions: Dict[str, Any],
        currency: str = "USD",
        start_date: Optional[str] = None,  # YYYYMMDD 필터
    ) -> Dict[str, Any]:
        """
        실시간 평가 수익률 계산

        Args:
            current_prices: 현재가 {symbol: price} (Decimal 또는 float)
            all_positions: 전체 보유 포지션
            currency: 통화
            start_date: 필터 시작일 (YYYYMMDD), None이면 전체 기간

        Returns:
            WorkflowPnLEvent 생성에 필요한 데이터 dict
        """
        from programgarden_core.bases import PositionDetail

        # float를 Decimal로 변환
        prices = {
            symbol: Decimal(str(price)) if not isinstance(price, Decimal) else price
            for symbol, price in current_prices.items()
        }

        # 브로커 스냅샷에서 심볼별 계약 승수 역산. FIFO lot 산술은 승수를 모르므로
        # (eval/buy/pnl 금액이 선물에서 1/N 로 축소) 여기서 얻은 승수로 스케일한다.
        # pnl_rate 는 eval/buy 비율이라 승수가 소거돼 영향 없음.
        multipliers = self._infer_multipliers(all_positions, prices)

        workflow_positions = self.get_workflow_positions(start_date=start_date)
        other_positions = self.get_other_positions(all_positions)

        # 워크플로우 포지션 계산.
        # eval/buy 는 양수 명목가(승수 스케일)로 유지하고, pnl 은 side_sign 으로
        # 부호를 보정해 별도 누적한다(FIFO 는 롱-only 산식이라 숏이면 eval−buy 의
        # 부호가 뒤집혀 있음). 롱은 side_sign=+1 이라 기존과 동일.
        wf_eval = Decimal(0)
        wf_buy = Decimal(0)
        wf_pnl = Decimal(0)
        wf_details: List[PositionDetail] = []
        # 증거 카운터 — 비율을 **발행해도 되는지** 를 결정한다(금액은 영향 없음).
        wf_unpriced = 0   # 현재가를 관측하지 못해 평단으로 대체한 종목 수
        wf_unbased = 0    # 평단이 0 이하라 매수근거가 없는 종목 수

        for symbol, pos in workflow_positions.items():
            observed_price = prices.get(symbol)
            if observed_price is None or observed_price <= 0:
                wf_unpriced += 1
            if pos.avg_price <= 0:
                wf_unbased += 1
            # 🔴 금액 계산은 **현행 그대로** 둔다(평단 폴백 포함) — 금액을 비우면 모니터링
            # KPI 합산이 통째로 접히고, 전량 청산한 날의 0 은 진짜 0 이다.
            # 달라지는 것은 "그 금액으로 비율을 발행할 자격이 있는가" 뿐이다.
            current_price = observed_price if (observed_price and observed_price > 0) else pos.avg_price
            mult, side_sign = multipliers.get(symbol, (Decimal(1), Decimal(1)))
            eval_amount = current_price * pos.quantity * mult
            buy_amount = pos.avg_price * pos.quantity * mult
            pnl_amount = (eval_amount - buy_amount) * side_sign
            pnl_rate = (pnl_amount / buy_amount * 100) if buy_amount else Decimal(0)

            wf_eval += eval_amount
            wf_buy += buy_amount
            wf_pnl += pnl_amount

            wf_details.append(PositionDetail(
                symbol=symbol,
                exchange=pos.exchange,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                current_price=current_price,
                pnl_amount=pnl_amount,
                pnl_rate=pnl_rate,
            ))

        # 🔴 계산할 수 없으면 0 이 아니라 **아무것도 발행하지 않는다**(None).
        #
        # 종전 `else Decimal(0)` 는 "아무것도 안 샀다" 를 **"0% 로 측정됐다"** 로 바꿔 발행했다.
        # 그러면 워크플로우를 시작만 해도 스냅샷이 생겨 공유 카드가 「참고 데이터」 배지 달린
        # 정직한 0.0% 에서 **배지 없는 "실측 0.0%"** 로 바뀐다(승률 0%·손익비 0.00 까지).
        # 선물은 이미 이 원칙으로 고쳐져 있다(`futures_pnl.unavailable_workflow_pnl`) —
        # 주식만 안 따라갔다.
        #
        # 한 종목이라도 현재가를 못 봤거나(`wf_unpriced`) 평단이 없으면(`wf_unbased`)
        # 합계 비율이 **부풀려진다**(분모만 줄거나 평가액이 매수액으로 눌린다). 그건 0 이
        # 아닌 채로 틀리므로 값 자체를 내지 않는다.
        wf_rate_reason: Optional[str] = None
        if not workflow_positions:
            wf_rate_reason = "no_workflow_positions"
        elif wf_unbased:
            wf_rate_reason = "basis_unreported"
        elif wf_unpriced:
            wf_rate_reason = "price_unreported"
        elif not wf_buy:
            wf_rate_reason = "no_workflow_positions"
        wf_rate = None if wf_rate_reason else (wf_pnl / wf_buy * 100)

        # 그 외 포지션 계산
        other_eval = Decimal(0)
        other_buy = Decimal(0)
        other_pnl = Decimal(0)
        other_details: List[PositionDetail] = []
        other_unpriced = 0
        other_unbased = 0

        for symbol, pos in other_positions.items():
            observed_price = prices.get(symbol)
            if observed_price is None or observed_price <= 0:
                other_unpriced += 1
            if pos.avg_price <= 0:
                other_unbased += 1
            current_price = observed_price if (observed_price and observed_price > 0) else pos.avg_price
            mult, side_sign = multipliers.get(symbol, (Decimal(1), Decimal(1)))
            eval_amount = current_price * pos.quantity * mult
            buy_amount = pos.avg_price * pos.quantity * mult
            pnl_amount = (eval_amount - buy_amount) * side_sign
            pnl_rate = (pnl_amount / buy_amount * 100) if buy_amount else Decimal(0)

            other_eval += eval_amount
            other_buy += buy_amount
            other_pnl += pnl_amount

            other_details.append(PositionDetail(
                symbol=symbol,
                exchange=pos.exchange,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                current_price=current_price,
                pnl_amount=pnl_amount,
                pnl_rate=pnl_rate,
            ))

        # wf_rate 와 같은 규율 — 근거가 없으면 비율을 발행하지 않는다.
        other_rate = (
            None
            if (not other_positions or other_unbased or other_unpriced or not other_buy)
            else (other_pnl / other_buy * 100)
        )

        # 전체 계산 — pnl 은 부호 보정된 per-position 합, eval/buy 는 명목가 합.
        total_eval = wf_eval + other_eval
        total_buy = wf_buy + other_buy
        total_pnl = wf_pnl + other_pnl
        # 전체 비율은 **양쪽 다 증거가 성립할 때만** 낸다. 한쪽이 모름이면 합계도 모름이다
        # (모르는 쪽을 0 으로 치고 더하면 없는 정확도를 만들어낸다).
        total_unpriced = wf_unpriced + other_unpriced
        total_unbased = wf_unbased + other_unbased
        total_rate = (
            None
            if (not total_buy or total_unbased or total_unpriced)
            else (total_pnl / total_buy * 100)
        )
        
        # 신뢰도 계산
        anomalies = self.detect_anomalies()
        trust_score = self.calculate_trust_score(anomalies)
        
        return {
            "job_id": self.job_id,
            "broker_node_id": self.broker_node_id,
            "product": self.product,
            
            "workflow_pnl_rate": wf_rate,
            # 비율을 못 낸 **이유**. 값을 비우는 것만으로는 "안 샀다" 와 "증권사가 평단을
            # 안 보냈다" 가 구분되지 않는다 — 서버는 이 사유를 raw_event 에 그대로 싣는다.
            # 어휘는 dsl-api `app/utils/pnl_rate_evidence.RATE_UNAVAILABLE_REASONS` 와 공용.
            "workflow_rate_unavailable_reason": wf_rate_reason,
            "workflow_eval_amount": wf_eval,
            "workflow_buy_amount": wf_buy,
            "workflow_pnl_amount": wf_pnl,
            
            "other_pnl_rate": other_rate,
            "other_eval_amount": other_eval,
            "other_buy_amount": other_buy,
            "other_pnl_amount": other_pnl,
            
            "total_pnl_rate": total_rate,
            "total_eval_amount": total_eval,
            "total_buy_amount": total_buy,
            "total_pnl_amount": total_pnl,
            
            "workflow_positions": wf_details,
            "other_positions": other_details,
            
            "trust_score": trust_score,
            "anomaly_count": len(anomalies),
            
            "currency": currency,
            "timestamp": datetime.now(),
        }

    def personal_metrics(self) -> Dict[str, Any]:
        """Read retained workflow executions without claiming account performance.

        Historical FIFO rows have no currency or fee evidence. Keep their amounts
        per symbol/exchange and reject mixed ownership or an incomplete FIFO basis.
        Futures FIFO is not a monetary ledger. No equity/MDD basis is inferred.

        Version 2 adds closed-trade outcomes. One closed trade = one sell fill,
        using its *stored* realized amount — the replay below only validates the
        basis and never replaces a stored value, so the outcome is read from the
        same number the ledger committed.

        A workflow sell now consumes only workflow lots (_process_sell_fifo), so
        the old ``mixed_fifo_ownership`` pre-check is gone: a workflow sell can
        no longer have realized a non-workflow lot, so there is nothing to guard
        against. Old ledger rows written under the previous (classification-blind)
        sell replay with ``stored != expected`` and are rejected below as
        ``incomplete_fifo_basis`` — the honest outcome for a basis we can no
        longer reconstruct.

        A workflow sell whose own lots run out leaves a residual. When that
        residual was recorded with an account-average-price estimate covering
        exactly it (``estimate_basis_price`` present and ``unmatched_qty`` equal
        to the residual), the group is not rejected: its status becomes
        ``estimated``, its basis ``fifo_with_account_avg_price_estimate``, and
        the sell scores on ``stored + estimated_pnl`` (the FIFO-matched amount
        plus the estimated tail). Any other residual is an incomplete basis.

        Counts aggregate across symbols because a count carries no currency.
        Amounts do not: with `currency` unproven per row, summing gross profit
        across symbols would invent the very unit this method refuses to claim.
        So gross amounts stay inside each group, and the top-level profit/loss
        ratio is published only when a single group carries the whole ledger —
        the one case where "the currency is the same" needs no evidence.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = [dict(row) for row in conn.execute(
                "SELECT * FROM trade_history WHERE trading_mode=? ORDER BY id",
                (self.trading_mode,),
            )]
        selected = [row for row in rows if row["product"] == self.product
                    and row["provider"] == self.provider and row["classification"] == "workflow"]
        keys = set()
        invalid_count = False
        groups: Dict[Tuple[str, str], List[dict]] = {}
        for row in selected:
            try:
                quantity = Decimal(str(row["quantity"]))
                if not quantity.is_finite() or quantity < 0:
                    raise ValueError("Invalid execution quantity")
                if quantity == 0:
                    continue
                order_date = row["order_date"]
                if not isinstance(order_date, str) or not re.fullmatch(r"[0-9]{8}", order_date):
                    raise ValueError("Missing order date")
                datetime.strptime(order_date, "%Y%m%d")
                order_no = self._normalize_identifier(row["order_no"])
                if order_no is None:
                    raise ValueError("Missing order number")
                keys.add((order_date, order_no))
            except (ValueError, TypeError, ArithmeticError):
                invalid_count = True
            key = (row["symbol"] or "", row["exchange"] or "")
            groups.setdefault(key, []).append(row)

        realized = []
        for (symbol, exchange), fills in sorted(groups.items()):
            reason = None
            amount = None
            outcome = None
            # Whether this group's amount includes an account-avg-price estimate,
            # and how much quantity was estimated (Σ unmatched over its sells).
            group_estimated = False
            group_est_qty = Decimal(0)
            if self.product == "overseas_futures":
                reason = "futures_fifo_not_monetary"
            elif not symbol:
                reason = "missing_symbol"
            else:
                # The old mixed_fifo_ownership pre-check is gone: a workflow sell
                # now consumes only workflow lots, so it can never have realized a
                # non-workflow lot. Old rows written under the previous replay
                # fall out below as incomplete_fifo_basis (stored != expected).
                try:
                    lots = []
                    total = Decimal(0)
                    # NB: `closed` below is the matched lot quantity — do not
                    # reuse that name for a counter.
                    trades = wins = losses = evens = 0
                    gross_profit = Decimal(0)
                    gross_loss = Decimal(0)
                    for fill in fills:
                        quantity = Decimal(str(fill["quantity"]))
                        price = Decimal(str(fill["price"]))
                        stored = Decimal(str(fill["realized_pnl"]))
                        if not all(value.is_finite() for value in (quantity, price, stored)) or quantity <= 0:
                            raise ValueError("Invalid stored fill")
                        if fill["side"] == "buy":
                            if stored != 0:
                                raise ValueError("Unexpected opening PnL")
                            lots.append([fill["fill_datetime"] or "", fill["id"], quantity, price])
                            lots.sort(key=lambda lot: (lot[0], lot[1]))
                        elif fill["side"] == "sell":
                            remaining = quantity
                            expected = Decimal(0)
                            for lot in lots:
                                closed = min(remaining, lot[2])
                                expected += (price - lot[3]) * closed
                                lot[2] -= closed
                                remaining -= closed
                                if remaining == 0:
                                    break
                            tolerance = max(Decimal("0.000001"), abs(expected) * Decimal("0.000000001"))
                            # The FIFO-matched portion must reproduce the stored
                            # amount, whether or not a tail remains.
                            if abs(stored - expected) > tolerance:
                                raise ValueError("Inconsistent FIFO basis")
                            # trade_amount is what this one closed trade scores on;
                            # it starts as the stored (matched) value and grows by
                            # the recorded estimate when a tail remains.
                            trade_amount = stored
                            if remaining > 0:
                                # A residual after the workflow lots run out is
                                # accepted only as a recorded account-avg-price
                                # estimate covering exactly this residual; anything
                                # else is an incomplete basis.
                                est_basis = fill["estimate_basis_price"]
                                est_unmatched = fill["unmatched_qty"]
                                est_pnl = fill["estimated_pnl"]
                                if est_basis is None or est_unmatched is None or est_pnl is None:
                                    raise ValueError("Incomplete FIFO basis without estimate")
                                est_unmatched_d = Decimal(str(est_unmatched))
                                est_pnl_d = Decimal(str(est_pnl))
                                if est_unmatched_d != remaining or not est_pnl_d.is_finite():
                                    raise ValueError("Estimate does not cover the residual")
                                # Add (never replace) the stored estimate to the
                                # matched amount; one sell fill is still one trade.
                                trade_amount = stored + est_pnl_d
                                group_estimated = True
                                group_est_qty += remaining
                            total += trade_amount
                            trades += 1
                            if trade_amount > 0:
                                wins += 1
                                gross_profit += trade_amount
                            elif trade_amount < 0:
                                losses += 1
                                gross_loss += -trade_amount
                            else:
                                evens += 1
                        else:
                            raise ValueError("Unknown fill side")
                    amount = float(total)
                    if not Decimal(str(amount)).is_finite():
                        raise ValueError("Non-finite total")
                    gross_profit_f = float(gross_profit)
                    gross_loss_f = float(gross_loss)
                    if not all(Decimal(str(v)).is_finite() for v in (gross_profit_f, gross_loss_f)):
                        raise ValueError("Non-finite gross amount")
                    outcome = {"closed_trades": trades, "winning_trades": wins,
                               "losing_trades": losses, "breakeven_trades": evens,
                               "gross_profit": gross_profit_f, "gross_loss": gross_loss_f}
                except (ValueError, TypeError, ArithmeticError, OverflowError):
                    reason = "incomplete_fifo_basis"
                    outcome = None
                    group_estimated = False
                    group_est_qty = Decimal(0)
            if reason is not None:
                status = "unavailable"
                basis = None
                estimated_quantity = None
            elif group_estimated:
                status = "estimated"
                basis = "fifo_with_account_avg_price_estimate"
                estimated_quantity = float(group_est_qty)
            else:
                status = "available"
                basis = "fifo"
                estimated_quantity = 0
            entry = {"symbol": symbol, "exchange": exchange, "currency": None,
                     "amount": amount, "status": status, "reason": reason,
                     "basis": basis, "estimated_quantity": estimated_quantity}
            # A rejected group publishes no outcome: its trades are unknown, and
            # unknown trades must not be counted as zero of anything.
            entry.update(outcome or {"closed_trades": None, "winning_trades": None,
                                     "losing_trades": None, "breakeven_trades": None,
                                     "gross_profit": None, "gross_loss": None})
            realized.append(entry)
        # Counts carry no currency, so they aggregate across symbols. A group the
        # replay rejected is excluded and downgrades the status to "partial" —
        # "some of this strategy's trades are not in these numbers" is a different
        # claim from "these are all of them", and the caller must be able to tell.
        scored = [g for g in realized if g["closed_trades"] is not None]
        counted = [g for g in scored if g["closed_trades"] > 0]
        if not scored:
            trade_status, trade_reason = "unavailable", (
                "futures_fifo_not_monetary" if self.product == "overseas_futures"
                else "no_scorable_fifo_basis")
            closed_total = winning_total = losing_total = breakeven_total = None
        else:
            trade_status = "available" if len(scored) == len(realized) else "partial"
            trade_reason = None if trade_status == "available" else "some_groups_unscorable"
            closed_total = sum(g["closed_trades"] for g in scored)
            winning_total = sum(g["winning_trades"] for g in scored)
            losing_total = sum(g["losing_trades"] for g in scored)
            breakeven_total = sum(g["breakeven_trades"] for g in scored)

        # The ratio is money, and money needs a unit. One group means one symbol,
        # hence one currency — the only case where the unit is provable without
        # currency evidence. Anything else stays per group.
        ratio = None
        ratio_status = "unavailable"
        if len(counted) != 1:
            ratio_reason = ("no_closed_trades" if not counted
                            else "multi_symbol_currency_unknown")
        else:
            group = counted[0]
            if group["gross_loss"] > 0:
                candidate = group["gross_profit"] / group["gross_loss"]
                if Decimal(str(candidate)).is_finite():
                    ratio, ratio_status, ratio_reason = candidate, "available", None
                else:
                    ratio_reason = "non_finite_ratio"
            else:
                # No losing trade means no denominator. Publishing gross profit
                # here (the server's day-based metric does) reads as a ratio of
                # that size and overstates the strategy.
                ratio_reason = "no_losing_trades"

        # How many groups carry an account-avg-price estimate, and whether the
        # aggregated figures rest on any estimate. A count is null when it is
        # itself unavailable; otherwise it is "measured" unless a scored group
        # was estimated. The ratio comes from a single group, so its basis is
        # that one group's.
        estimated_group_count = sum(1 for g in realized if g["status"] == "estimated")
        if trade_status == "unavailable":
            closed_trade_basis = None
        else:
            closed_trade_basis = ("includes_estimates"
                                  if any(g["status"] == "estimated" for g in scored)
                                  else "measured")
        if ratio_status != "available":
            profit_loss_ratio_basis = None
        else:
            profit_loss_ratio_basis = ("includes_estimates"
                                       if counted[0]["status"] == "estimated"
                                       else "measured")

        # Fills on this same account placed outside this strategy, by classification:
        # manual (a person via HTS/app/branch) → hts, unknown_api (another API
        # client) → other_api, other (broker-side codes 96/LP/SK/SO or unlisted)
        # → other. Futures fill frames carry no communication-media field, so
        # the channels cannot be told apart for them — unavailable.
        if self.product == "overseas_futures":
            off_strategy_fills = {"hts": None, "other_api": None, "other": None, "other_codes": None,
                                  "status": "unavailable",
                                  "reason": "futures_fills_have_no_media_code"}
        else:
            in_scope = [r for r in rows if r["product"] == self.product
                        and r["provider"] == self.provider]
            off_strategy_fills = {
                "hts": sum(1 for r in in_scope if r["classification"] == "manual"),
                "other_api": sum(1 for r in in_scope if r["classification"] == "unknown_api"),
                "other": sum(1 for r in in_scope if r["classification"] == "other"),
                # Distinct unlisted codes behind "other" — the evidence trail for
                # extending MEDIA_CODES_* (consumers may ignore this key).
                "other_codes": sorted({str(r["commda_code"]) for r in in_scope
                                       if r["classification"] == "other" and r["commda_code"]}),
                "status": "available", "reason": None,
            }

        return {
            "version": 2,
            "scope": {"kind": "local_workflow_ledger", "product": self.product,
                      "provider": self.provider, "trading_mode": self.trading_mode},
            "as_of": datetime.now(timezone.utc).isoformat(),
            "basis": "stored_fifo_gross_excluding_fees",
            "executed_order_count": None if invalid_count else len(keys),
            "executed_order_count_status": "unavailable" if invalid_count else "available",
            "executed_order_count_reason": "invalid_execution_identity" if invalid_count else None,
            "realized_pnl": realized,
            "closed_trade_count": closed_total,
            "winning_trade_count": winning_total,
            "losing_trade_count": losing_total,
            "breakeven_trade_count": breakeven_total,
            "closed_trade_status": trade_status,
            "closed_trade_reason": trade_reason,
            "closed_trade_basis": closed_trade_basis,
            "estimated_group_count": estimated_group_count,
            "profit_loss_ratio": ratio,
            "profit_loss_ratio_status": ratio_status,
            "profit_loss_ratio_reason": ratio_reason,
            "profit_loss_ratio_basis": profit_loss_ratio_basis,
            "off_strategy_fills": off_strategy_fills,
            "max_drawdown": None,
            "max_drawdown_status": "unavailable",
            "max_drawdown_reason": "equity_history_unavailable",
        }
    
    def detect_anomalies(self) -> List[AnomalyResult]:
        """
        이상 거래 감지
        
        Returns:
            감지된 이상 거래 목록
        """
        anomalies: List[AnomalyResult] = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. sell_without_buy: 워크플로우 매수 없이 매도한 경우
            cursor.execute("""
                SELECT symbol, SUM(CASE WHEN side = 'buy' THEN quantity ELSE 0 END) as buy_qty,
                       SUM(CASE WHEN side = 'sell' THEN quantity ELSE 0 END) as sell_qty
                FROM trade_history
                WHERE classification = 'workflow' AND trading_mode = ?
                GROUP BY symbol
                HAVING sell_qty > buy_qty
            """, (self.trading_mode,))
            
            for symbol, buy_qty, sell_qty in cursor.fetchall():
                anomalies.append(AnomalyResult(
                    pattern="sell_without_buy",
                    symbol=symbol,
                    description=f"Sell qty ({sell_qty}) exceeds buy qty ({buy_qty})",
                    severity=10,
                ))
            
            # 2. unknown_api_ratio: 알 수 없는 API 주문 비율
            cursor.execute("""
                SELECT
                    SUM(CASE WHEN classification = 'unknown_api' THEN 1 ELSE 0 END) as unknown_count,
                    COUNT(*) as total_count
                FROM trade_history
                WHERE commda_code = '40' AND trading_mode = ?
            """, (self.trading_mode,))
            
            row = cursor.fetchone()
            if row and row[1] > 0:
                unknown_count, total_count = row
                ratio = unknown_count / total_count
                if ratio > 0.1:  # 10% 이상이면 이상
                    severity = min(int(ratio * 100), 20)  # 최대 20점 감점
                    anomalies.append(AnomalyResult(
                        pattern="unknown_api_ratio",
                        symbol="*",
                        description=f"Unknown API orders: {unknown_count}/{total_count} ({ratio*100:.1f}%)",
                        severity=severity,
                    ))
        
        return anomalies
    
    def calculate_trust_score(self, anomalies: Optional[List[AnomalyResult]] = None) -> int:
        """
        신뢰도 점수 계산

        워크플로우 거래가 없으면 0 (신뢰도 산정 불가),
        거래가 있으면 100에서 이상 거래 감지 시 감점.

        Args:
            anomalies: 이상 거래 목록 (없으면 자동 감지)

        Returns:
            신뢰도 점수 (0-100)
        """
        # 워크플로우 거래가 없으면 신뢰도 0
        if not self._has_workflow_orders():
            return 0

        if anomalies is None:
            anomalies = self.detect_anomalies()

        score = 100
        for anomaly in anomalies:
            score -= anomaly.severity

        return max(0, score)

    def _has_workflow_orders(self) -> bool:
        """워크플로우 주문이 존재하는지 확인 (현재 trading_mode 기준)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM workflow_orders WHERE trading_mode = ? LIMIT 1", (self.trading_mode,))
            return cursor.fetchone()[0] > 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        통계 정보 조회 (현재 trading_mode 기준)

        Returns:
            주문/체결 통계
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 워크플로우 주문 수
            cursor.execute("SELECT COUNT(*) FROM workflow_orders WHERE trading_mode = ?", (self.trading_mode,))
            order_count = cursor.fetchone()[0]

            # 분류별 체결 수
            cursor.execute("""
                SELECT classification, COUNT(*), SUM(quantity)
                FROM trade_history
                WHERE trading_mode = ?
                GROUP BY classification
            """, (self.trading_mode,))
            fill_stats = {row[0]: {"count": row[1], "quantity": row[2]} for row in cursor.fetchall()}

            # 활성 로트 수
            cursor.execute("""
                SELECT classification, COUNT(*), SUM(remaining_qty)
                FROM workflow_position_lots
                WHERE remaining_qty > 0 AND trading_mode = ?
                GROUP BY classification
            """, (self.trading_mode,))
            lot_stats = {row[0]: {"count": row[1], "quantity": row[2]} for row in cursor.fetchall()}

            return {
                "trading_mode": self.trading_mode,
                "workflow_orders": order_count,
                "fills_by_classification": fill_stats,
                "active_lots_by_classification": lot_stats,
                "trust_score": self.calculate_trust_score(),
            }

    def update_order_fill_price(
        self,
        order_no: str,
        order_date: str,
        fill_price: float,
    ) -> bool:
        """
        시장가 주문의 체결 가격 업데이트
        
        시장가 주문은 주문 시점에 가격을 알 수 없으므로,
        체결 이벤트 수신 시 실제 체결 가격으로 업데이트합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            fill_price: 체결 가격
            
        Returns:
            업데이트 성공 여부
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 가격이 0인 주문만 업데이트 (시장가 주문)
            cursor.execute("""
                UPDATE workflow_orders
                SET price = ?
                WHERE order_no = ? AND order_date = ? AND trading_mode = ? AND (price = 0 OR price IS NULL)
            """, (fill_price, order_no, order_date, self.trading_mode))
            
            updated = cursor.rowcount > 0
            conn.commit()
            
            if updated:
                logger.debug(f"Updated order fill price: {order_no} @ {fill_price}")
            
            return updated

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """최근 미체결 가능성이 있는 주문 목록 (긴급 정지 시 사용).

        최근 60초 이내 기록된 주문을 반환합니다.
        체결 여부를 정확히 알 수 없으므로, HTS/MTS에서 직접 확인이 필요합니다.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT order_no, order_date, symbol, exchange, side, quantity, price, node_id
                    FROM workflow_orders
                    WHERE trading_mode = ?
                      AND created_at >= datetime('now', '-60 seconds')
                    ORDER BY created_at DESC
                """, (self.trading_mode,))
                return [
                    {
                        "order_no": row[0],
                        "order_date": row[1],
                        "symbol": row[2],
                        "exchange": row[3],
                        "side": row[4],
                        "quantity": row[5],
                        "price": row[6],
                        "node_id": row[7],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception:
            return []

    def get_orders_without_fill_price(self) -> List[Dict[str, Any]]:
        """
        체결 가격이 없는 주문 목록 조회
        
        연결 끊김 등으로 체결 이벤트를 놓친 경우,
        체결내역 조회로 가격을 복구하기 위한 메서드입니다.
        
        Returns:
            가격이 0인 주문 목록
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT order_no, order_date, symbol, exchange, side, quantity
                FROM workflow_orders
                WHERE trading_mode = ? AND (price = 0 OR price IS NULL)
                ORDER BY created_at DESC
            """, (self.trading_mode,))
            
            return [
                {
                    "order_no": row[0],
                    "order_date": row[1],
                    "symbol": row[2],
                    "exchange": row[3],
                    "side": row[4],
                    "quantity": row[5],
                }
                for row in cursor.fetchall()
            ]

    def sync_fill_prices_from_history(
        self,
        fill_history: List[Dict[str, Any]],
    ) -> int:
        """
        체결내역에서 주문 가격 동기화 (Fallback)
        
        연결 끊김 등으로 실시간 체결 이벤트를 놓친 경우,
        체결내역 API 응답으로 가격을 복구합니다.
        
        Args:
            fill_history: 체결내역 API 응답 리스트
                [{"order_no": "123", "order_date": "20260123", "fill_price": 2.82}, ...]
            
        Returns:
            업데이트된 주문 수
        """
        updated_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for fill in fill_history:
                order_no = fill.get("order_no", "")
                order_date = fill.get("order_date", "")
                fill_price = fill.get("fill_price", 0)
                
                if not order_no or not order_date or fill_price <= 0:
                    continue
                
                cursor.execute("""
                    UPDATE workflow_orders
                    SET price = ?
                    WHERE order_no = ? AND order_date = ? AND trading_mode = ? AND (price = 0 OR price IS NULL)
                """, (fill_price, order_no, order_date, self.trading_mode))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    logger.debug(f"Synced fill price from history: {order_no} @ {fill_price}")
            
            conn.commit()
        
        if updated_count > 0:
            logger.info(f"Synced {updated_count} order fill prices from history")
        
        return updated_count

    def cancel_order(
        self,
        order_no: str,
        order_date: str,
    ) -> bool:
        """
        주문 취소 처리
        
        취소 완료 이벤트('13') 수신 시 호출하여 주문을 삭제합니다.
        아직 체결되지 않은 주문만 취소 가능합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            
        Returns:
            취소 성공 여부
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # workflow_orders에서 삭제
            cursor.execute("""
                DELETE FROM workflow_orders
                WHERE order_no = ? AND order_date = ? AND trading_mode = ?
            """, (order_no, order_date, self.trading_mode))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            
            if deleted:
                logger.info(f"Cancelled workflow order: {order_no}")
            else:
                logger.debug(f"Order not found for cancellation: {order_no}")
            
            return deleted

    def modify_order(
        self,
        order_no: str,
        order_date: str,
        new_quantity: Optional[int] = None,
        new_price: Optional[float] = None,
    ) -> bool:
        """
        주문 정정 처리
        
        정정 완료 이벤트('12') 수신 시 호출하여 주문 정보를 업데이트합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            new_quantity: 새 수량 (None이면 변경 안함)
            new_price: 새 가격 (None이면 변경 안함)
            
        Returns:
            정정 성공 여부
        """
        if new_quantity is None and new_price is None:
            return False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 동적 쿼리 생성
            updates = []
            params = []
            
            if new_quantity is not None:
                updates.append("quantity = ?")
                params.append(new_quantity)
            
            if new_price is not None:
                updates.append("price = ?")
                params.append(new_price)
            
            params.extend([order_no, order_date, self.trading_mode])

            cursor.execute(f"""
                UPDATE workflow_orders
                SET {", ".join(updates)}
                WHERE order_no = ? AND order_date = ? AND trading_mode = ?
            """, params)
            
            updated = cursor.rowcount > 0
            conn.commit()
            
            if updated:
                logger.info(f"Modified workflow order: {order_no} (qty={new_quantity}, price={new_price})")
            else:
                logger.debug(f"Order not found for modification: {order_no}")
            
            return updated

    def sync_fills_from_history(
        self,
        fill_history: List[Dict[str, Any]],
    ) -> int:
        """
        체결내역에서 FIFO 포지션 동기화 (record_fill 호출)
        
        연결 끊김 등으로 실시간 체결 이벤트를 놓친 경우,
        체결내역 API 응답으로 포지션을 생성합니다.
        
        Args:
            fill_history: 체결내역 API 응답 리스트
                [{
                    "order_no": "123",
                    "order_date": "20260123",
                    "symbol": "AAPL",
                    "exchange": "NASDAQ",
                    "side": "buy",
                    "quantity": 10,
                    "price": 192.50,
                    "fill_time": "093000000"
                }, ...]
            
        Returns:
            처리된 체결 수
        """
        processed_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for fill in fill_history:
                order_no = fill.get("order_no", "")
                order_date = fill.get("order_date", "")
                symbol = fill.get("symbol", "")
                exchange = fill.get("exchange", "NASDAQ")
                side = fill.get("side", "")
                quantity = fill.get("quantity", 0)
                price = fill.get("price", 0)
                fill_time = fill.get("fill_time", "")
                
                if not order_no or not order_date or not symbol or not side:
                    continue
                
                if quantity <= 0 or price <= 0:
                    continue
                
                # 이미 처리된 체결인지 확인 (trade_history에 있는지)
                cursor.execute("""
                    SELECT COUNT(*) FROM trade_history
                    WHERE order_no = ? AND order_date = ? AND trading_mode = ?
                """, (order_no, order_date, self.trading_mode))
                
                if cursor.fetchone()[0] > 0:
                    # 이미 처리됨
                    continue
        
        # 연결 닫고 record_fill 호출 (별도 트랜잭션)
        from programgarden.database.workflow_position_tracker import FillEvent
        
        for fill in fill_history:
            order_no = fill.get("order_no", "")
            order_date = fill.get("order_date", "")
            symbol = fill.get("symbol", "")
            exchange = fill.get("exchange", "NASDAQ")
            side = fill.get("side", "")
            quantity = fill.get("quantity", 0)
            price = fill.get("price", 0)
            fill_time = fill.get("fill_time", "")
            
            if not order_no or not symbol or not side or quantity <= 0 or price <= 0:
                continue
            
            fill_event = FillEvent(
                order_no=order_no,
                order_date=order_date,
                symbol=symbol,
                exchange=exchange,
                side=side,
                quantity=quantity,
                price=price,
                fill_time=fill_time,
                commda_code="40",  # OPEN API
            )
            
            try:
                self.record_fill(fill_event)
                processed_count += 1
                logger.info(f"Synced fill from history: {symbol} {side} {quantity}@{price}")
            except Exception as e:
                logger.warning(f"Failed to sync fill from history: {order_no} - {e}")
        
        return processed_count
