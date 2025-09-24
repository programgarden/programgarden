"""Scaling trailing-stop manager with SQLite persistence.

This module provides TrailingStopManager, a small, self-contained utility
to manage per-position highest-price tracking and trailing stop logic.

Design goals:
- Persistent storage (SQLite) so highest-price / highest-profit survives restarts.
- Support scaling rules: change trailing percent at defined profit thresholds.
- Simple importable API for external users.

Usage (basic):
    from programgarden_community.overseas_stock.sell_new.loss_cut import TrailingStopManager

    mgr = TrailingStopManager('~/.trailing_stop.db')
    mgr.open_position('AAPL', entry_price=100.0, trailing_pct=0.03, scale_rules=[(0.05, 0.02), (0.15, 0.01)])
    action = mgr.update_price('AAPL', 110.0)
    if action == 'sell':
        # execute market sell and mgr.close_position('AAPL')

The class is intentionally dependency-free (uses stdlib sqlite3) so it's easy
to drop into most projects.
"""

from __future__ import annotations

from datetime import datetime
import os
import sqlite3
from typing import List, Optional
from zoneinfo import ZoneInfo
from programgarden_core import (
    BaseSellOverseasStock, BaseSellOverseasStockResponseType
)


class TrailingStopManager(BaseSellOverseasStock):

    id: str = "TrailingStopManager"
    description: str = "트레일링 스탑 매니저"
    securities: List[str] = ["ls-sec.co.kr"]

    def __init__(
        self,
        appkey: Optional[str] = None,
        appsecretkey: Optional[str] = None,
        scailing_bool: bool = True,
        scailing_rate: float = 0.8,
        start_losscut: float = -5,
    ):
        """
        스케일링 트레일링 스탑 매니저 초기화

        Args:
            appkey (Optional[str]): LS증권 앱키
            appsecretkey (Optional[str]): LS증권 앱시크릿키
            scailing_bool (bool): 스케일링 여부
            scailing_rate (float): 스케일링 비율
            start_losscut (float): 시작 손절매 비율
        """
        super().__init__()

        self.appkey = appkey
        self.appsecretkey = appsecretkey
        self.scailing_bool = scailing_bool
        self.scailing_rate = scailing_rate
        self.start_losscut = start_losscut

        self.db_path = self._default_db_path()
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_db()

    def _default_db_path(self) -> str:
        base = os.path.join(os.getcwd(), "trailing_db")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "trailing_stop.db")

    async def execute(self) -> List[BaseSellOverseasStockResponseType]:

        create_at_eastern = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S%z")

        # 잔고평가 가져오기
        results: List[BaseSellOverseasStockResponseType] = []

        for held in self.held_symbols:
            shtn_isu_no = held.get("ShtnIsuNo")
            fcurr_mkt_code = held.get("FcurrMktCode")
            keysymbol = fcurr_mkt_code + shtn_isu_no
            pnl_rat = held.get("PnlRat")
            astk_sell_able_qty = held.get("AstkSellAbleQty")
            crcy_code = held.get("CrcyCode")
            pchs_amt = held.get("PchsAmt")

            row = self._get_position(keysymbol)

            # DB에 없으면, 초기값 저장하기
            if not row:
                conn = self._connect()
                conn.execute(
                    "INSERT INTO scaling_positions (keysymbol, highest_income, create_at)"
                    " VALUES (?, ?, ?)",
                    (keysymbol, 0.0, create_at_eastern),
                )
                conn.commit()

            highest_income = row["highest_income"]

            # 손절 비율 계산
            cut_rate = self.scailing_rate * highest_income

            # 0% 이하인 경우 손절 비율로 계산
            if pnl_rat <= 0:
                if self.start_losscut <= cut_rate:
                    data: BaseSellOverseasStockResponseType = {
                        "success": True,
                        "shtn_isu_no": shtn_isu_no,
                        "ord_mkt_code": fcurr_mkt_code,
                        "ord_ptn_code": "01",
                        "ord_qty": astk_sell_able_qty,  # 전량 매도
                        "ordprc_ptn_code": "03",
                        "ovrs_ord_prc": 0.0,  # 시장가,
                        "crcy_code": crcy_code,
                        "pnl_rat": pnl_rat,
                        "pchs_amt": pchs_amt,
                    }
                    results.append(data)

                # 손절매 실행
                elif pnl_rat <= cut_rate:
                    data: BaseSellOverseasStockResponseType = {
                        "success": True,
                        "isu_no": shtn_isu_no,
                        "ord_mkt_code": fcurr_mkt_code,
                        "ord_ptn_code": "01",
                        "ord_qty": astk_sell_able_qty,  # 전량 매도
                        "ordprc_ptn_code": "03",
                        "ovrs_ord_prc": 0.0,  # 시장가
                        "crcy_code": crcy_code,
                        "pnl_rat": pnl_rat,
                        "pchs_amt": pchs_amt,
                    }
                    results.append(data)

                # 최고 수익률 갱신
                elif pnl_rat > highest_income:
                    conn = self._connect()
                    conn.execute(
                        "REPLACE INTO scaling_positions (keysymbol, highest_income)"
                        " VALUES (?, ?)",
                        (keysymbol, pnl_rat),
                    )
                    conn.commit()

        return results

    async def on_real_order_receive(self, order_type, response):
        """
        매도 주문후 종목들을 반환받습니다.
        """
        print(f"매도 Community 주문 데이터 수신: {order_type}")

        return
        for held in self.held_symbols:
            shtn_isu_no = held.get("ShtnIsuNo")
            fcurr_mkt_code = held.get("FcurrMktCode")
            keysymbol = fcurr_mkt_code + shtn_isu_no

            print("데이터 수신했음", keysymbol)

            # self.close_position(keysymbol)
            # print(f"TrailingStopManager: Closed position for {keysymbol}")

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_db(self) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS scaling_positions (
                keysymbol TEXT PRIMARY KEY,
                highest_income REAL NOT NULL,
                create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

    def _get_position(self, keysymbol: str) -> Optional[sqlite3.Row]:
        if not keysymbol:
            return None

        cur = self._connect().cursor()
        cur.execute("SELECT * FROM scaling_positions WHERE keysymbol = ?", (keysymbol,))
        return cur.fetchone()

    def close_position(self, keysymbol: str) -> None:
        conn = self._connect()
        conn.execute("DELETE FROM scaling_positions WHERE keysymbol = ?", (keysymbol,))
        conn.commit()


if __name__ == "__main__":
    mgr = TrailingStopManager(":memory:")
    mgr.open_position("TST", entry_price=100.0, trailing_pct=0.05, scale_rules=[(0.05, 0.03), (0.2, 0.02)])

    prices = [100, 102, 106, 110, 108, 105, 101, 99]
    for p in prices:
        action = mgr.update_price("TST", p)
        pos = mgr.get_position("TST")
        print(f"price={p:.2f} highest={pos['highest_price']:.2f} stop={pos['stop_price']:.2f} action={action}")
        if action == "sell":
            print("=> SELL signal")
            mgr.close_position("TST")
            break
