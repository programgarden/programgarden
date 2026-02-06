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
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PositionInfo:
    """포지션 정보"""
    symbol: str
    exchange: str
    quantity: int
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

        # 체결 버퍼 (Race Condition 방어)
        self._pending_fills: Dict[str, PendingFill] = {}  # key: order_no_order_date
        self._buffer_lock = asyncio.Lock()

        # DB 초기화
        self._init_db()
    
    def _init_db(self) -> None:
        """데이터베이스 테이블 초기화"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
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
                    created_at TEXT
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
        """버퍼에서 매칭되는 체결 처리"""
        key = f"{order_no}_{order_date}"
        
        async with self._buffer_lock:
            if key in self._pending_fills:
                fill = self._pending_fills.pop(key)
                logger.debug(f"Processing buffered fill: {key}")
                await self._process_fill_internal(fill, "workflow")
    
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
            commda_code: 매체구분코드 (40=OPEN API)
            
        Returns:
            분류 결과: "workflow" | "manual" | "unknown_api" | "pending"
        """
        # 1. 수동 주문 (앱/HTS) - CommdaCode != "40"
        if commda_code != "40":
            fill = PendingFill(
                order_no=order_no, order_date=order_date, symbol=symbol,
                exchange=exchange, side=side, quantity=quantity, price=price,
                fill_time=fill_time, commda_code=commda_code, received_at=datetime.now()
            )
            await self._process_fill_internal(fill, "manual")
            return "manual"
        
        # 2. API 주문 - DB 확인
        is_workflow = self._check_workflow_order(order_no, order_date)
        
        if is_workflow:
            fill = PendingFill(
                order_no=order_no, order_date=order_date, symbol=symbol,
                exchange=exchange, side=side, quantity=quantity, price=price,
                fill_time=fill_time, commda_code=commda_code, received_at=datetime.now()
            )
            await self._process_fill_internal(fill, "workflow")
            return "workflow"
        
        # 3. API 주문인데 DB에 없음 - 버퍼에 저장
        key = f"{order_no}_{order_date}"
        fill = PendingFill(
            order_no=order_no, order_date=order_date, symbol=symbol,
            exchange=exchange, side=side, quantity=quantity, price=price,
            fill_time=fill_time, commda_code=commda_code, received_at=datetime.now()
        )
        
        async with self._buffer_lock:
            self._pending_fills[key] = fill
        
        # 타임아웃 후 처리
        asyncio.create_task(self._process_timeout_fill(key))
        
        logger.debug(f"Buffered fill (waiting for order): {key}")
        return "pending"
    
    async def _process_timeout_fill(self, key: str) -> None:
        """버퍼 타임아웃 후 처리"""
        await asyncio.sleep(self.FILL_BUFFER_TIMEOUT)
        
        async with self._buffer_lock:
            if key in self._pending_fills:
                fill = self._pending_fills.pop(key)
                logger.warning(f"Fill timeout - classifying as unknown_api: {key}")
                await self._process_fill_internal(fill, "unknown_api")
    
    async def _process_fill_internal(self, fill: PendingFill, classification: str) -> None:
        """체결 내부 처리 (FIFO 로직)"""
        fill_datetime = f"{fill.order_date}_{fill.fill_time}"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            realized_pnl = 0.0

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
                realized_pnl = self._process_sell_fifo(
                    cursor, fill.symbol, fill.quantity, fill.price, classification
                )

            # 체결 내역 저장
            cursor.execute("""
                INSERT INTO trade_history
                (product, provider, order_no, order_date, symbol, exchange, side, quantity, price,
                 fill_datetime, classification, commda_code, realized_pnl, trading_mode, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.product, self.provider,
                fill.order_no, fill.order_date, fill.symbol, fill.exchange,
                fill.side, fill.quantity, fill.price, fill_datetime,
                classification, fill.commda_code, realized_pnl, self.trading_mode, datetime.now().isoformat()
            ))

            conn.commit()

        logger.debug(f"Processed fill: {fill.symbol} {fill.side} {fill.quantity}@{fill.price} [{classification}] ({self.trading_mode})")
    
    def _process_sell_fifo(
        self,
        cursor: sqlite3.Cursor,
        symbol: str,
        quantity: int,
        sell_price: float,
        classification: str,
    ) -> float:
        """
        FIFO 매도 처리
        
        fill_datetime 순으로 정렬하여 선입선출 방식으로 청산합니다.
        
        Args:
            cursor: DB 커서
            symbol: 종목코드
            quantity: 매도 수량
            sell_price: 매도가
            classification: 분류 (로깅용)
            
        Returns:
            실현 손익
        """
        remaining_to_sell = quantity
        total_realized_pnl = 0.0
        
        # fill_datetime 순으로 정렬 (FIFO, 현재 trading_mode 내에서만)
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
        
        if remaining_to_sell > 0:
            logger.warning(f"Sell without enough position: {symbol} remaining={remaining_to_sell}")
        
        return total_realized_pnl
    
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
                if symbol in positions:
                    # 같은 종목: 평균단가 재계산
                    pos = positions[symbol]
                    total_qty = pos.quantity + remaining_qty
                    total_cost = (pos.avg_price * pos.quantity) + (Decimal(str(buy_price)) * remaining_qty)
                    pos.quantity = total_qty
                    pos.avg_price = total_cost / total_qty
                else:
                    positions[symbol] = PositionInfo(
                        symbol=symbol,
                        exchange=exchange or "",
                        quantity=remaining_qty,
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
            total_qty = pos_data.get("quantity", 0) or pos_data.get("qty", 0)
            avg_price = pos_data.get("avg_price", 0) or pos_data.get("buy_price", 0)
            exchange = pos_data.get("exchange", "")
            
            workflow_qty = workflow_positions.get(symbol, PositionInfo(symbol, "", 0, Decimal(0), "")).quantity
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
        
        workflow_positions = self.get_workflow_positions(start_date=start_date)
        other_positions = self.get_other_positions(all_positions)
        
        # 워크플로우 포지션 계산
        wf_eval = Decimal(0)
        wf_buy = Decimal(0)
        wf_details: List[PositionDetail] = []
        
        for symbol, pos in workflow_positions.items():
            current_price = prices.get(symbol, pos.avg_price)
            eval_amount = current_price * pos.quantity
            buy_amount = pos.avg_price * pos.quantity
            pnl_amount = eval_amount - buy_amount
            pnl_rate = (pnl_amount / buy_amount * 100) if buy_amount else Decimal(0)
            
            wf_eval += eval_amount
            wf_buy += buy_amount
            
            wf_details.append(PositionDetail(
                symbol=symbol,
                exchange=pos.exchange,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                current_price=current_price,
                pnl_amount=pnl_amount,
                pnl_rate=pnl_rate,
            ))
        
        wf_pnl = wf_eval - wf_buy
        wf_rate = (wf_pnl / wf_buy * 100) if wf_buy else Decimal(0)
        
        # 그 외 포지션 계산
        other_eval = Decimal(0)
        other_buy = Decimal(0)
        other_details: List[PositionDetail] = []
        
        for symbol, pos in other_positions.items():
            current_price = prices.get(symbol, pos.avg_price)
            eval_amount = current_price * pos.quantity
            buy_amount = pos.avg_price * pos.quantity
            pnl_amount = eval_amount - buy_amount
            pnl_rate = (pnl_amount / buy_amount * 100) if buy_amount else Decimal(0)
            
            other_eval += eval_amount
            other_buy += buy_amount
            
            other_details.append(PositionDetail(
                symbol=symbol,
                exchange=pos.exchange,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                current_price=current_price,
                pnl_amount=pnl_amount,
                pnl_rate=pnl_rate,
            ))
        
        other_pnl = other_eval - other_buy
        other_rate = (other_pnl / other_buy * 100) if other_buy else Decimal(0)
        
        # 전체 계산
        total_eval = wf_eval + other_eval
        total_buy = wf_buy + other_buy
        total_pnl = total_eval - total_buy
        total_rate = (total_pnl / total_buy * 100) if total_buy else Decimal(0)
        
        # 신뢰도 계산
        anomalies = self.detect_anomalies()
        trust_score = self.calculate_trust_score(anomalies)
        
        return {
            "job_id": self.job_id,
            "broker_node_id": self.broker_node_id,
            "product": self.product,
            
            "workflow_pnl_rate": wf_rate,
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
