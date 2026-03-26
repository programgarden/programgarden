"""
ProgramGarden Core - Futures Symbol Query Node

해외선물 전체종목조회:
- OverseasFuturesSymbolQueryNode: 해외선물 전체 거래 가능 종목 조회 (o3101 API)
"""

from typing import Optional, List, Literal, Dict, ClassVar, TYPE_CHECKING
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
    SYMBOL_LIST_FIELDS,
)


class OverseasFuturesSymbolQueryNode(BaseNode):
    """
    해외선물 전체종목조회 노드

    해외선물 전체 거래 가능 종목을 조회합니다.
    o3101 API (해외선물마스터조회) 사용.
    """

    type: Literal["OverseasFuturesSymbolQueryNode"] = "OverseasFuturesSymbolQueryNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.OverseasFuturesSymbolQueryNode.description"
    _img_url: ClassVar[str] = ""
    _product_scope: ClassVar[ProductScope] = ProductScope.FUTURES
    _broker_provider: ClassVar[BrokerProvider] = BrokerProvider.LS

    futures_exchange: Optional[str] = Field(
        default=None,
        description="Exchange for overseas_futures: 1(all), 2(CME), 3(SGX), etc.",
    )
    futures_contract_month: Optional[str] = Field(
        default=None,
        description="Contract month filter for overseas_futures: F, 2026F, front, next",
    )
    max_results: int = Field(
        default=500,
        description="Maximum number of symbols to retrieve per request",
    )

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(name="symbols", type="symbol_list", description="i18n:ports.symbols", fields=SYMBOL_LIST_FIELDS),
        OutputPort(name="count", type="integer", description="Total symbol count"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, ExpressionMode
        return {
            "futures_exchange": FieldSchema(
                name="futures_exchange",
                type=FieldType.ENUM,
                description="거래소 구분. 1: 전체, 2: CME, 3: SGX, 4: EUREX, 5: ICE, 6: HKEX, 7: OSE",
                enum_values=["1", "2", "3", "4", "5", "6", "7"],
                enum_labels={
                    "1": "i18n:enums.futures_exchange.1",
                    "2": "i18n:enums.futures_exchange.2",
                    "3": "i18n:enums.futures_exchange.3",
                    "4": "i18n:enums.futures_exchange.4",
                    "5": "i18n:enums.futures_exchange.5",
                    "6": "i18n:enums.futures_exchange.6",
                    "7": "i18n:enums.futures_exchange.7",
                },
                default="1",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="1",
                expected_type="str",
            ),
            "futures_contract_month": FieldSchema(
                name="futures_contract_month",
                type=FieldType.STRING,
                description="월물 필터. 예: 'F' (1월), '2026F' (2026년 1월), 'front' (근월물), 'next' (차월물). 월물코드: F=1월, G=2월, H=3월, J=4월, K=5월, M=6월, N=7월, Q=8월, U=9월, V=10월, X=11월, Z=12월",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example="front",
                expected_type="str",
                placeholder="front, next, F, 2026F",
            ),
            "max_results": FieldSchema(
                name="max_results",
                type=FieldType.INTEGER,
                description="최대 조회 건수. 연속 조회로 전체 데이터를 가져옵니다.",
                default=500,
                min_value=100,
                max_value=10000,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                example=500,
                expected_type="int",
            ),
        }
