"""
균등하게 분할매수하기 위한 자금배분
"""
from typing import List, Optional
from programgarden_core import (
    BaseNewOrderOverseasStock,
    BaseNewOrderOverseasStockResponseType,
)
from programgarden_finance import LS, g3101


class StockSplitFunds(BaseNewOrderOverseasStock):

    id: str = "StockSplitFunds"
    description: str = "주식 분할 자금"
    securities: List[str] = ["ls-sec.co.kr"]
    order_types = ["new_buy"]

    def __init__(
        self,
        appkey: Optional[str] = None,
        appsecretkey: Optional[str] = None,
        percent_balance: float = 10.0,
        max_symbols: float = 5,
    ):
        """
        주식 분할 자금 초기화

        Args:
            appkey (Optional[str]): LS증권 앱키
            appsecretkey (Optional[str]): LS증권 앱시크릿키
            percent_balance (float): 현재 예수금의 몇 %를 사용할지
            max_symbols (float): 최대 몇 종목까지 매수할지
        """
        super().__init__()

        self.appkey = appkey
        self.appsecretkey = appsecretkey
        self.percent_balance = percent_balance
        self.max_symbols = max_symbols

    async def execute(self) -> List[BaseNewOrderOverseasStockResponseType]:
        ls = LS.get_instance()
        if not ls.is_logged_in():
            await ls.async_login(
                appkey=self.appkey,
                appsecretkey=self.appsecretkey
            )

        fcurr_dps = self.fcurr_dps * self.percent_balance

        # 종목당 최대 매수 금액
        per_max_amt = round(fcurr_dps / self.max_symbols, 2)

        orders: List[BaseNewOrderOverseasStockResponseType] = []
        for symbol in self.available_symbols:
            if len(orders) >= self.max_symbols:
                break

            exchcd = symbol.get("exchcd")
            symbol = symbol.get("symbol")

            cur = await ls.overseas_stock().market().g3101(
                body=g3101.G3101InBlock(
                    keysymbol=exchcd+symbol,
                    exchcd=exchcd,
                    symbol=symbol
                )
            ).req_async()

            # 계산된 금액으로 살 수 있는 최대 수량(정수)
            price = round(float(cur.block.price), 1)
            if price <= 0:
                buy_qty = 0
            else:
                buy_qty = int(per_max_amt // price)
            if buy_qty < 1:
                continue

            # 주문 생성
            order: BaseNewOrderOverseasStockResponseType = {
                "success": True,
                "ord_ptn_code": "02",
                "ord_mkt_code": exchcd,
                "shtn_isu_no": symbol,
                "ord_qty": buy_qty,
                "ovrs_ord_prc": price,
                "ordprc_ptn_code": "00",
                "bns_tp_code": "2",  # 매수
            }

            orders.append(order)

        return orders

    async def on_real_order_receive(self, order_type, response):
        pass


__all__ = [
    "StockSplitFunds"
]
