from __future__ import annotations

from typing import List
from programgarden_core import (
    BaseNewOrderOverseasStock, BaseNewOrderOverseasStockResponseType
)


class BasicLossCutManager(BaseNewOrderOverseasStock):

    id: str = "BasicLossCutManager"
    description: str = "기본 손절매 매니저"
    securities: List[str] = ["ls-sec.co.kr"]
    order_types = ["new_sell"]

    def __init__(
        self,
        losscut: float = -5,
    ):
        """
        기본 손절매 매니저 초기화

        Args:
            losscut (float): 손절매 비율
        """
        super().__init__()

        self.losscut = losscut

    async def execute(self) -> List[BaseNewOrderOverseasStockResponseType]:
        results: List[BaseNewOrderOverseasStockResponseType] = []
        for held in self.held_symbols:
            shtn_isu_no = held.get("ShtnIsuNo")
            fcurr_mkt_code = held.get("FcurrMktCode")
            # keysymbol = fcurr_mkt_code + shtn_isu_no

            rnl_rat = float(held.get("PnlRat", 0))

            if rnl_rat <= self.losscut:
                result: BaseNewOrderOverseasStockResponseType = {
                    "success": True,
                    "ord_ptn_code": "01",
                    "ord_mkt_code": fcurr_mkt_code,
                    "shtn_isu_no": shtn_isu_no,
                    "ord_qty": held.get("AstkSellAbleQty", 0),
                    "ovrs_ord_prc": 0.0,
                    "ordprc_ptn_code": "03",
                    "crcy_code": "USD",
                    "pnl_rat": rnl_rat,
                    "pchs_amt": held.get("PchsAmt", 0.0),
                    "bns_tp_code": "1",  # 매도
                }
                results.append(result)

        return results

    def on_real_order_receive(self, order_type, response):
        pass


__all__ = ["BasicLossCutManager"]
