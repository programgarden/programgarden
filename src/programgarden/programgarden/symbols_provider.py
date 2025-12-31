"""Symbol discovery adapter for LS Securities.

EN:
    Wraps the LS (LS증권) finance client to fetch market, account, and pending
    symbols for overseas stocks and futures. Downstream components use the
    asynchronous :class:`SymbolProvider` to populate strategy universes based
    on order intent. Supports cached data from AccountTracker when available.

KR:
    LS(LS증권) 금융 클라이언트를 감싸 해외 주식/선물의 시장, 보유, 미체결 종목을
    조회합니다. 주문 의도에 따라 전략 우주를 구성할 때 비동기
    :class:`SymbolProvider`를 활용합니다. AccountTracker가 있으면 캐시된 데이터를
    활용합니다.
"""

from __future__ import annotations

from datetime import date, datetime
import logging
from typing import TYPE_CHECKING, List, Literal, Optional, Union
from zoneinfo import ZoneInfo

from programgarden_core import (
    OrderType,
    SecuritiesAccountType,
    SymbolInfoOverseasFutures,
    SymbolInfoOverseasStock,
)

if TYPE_CHECKING:
    from .data_cache_manager import DataCacheManager

logger = logging.getLogger("programgarden.symbols_provider")
from programgarden_finance import (
    CIDBQ01500,
    CIDBQ01800,
    LS,
    g3190,
    o3101,
    o3105,
)


class SymbolProvider:
    """Provide symbol lists tailored to Programgarden order workflows.

    EN:
        Central entry point for fetching symbols across LS endpoints. Each helper
        method focuses on a specific account or market feed to minimize redundant
        API calls. When cache_manager with an active Tracker is set, uses cached
        data instead of direct API calls.

    KR:
        LS 엔드포인트 전반에서 종목을 조회하는 중심 진입점입니다. 각 헬퍼 메서드는
        중복 API 호출을 줄이기 위해 특정 계좌/시장 피드에 집중합니다.
        Tracker가 활성화된 cache_manager가 설정되면 직접 API 호출 대신 캐시
        데이터를 사용합니다.
    """

    def __init__(self, cache_manager: Optional[DataCacheManager] = None):
        """Initialize SymbolProvider with optional cache manager.

        Args:
            cache_manager (Optional[DataCacheManager]):
                EN: Cache manager with Tracker support.
                KR: Tracker 지원 캐시 매니저입니다.
        """
        self._cache_manager = cache_manager

    def set_cache_manager(self, cache_manager: DataCacheManager) -> None:
        """Set cache manager for Tracker-based queries.

        Args:
            cache_manager (DataCacheManager):
                EN: Cache manager instance with Tracker support.
                KR: Tracker 지원 캐시 매니저 인스턴스입니다.
        """
        self._cache_manager = cache_manager

    async def get_symbols(
        self,
        order_type: Optional[OrderType],
        securities: SecuritiesAccountType,
        product: Literal["overseas_stock", "overseas_futures"] = "overseas_stock",
        futures_outstanding_only: bool = False,
    ) -> List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]:
        """Retrieve symbols matching the product and order context.

        EN:
            Dispatches to stock or futures helper methods depending on the product
            and order type. Skips all work when the LS client is not authenticated.

        KR:
            상품과 주문 유형에 따라 주식/선물 헬퍼 메서드를 호출하며, LS 클라이언트가
            로그인하지 않은 경우 즉시 작업을 건너뜁니다.

        Args:
            order_type (Optional[OrderType]):
                EN: Order intention (new/modify/cancel) guiding which feeds to query.
                KR: 어떤 피드를 조회할지 결정하는 주문 의도(신규/정정/취소)입니다.
            securities (SecuritiesAccountType):
                EN: Account configuration containing broker/company metadata.
                KR: 증권사/회사 정보를 포함하는 계좌 설정입니다.
            product (Literal[...]):
                EN: ``"overseas_stock"`` or ``"overseas_futures"``.
                KR: ``"overseas_stock"`` 또는 ``"overseas_futures"`` 값을 가집니다.
            futures_outstanding_only (bool):
                EN: When ``True``, include only outstanding futures positions.
                KR: ``True``이면 미결제 선물 포지션만 포함합니다.

        Returns:
            List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]:
                EN: Aggregated symbol list matching the request.
                KR: 요청 조건에 맞는 종합 심볼 목록입니다.
        """

        company = securities.get("company", "ls")
        configured_product = securities.get("product", product)

        if company != "ls":
            return []

        ls = LS.get_instance()
        if not ls.is_logged_in():
            return []

        symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        if configured_product == "overseas_stock":
            if order_type in ("new_buy", None):
                symbols.extend(await self.get_stock_market_symbols(ls))
            elif order_type == "new_sell":
                symbols.extend(await self.get_stock_account_symbols(ls))
            elif order_type in {"modify_buy", "modify_sell", "cancel_buy", "cancel_sell"}:
                symbols.extend(await self.get_stock_non_trade_symbols(ls))

        elif configured_product == "overseas_futures":
            if order_type in {"new_buy", "new_sell", None} and not futures_outstanding_only:
                symbols.extend(await self.get_future_market_symbols(ls))
            elif order_type in {"modify_buy", "modify_sell", "cancel_buy", "cancel_sell"}:
                symbols.extend(
                    await self.get_future_non_trade_symbols(
                        ls=ls,
                        order_type=order_type,
                    )
                )

            # TODO: 해외선물은 매수/매도와 상관없이 보유종목 반환을 해주어야 미결제 체결을 한다.
            # TODO: 현재 요청시 주소 에러가 발생한다. finance에서는 정상이다.
            if futures_outstanding_only:
                symbols.extend(await self.get_future_account_symbols(ls))

        else:
            logger.warning(f"Unsupported product: {configured_product}")

        return symbols

    async def get_stock_account_symbols(self, ls: LS) -> List[SymbolInfoOverseasStock]:
        """Retrieve overseas stock holdings from the account.

        EN:
            Uses cached Tracker data when available, otherwise queries LS account
            endpoints to collect currently held symbols.

        KR:
            Tracker 캐시에서 보유 종목을 조회합니다. Tracker가 초기화되지 않았으면
            예외가 발생합니다.
        """
        holdings: List[SymbolInfoOverseasStock] = []

        # Tracker 필수 - 초기화되지 않았으면 예외 발생
        if not self._cache_manager or not self._cache_manager.has_tracker:
            raise RuntimeError(
                "AccountTracker가 초기화되지 않았습니다. "
                "system_executor._warmup_cache()가 먼저 실행되어야 합니다."
            )

        positions = self._cache_manager.get_positions()
        for symbol, pos in positions.items():
            market_code = getattr(pos, 'market_code', '82')
            holdings.append(
                SymbolInfoOverseasStock(
                    symbol=symbol.strip(),
                    exchcd=market_code,
                    mcap=0.0,
                    product_type="overseas_stock",
                )
            )
        return holdings

    async def get_stock_market_symbols(self, ls: LS) -> List[SymbolInfoOverseasStock]:
        """Retrieve tradable overseas stock symbols from the market feed.

        EN:
            Streams the bulk market list using ``g3190`` and accumulates results via
            the callback interface.

        KR:
            ``g3190`` API의 콜백 인터페이스를 통해 대량 시장 리스트를 스트리밍으로 수집합니다.
        """

        overseas_stock = ls.overseas_stock()
        market_symbols: List[SymbolInfoOverseasStock] = []

        await overseas_stock.market().g3190(
            body=g3190.G3190InBlock(
                delaygb="R",
                natcode="US",
                exgubun="2",
                readcnt=500,
                cts_value="",
            )
        ).occurs_req_async(
            callback=lambda response, _: market_symbols.extend(
                SymbolInfoOverseasStock(
                    symbol=block.symbol.strip(),
                    exchcd=block.exchcd,
                    mcap=block.share * block.clos,
                    product_type="overseas_stock",
                )
                for block in response.block1
            )
            if response and hasattr(response, "block1") and response.block1
            else None
        )

        return market_symbols

    async def get_stock_non_trade_symbols(self, ls: LS) -> List[SymbolInfoOverseasStock]:
        """Retrieve non-traded (open orders) overseas stock symbols.

        EN:
            Uses cached Tracker data when available, otherwise pulls pending orders
            per exchange and resolves them to symbol metadata.

        KR:
            Tracker 캐시에서 미체결 주문을 조회합니다. Tracker가 초기화되지 않았으면
            예외가 발생합니다.
        """
        outstanding: List[SymbolInfoOverseasStock] = []

        # Tracker 필수 - 초기화되지 않았으면 예외 발생
        if not self._cache_manager or not self._cache_manager.has_tracker:
            raise RuntimeError(
                "AccountTracker가 초기화되지 않았습니다. "
                "system_executor._warmup_cache()가 먼저 실행되어야 합니다."
            )

        open_orders = self._cache_manager.get_open_orders()
        for order_no, order in open_orders.items():
            symbol = getattr(order, 'symbol', '').strip()
            market_code = getattr(order, 'market_code', '82') if hasattr(order, 'market_code') else '82'
            outstanding.append(
                SymbolInfoOverseasStock(
                    symbol=symbol,
                    exchcd=market_code,
                    mcap=0.0,
                    OrdNo=int(order_no) if order_no.isdigit() else 0,
                    product_type="overseas_stock",
                )
            )
        return outstanding

    async def get_future_market_symbols(self, ls: LS) -> List[SymbolInfoOverseasFutures]:
        """Retrieve all overseas futures symbols from the market feed.

        EN:
            Calls ``o3101`` to obtain the universe of futures symbols, attaching
            optional metadata (due month, currency, margins) when available.

        KR:
            ``o3101`` API를 호출해 선물 종목 전체를 가져오고, 제공되는 경우 만기 월,
            통화, 증거금 등 부가 정보를 추가합니다.
        """

        futures_symbols: List[SymbolInfoOverseasFutures] = []

        o3101_response = await ls.overseas_futureoption().market().o3101(
            body=o3101.O3101InBlock(gubun="1")
        ).req_async()

        if not o3101_response or not getattr(o3101_response, "block", None):
            return futures_symbols

        for block in o3101_response.block:
            try:
                symbol_code = block.Symbol.strip()
            except AttributeError:
                symbol_code = block.Symbol

            # 모의투자는 홍콩거래소만 지원됩니다.
            if ls.token_manager.paper_trading and block.ExchCd.strip() != "HKEX":
                continue

            symbol_info: SymbolInfoOverseasFutures = SymbolInfoOverseasFutures(
                symbol=symbol_code,
                exchcd=(block.ExchCd or "").strip(),
                product_type="overseas_futures",
            )

            if getattr(block, "SymbolNm", None):
                symbol_info["symbol_name"] = block.SymbolNm.strip()

            year = (block.LstngYr or "").strip()
            month = (block.LstngM or "").strip()
            due = f"{year}{month}" if year or month else ""
            if due:
                symbol_info["due_yymm"] = due

            if getattr(block, "GdsCd", None):
                symbol_info["prdt_code"] = block.GdsCd.strip()

            if getattr(block, "CrncyCd", None):
                symbol_info["currency_code"] = block.CrncyCd.strip()

            try:
                symbol_info["contract_size"] = float(block.CtrtPrAmt)
            except (TypeError, ValueError):
                pass

            try:
                symbol_info["unit_price"] = float(block.UntPrc)
            except (TypeError, ValueError):
                pass

            try:
                symbol_info["min_change_amount"] = float(block.MnChgAmt)
            except (TypeError, ValueError):
                pass

            try:
                symbol_info["maintenance_margin"] = float(block.MntncMgn)
            except (TypeError, ValueError):
                pass

            try:
                symbol_info["opening_margin"] = float(block.OpngMgn)
            except (TypeError, ValueError):
                pass

            futures_symbols.append(symbol_info)

        return futures_symbols

    async def get_future_non_trade_symbols(
        self,
        ls: LS,
        order_type: Optional[OrderType] = None,
    ) -> List[SymbolInfoOverseasFutures]:
        """Retrieve overseas futures orders that are still outstanding.

        EN:
            Looks up pending futures orders via ``CIDBQ01800`` and enriches each
            entry with market data to aid cancel/modify flows.

        KR:
            ``CIDBQ01800`` API를 통해 미체결 선물 주문을 조회하고, 취소/정정 흐름을 돕기
            위해 시장 데이터를 추가합니다.
        """

        outstanding: List[SymbolInfoOverseasFutures] = []

        bns_tp_code = "0"
        if order_type in {"modify_buy", "cancel_buy"}:
            bns_tp_code = "2"
        elif order_type in {"modify_sell", "cancel_sell"}:
            bns_tp_code = "1"

        try:
            cidbq01800_response = await ls.overseas_futureoption().accno().CIDBQ01800(
                body=CIDBQ01800.CIDBQ01800InBlock1(
                    RecCnt=1,
                    IsuCodeVal="",  # 빈 문자열로 계좌 내 전체 미체결 주문을 조회합니다.
                    OrdDt="",
                    OrdStatCode="2",
                    BnsTpCode=bns_tp_code,
                    QryTpCode="1",
                    OrdPtnCode="00",
                    OvrsDrvtFnoTpCode="A",
                )
            ).req_async()
        except Exception as exc:
            logger.exception(f"해외선물 미체결 주문 조회에 실패했습니다: {exc}")
            return outstanding

        if not cidbq01800_response or not getattr(cidbq01800_response, "block2", None):
            return outstanding

        for block in cidbq01800_response.block2:
            try:
                pending_qty = int(getattr(block, "UnercQty", 0) or 0)
            except (TypeError, ValueError):
                pending_qty = 0

            if pending_qty <= 0:
                continue

            symbol_code = str(getattr(block, "IsuCodeVal", "") or "").strip()
            if not symbol_code:
                continue

            futures_info: SymbolInfoOverseasFutures = {
                "symbol": symbol_code,
                "product_type": "overseas_futures",
                "position_side": "flat",
                "OrdNo": block.OvrsFutsOrdNo,
            }

            # 모의투자에서도 사용 가능한 종목인지 확인하기 위해서 시세 요청
            # 모의투자 종목은 시세 요청에서 데이터가 나오지 않는다.
            exist_req = await ls.overseas_futureoption().market().o3105(
                body=o3105.O3105InBlock(symbol=symbol_code)
            ).req_async()

            if not exist_req or not getattr(exist_req, "block", None):
                if ls.token_manager.paper_trading:
                    logger.warning(f"모의투자API에서 지원되지 않는 종목입니다: {symbol_code}")
                logger.warning(f"해외선물API에서 지원되지 않는 종목입니다: {symbol_code}")
                continue

            futures_info["exchcd"] = exist_req.block.ExchCd
            futures_info["due_yymm"] = exist_req.block.MtrtDt
            futures_info["prdt_code"] = exist_req.block.GdsCd
            futures_info["currency_code"] = exist_req.block.CrncyCd
            futures_info["contract_size"] = float(exist_req.block.CtrtPrAmt)
            futures_info["position_side"] = (
                "short" if block.BnsTpCode == "1" else "long" if block.BnsTpCode == "2" else "flat"
            )
            futures_info["unit_price"] = float(exist_req.block.UntPrc)
            futures_info["min_change_amount"] = float(exist_req.block.MnChgAmt)
            futures_info["maintenance_margin"] = float(exist_req.block.MntncMgn)
            futures_info["opening_margin"] = float(exist_req.block.OpngMgn)

            outstanding.append(futures_info)

        return outstanding

    async def get_future_account_symbols(self, ls: LS) -> List[SymbolInfoOverseasFutures]:
        """Retrieve overseas futures positions currently held in the account.

        EN:
            Queries the balance endpoint for open futures positions and confirms
            each symbol is supported on the target environment (live or paper).

        KR:
            보유 선물 포지션을 조회하고 대상 환경(실거래/모의)에 지원되는 종목인지
            확인합니다.
        """

        holdings: List[SymbolInfoOverseasFutures] = []

        ny_time = datetime.now(ZoneInfo("America/New_York"))
        query_date = ny_time.strftime("%Y%m%d")

        try:
            balance_response = await ls.overseas_futureoption().accno().CIDBQ01500(
                body=CIDBQ01500.CIDBQ01500InBlock1(
                    RecCnt=1,
                    QryDt=query_date,
                    BalTpCode="2",
                )
            ).req_async()

        except Exception as exc:
            logger.exception(f"해외선물 보유 종목 조회에 실패했습니다: {exc}")
            return holdings

        if not balance_response or not getattr(balance_response, "block2", None):
            return holdings

        for block in balance_response.block2:
            symbol_code = str(getattr(block, "IsuCodeVal", "") or "").strip()
            if not symbol_code:
                continue

            exist_req = await ls.overseas_futureoption().market().o3105(
                body=o3105.O3105InBlock(symbol=symbol_code)
            ).req_async()

            if not exist_req or not getattr(exist_req, "block", None) or not getattr(exist_req.block, "Symbol", None):
                if ls.token_manager.paper_trading:
                    logger.warning(
                        f"해외선물 잔고 종목 조회 중단: 종목코드 {symbol_code}는(은) 모의투자API에서 조회할 수 없는 종목입니다."
                    )
                logger.warning(
                    f"해외선물 잔고 종목 조회 중단: 종목코드 {symbol_code}는(은) 지원되지 않는 종목입니다."
                )
                continue

            futures_info: SymbolInfoOverseasFutures = {
                "symbol": symbol_code,
                "product_type": "overseas_futures",
                "position_side": "short" if block.BnsTpCode == "1" else "long" if block.BnsTpCode == "2" else "flat",
            }

            futures_info["exchcd"] = exist_req.block.ExchCd
            futures_info["due_yymm"] = exist_req.block.MtrtDt
            futures_info["prdt_code"] = exist_req.block.GdsCd
            futures_info["currency_code"] = exist_req.block.CrncyCd
            futures_info["contract_size"] = float(exist_req.block.CtrtPrAmt)
            futures_info["unit_price"] = float(exist_req.block.UntPrc)
            futures_info["min_change_amount"] = float(exist_req.block.MnChgAmt)
            futures_info["maintenance_margin"] = float(exist_req.block.MntncMgn)
            futures_info["opening_margin"] = float(exist_req.block.OpngMgn)

            holdings.append(futures_info)

        return holdings

