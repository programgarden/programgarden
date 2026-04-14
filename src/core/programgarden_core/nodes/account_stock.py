"""
ProgramGarden Core - Stock Account Node

해외주식 계좌 조회:
- OverseasStockAccountNode: 해외주식 계좌 잔고, 보유종목 조회 (REST API 1회성)
"""

from typing import List, Literal, Dict, ClassVar, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    ProductScope,
    BrokerProvider,
    OVERSEAS_STOCK_BALANCE_FIELDS,
    POSITION_FIELDS,
    SYMBOL_LIST_FIELDS,
)


class OverseasStockAccountNode(BaseNode):
    """
    해외주식 REST API 1회성 계좌 조회 노드

    특정 시점의 해외주식 계좌 정보를 REST API로 조회합니다:
    - 보유종목 목록
    - 각 종목별 포지션 (수량, 평균단가, 평가금액, 손익률)
    - 예수금/총자산

    미체결 주문 조회는 OverseasStockOpenOrdersNode를 사용하세요.
    실시간 업데이트가 필요하면 OverseasStockRealAccountNode를 사용하세요.
    """

    type: Literal["OverseasStockAccountNode"] = "OverseasStockAccountNode"
    category: NodeCategory = NodeCategory.ACCOUNT
    description: str = "i18n:nodes.OverseasStockAccountNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.STOCK
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="held_symbols",
            type="symbol_list",
            description="i18n:ports.held_symbols",
            fields=SYMBOL_LIST_FIELDS,
            example=[
                {"exchange": "NASDAQ", "symbol": "AAPL"},
                {"exchange": "NASDAQ", "symbol": "TSLA"},
            ],
        ),
        OutputPort(
            name="balance",
            type="balance_data",
            description="i18n:ports.balance",
            fields=OVERSEAS_STOCK_BALANCE_FIELDS,
            example={
                "total_pnl_rate": 7.42,
                "cash_krw": 5_000_000,
                "stock_eval_krw": 12_500_000,
                "total_eval_krw": 17_500_000,
                "total_pnl_krw": 1_210_000,
                "orderable_amount": 3_500.50,
                "foreign_cash": 3_800.10,
                "exchange_rate": 1380.25,
            },
        ),
        OutputPort(
            name="positions",
            type="position_data",
            description="i18n:ports.positions",
            fields=POSITION_FIELDS,
            example=[
                {"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 10, "avg_price": 175.20, "pnl_rate": 6.99},
                {"symbol": "TSLA", "exchange": "NASDAQ", "quantity": 5, "avg_price": 240.00, "pnl_rate": -2.50},
            ],
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        return {}
