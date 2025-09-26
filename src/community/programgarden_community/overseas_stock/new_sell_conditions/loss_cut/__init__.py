from __future__ import annotations

from typing import List
from programgarden_core import (
    BaseNewSellOverseasStock, BaseNewSellOverseasStockResponseType
)


class BasicLossCutManager(BaseNewSellOverseasStock):

    id: str = "BasicLossCutManager"
    description: str = "기본 손절매 매니저"
    securities: List[str] = ["ls-sec.co.kr"]

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

    async def execute(self) -> List[BaseNewSellOverseasStockResponseType]:

        results: List[BaseNewSellOverseasStockResponseType] = []
        for held in self.held_symbols:
            shtn_isu_no = held.get("ShtnIsuNo")
            fcurr_mkt_code = held.get("FcurrMktCode")
            keysymbol = fcurr_mkt_code + shtn_isu_no

            rnl_rat = float(held.get("PnlRat", 0))

            print(f"손절: {rnl_rat <= self.losscut}, 손절매 조건 충족: {keysymbol} 손익률={rnl_rat:.2f}% <= {self.losscut}%")

            if rnl_rat <= self.losscut:
                result: BaseNewSellOverseasStockResponseType = {
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
                }
                results.append(result)

        print(f"손절매 주문 생성: {len(results)}건")

        return results

    def on_real_order_receive(self, order_type, response):
        pass


__all__ = ["BasicLossCutManager"]
