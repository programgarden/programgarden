"""
This module provides the BuyExecutor class which is responsible for
resolving and executing external buy/sell plugin classes (conditions).

The executor reads a system configuration, resolves the plugin by its
identifier, instantiates it with configured parameters, and runs its
"execute" method. Results (symbols to act on) are returned to the
caller and also logged.

The implementations here are intentionally small: the executor focuses
on orchestration (resolve -> instantiate -> set context -> execute)
and leaves trading logic to plugin classes that must subclass
`BaseNewBuyOverseasStock` from `programgarden_core`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Set, Union
from zoneinfo import ZoneInfo
from programgarden_core import (
    SystemType, OrderStrategyType,
    order_logger, symbol_logger, exceptions, HeldSymbol,
    HeldSymbolOverseasStock,
    HeldSymbolOverseasFutures,
    NonTradedSymbol,
    NonTradedSymbolOverseasStock,
    NonTradedSymbolOverseasFutures,
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    OrderType,
    DpsTyped
)
from programgarden_core import (
    BaseOrderOverseasStock,
    BaseOrderOverseasFutures,
    BaseNewOrderOverseasStockResponseType,
    BaseModifyOrderOverseasStockResponseType,
    BaseCancelOrderOverseasStockResponseType,
    BaseNewOrderOverseasFuturesResponseType,
    BaseModifyOrderOverseasFuturesResponseType,
    BaseCancelOrderOverseasFuturesResponseType,
)
from programgarden_finance import (
    LS,
    COSAT00301,
    COSAT00311,
    COSOQ00201,
    COSAQ00102,
    COSOQ02701,
    CIDBT00100,
    CIDBT00900,
    CIDBT01000,
    CIDBQ01500,
    CIDBQ01800,
    CIDBQ03000,

    o3105,
)

from programgarden.pg_listener import pg_listener
from programgarden.real_order_executor import RealOrderExecutor
from datetime import datetime

if TYPE_CHECKING:
    from .plugin_resolver import PluginResolver


class BuySellExecutor:
    """Coordinate buy/sell plugin resolution and order execution flows.

    EN:
        Handles orchestration for condition-based trading across overseas
        stock and futures products. The executor resolves plugin classes,
        injects contextual data such as holdings and pending orders, and
        delegates order placement to the `RealOrderExecutor` while keeping
        listeners informed.

    KR:
        해외 주식 및 해외 선물 상품을 대상으로 조건 기반 매매를 오케스트레이션합니다.
        실행기는 플러그인 클래스를 해석하고, 보유/미체결 종목과 같은 컨텍스트 데이터를
        주입한 뒤 `RealOrderExecutor`에 주문 실행을 위임하며 리스너에도 상황을 전달합니다.

    Attributes:
        plugin_resolver (PluginResolver):
            EN: Resolver that translates condition identifiers into
            executable plugin instances.
            KR: 조건 식별자를 실행 가능한 플러그인 인스턴스로 변환하는
            리졸버입니다.
        real_order_executor (RealOrderExecutor):
            EN: Bridge responsible for forwarding completed order payloads
            to downstream communities.
            KR: 완료된 주문 페이로드를 다운스트림 커뮤니티로 전달하는 브리지입니다.
    ---
    속성:
        plugin_resolver (PluginResolver):
            조건 식별자를 실행 플러그인으로 변환하는 리졸버입니다.
        real_order_executor (RealOrderExecutor):
            주문 결과를 커뮤니티로 안내하는 실행 브리지입니다.
    """

    def __init__(self, plugin_resolver: PluginResolver):
        """Initialize the executor with a plugin resolver dependency.

        EN:
            Stores the resolver and prepares a dedicated real order executor
            instance for downstream notifications.

        KR:
            리졸버를 보관하고, 커뮤니티 알림을 위한 전용 실거래 실행기 인스턴스를
            준비합니다.

        Args:
            plugin_resolver (PluginResolver):
                EN: Dependency that resolves plugin identifiers to
                concrete classes.
                KR: 플러그인 식별자를 구체 클래스에 매핑하는 의존성입니다.

        Returns:
            None:
                EN: Constructor performs side effects only.
                KR: 생성자는 부수 효과만 수행하고 값을 반환하지 않습니다.
        """

        # EN: Resolver used to look up condition classes by identifier.
        # KR: 조건 클래스를 식별자로 조회하기 위한 리졸버입니다.
        self.plugin_resolver = plugin_resolver
        # EN: Executor forwarding order payloads to community callbacks.
        # KR: 주문 페이로드를 커뮤니티 콜백으로 전달하는 실행기입니다.
        self.real_order_executor = RealOrderExecutor()

    def _symbol_label(self, symbol: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures, HeldSymbol, NonTradedSymbol]) -> str:
        """Format a human-readable label for diverse symbol payloads.

        EN:
            Consolidates multiple symbol representations into a consistent
            `EXCHANGE:CODE` string, falling back to the default string form.

        KR:
            다양한 심볼 표현을 `거래소:코드` 문자열로 통일하며, 데이터가 없으면
            기본 문자열 표현으로 대체합니다.

        Args:
            symbol (Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures, HeldSymbol, NonTradedSymbol]):
                EN: Symbol dictionary or domain object describing a
                tradable instrument.
                KR: 거래 가능 종목을 설명하는 심볼 딕셔너리 또는 도메인 객체입니다.

        Returns:
            str:
                EN: Normalized display label combining exchange and code.
                KR: 거래소와 코드를 결합한 정규화된 표시 문자열입니다.
        """
        if isinstance(symbol, dict):
            exch = symbol.get("exchcd") or symbol.get("OrdMktCode") or symbol.get("ExchCode") or symbol.get("OrdMktCodeVal") or "?"
            code = symbol.get("symbol") or symbol.get("ShtnIsuNo") or symbol.get("IsuNo") or symbol.get("IsuCodeVal") or symbol.get("IsuCode") or "?"
            return f"{exch}:{code}"
        return str(symbol)

    def _field_icon(self, field: str) -> str:
        """Return an emoji icon representing the order action type.

        EN:
            Maps `new`, `modify`, and `cancel` operations to green, yellow, and
            red indicators to highlight log messages.

        KR:
            로그 메시지를 강조하기 위해 `new`, `modify`, `cancel` 작업을 각각 초록,
            노랑, 빨간 이모지로 매핑합니다.

        Args:
            field (str):
                EN: Order action identifier, usually `new`, `modify`, or
                `cancel`.
                KR: 일반적으로 `new`, `modify`, `cancel` 값을 갖는 주문 작업
                식별자입니다.

        Returns:
            str:
                EN: Emoji icon string suitable for logging.
                KR: 로깅에 사용되는 이모지 문자열입니다.
        """
        return {"new": "🟢", "modify": "🟡", "cancel": "🔴"}.get(field, "✅")

    def _field_label(self, field: str) -> str:
        """Translate an order action into a localized label.

        EN:
            Provides human-readable Korean labels to pair with order actions in
            log statements.

        KR:
            로그 문장에 사용할 주문 작업의 한글 레이블을 제공합니다.

        Args:
            field (str):
                EN: Order action identifier.
                KR: 주문 작업 식별자입니다.

        Returns:
            str:
                EN: Localized order action label.
                KR: 주문 작업을 설명하는 한글 레이블입니다.
        """
        return {"new": "신규", "modify": "정정", "cancel": "취소"}.get(field, "처리")

    def _product_label(self, product: str) -> str:
        """Convert a product key into a localized product label.

        EN:
            Distinguishes between overseas stock and futures when logging.

        KR:
            로깅 시 해외 주식과 선물을 구분하는 한글 레이블을 제공합니다.

        Args:
            product (str):
                EN: Product identifier from the system config.
                KR: 시스템 구성에 정의된 상품 식별자입니다.

        Returns:
            str:
                EN: Localized product label.
                KR: 상품을 표현하는 한글 레이블입니다.
        """
        return {"overseas_stock": "해외주식", "overseas_futures": "해외선물"}.get(product, "해외주식")

    def _normalize_futures_side(self, value: Optional[Union[str, int]]) -> Optional[str]:
        """Normalize futures side representations to `long` or `short`."""
        if value is None:
            return None

        text = str(value).strip().lower()
        if text in {"2", "buy", "long", "b"}:
            return "long"
        if text in {"1", "sell", "short", "s"}:
            return "short"
        return None

    def _strategy_position_side(self, symbol: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]) -> Optional[str]:
        """Extract normalized side information from strategy symbols."""
        candidate = None

        if isinstance(symbol, dict) or hasattr(symbol, "get"):
            getter = symbol.get  # type: ignore[attr-defined]
            candidate = (
                getter("position_side")
                or getter("positionSide")
                or getter("bns_tp_code")
                or getter("BnsTpCode")
            )

        if candidate is None:
            candidate = (
                getattr(symbol, "position_side", None)
                or getattr(symbol, "positionSide", None)
                or getattr(symbol, "bns_tp_code", None)
                or getattr(symbol, "BnsTpCode", None)
            )

        return self._normalize_futures_side(candidate)

    async def new_order_execute(
        self,
        system: SystemType,
        res_symbols_from_conditions: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
        new_order: OrderStrategyType,
        order_id: str,
        order_types: List[OrderType]
    ) -> None:
        """Run the plugin pipeline for new order submissions.

        EN:
            Filters symbols returned from condition plugins, prepares deposit
            state, resolves community plugins, and executes applicable orders
            while emitting rich logs.

        KR:
            조건 플러그인이 반환한 종목을 필터링하고 예수금을 준비한 뒤, 커뮤니티
            플러그인을 해석하여 해당되는 주문을 실행하고 상세 로그를 남깁니다.

        Args:
            system (SystemType):
                EN: Complete trading system configuration including
                securities context.
                KR: 증권 컨텍스트를 포함한 전체 거래 시스템 구성입니다.
            res_symbols_from_conditions (List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]):
                EN: Symbols that passed strategy condition evaluation.
                KR: 전략 조건 평가를 통과한 종목 목록입니다.
            new_order (OrderStrategyType):
                EN: Declarative settings describing how to submit new
                orders.
                KR: 신규 주문 제출 방법을 설명하는 선언적 설정입니다.
            order_id (str):
                EN: Friendly identifier used for grouping log messages.
                KR: 로그 메시지를 그룹화하는 데 사용하는 식별자입니다.
            order_types (List[OrderType]):
                EN: Order action flags controlling which flows execute
                (e.g., `new_buy`).
                KR: 실행할 흐름을 제어하는 주문 작업 플래그 목록입니다
                (예: `new_buy`).

        Returns:
            None:
                EN: Completes after submitting all applicable orders.
                KR: 적용 가능한 주문을 모두 제출한 뒤 값을 반환하지 않습니다.

        Raises:
            exceptions.NotExistCompanyException:
                EN: Propagated when the configured securities company is
                unsupported.
                KR: 구성된 증권사가 지원되지 않을 때 전파됩니다.
            exceptions.OrderException:
                EN: Propagated from downstream order execution failures.
                KR: 하위 주문 실행 실패가 발생하면 전파됩니다.
        """
        order_logger.info(
            f"🛒 {order_id}: 신규 주문 진행을 시작합니다 (전략 종목 {len(res_symbols_from_conditions)}개)"
        )
        dps = await self._setup_dps(system, new_order)

        # 필터링, 보유, 미체결 종목들 가져오기
        non_held_symbols, held_symbols, non_trade_symbols = await self._block_duplicate_symbols(system, res_symbols_from_conditions)
        should_block_duplicates = new_order.get("block_duplicate_buy", True)
        product_key = system.get("securities", {}).get("product", "overseas_stock") or "overseas_stock"
        if product_key == "overseas_futures":
            has_directional_new_orders = any(flag in {"new_buy", "new_sell"} for flag in (order_types or []))
        else:
            has_directional_new_orders = "new_buy" in (order_types or [])

        if should_block_duplicates and has_directional_new_orders:
            res_symbols_from_conditions[:] = non_held_symbols

        if not res_symbols_from_conditions:
            # order_logger.warning(f"No symbols to buy. order_id: {order_id}")
            order_logger.info(f"⚪️ {order_id}: 중복 필터링 이후 실행할 종목이 없어 신규 주문을 종료합니다")
            return

        purchase_symbols, community_instance = await self.plugin_resolver.resolve_buysell_community(
            system_id=system.get("settings", {}).get("system_id", None),
            trade=new_order,
            available_symbols=res_symbols_from_conditions,
            held_symbols=held_symbols,
            non_trade_symbols=non_trade_symbols,
            dps=dps,
        )

        if not purchase_symbols:
            order_logger.warning(f"❌ {order_id}: 조건을 통과한 종목이 없어 신규 주문을 중단합니다")
            return

        order_logger.info(
            f"🎯 {order_id}: 플러그인이 실행 가능한 종목 {len(purchase_symbols)}개를 반환했습니다"
        )

        await self._execute_orders(
            system=system,
            symbols=purchase_symbols,
            community_instance=community_instance,
            field="new",
            order_id=order_id
        )

    async def _block_duplicate_symbols(
        self,
        system: SystemType,
        res_symbols_from_conditions: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
    ):
        """Filter out duplicate or already-held symbols before ordering.

        EN:
            Consults LS account APIs to gather current holdings and pending
            orders, excluding duplicates when block rules are enabled, and
            returns structured lists separating tradable, held, and pending
            symbols.

        KR:
            LS 계좌 API를 조회해 현재 보유 및 미체결 종목을 수집하고, 중복 차단
            규칙이 활성화된 경우 전략 종목에서 제거한 뒤, 거래 가능/보유/미체결
            목록을 구분해 반환합니다.

        Args:
            system (SystemType):
                EN: System configuration containing securities metadata
                and credentials.
                KR: 증권 메타데이터와 자격 정보를 포함한 시스템 구성입니다.
            res_symbols_from_conditions (List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]):
                EN: Symbols produced by condition plugins prior to
                filtering.
                KR: 필터링 전에 조건 플러그인이 생성한 종목 목록입니다.

        Returns:
            Tuple[List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]], List[HeldSymbol], List[NonTradedSymbol]]:
                EN: Triple containing tradable symbols, current holdings,
                and pending orders.
                KR: 거래 가능 종목, 현재 보유 종목, 미체결 주문으로 구성된
                튜플입니다.

        Raises:
            exceptions.OrderExecutionException:
                EN: Emitted via listener when remote queries fail.
                KR: 원격 조회 실패 시 리스너를 통해 발생하는 예외입니다.
        """

        held_symbols: List[HeldSymbol] = []
        non_trade_symbols: List[NonTradedSymbol] = []

        company = system.get("securities", {}).get("company", "")
        product = system.get("securities", {}).get("product", "")
        paper_trading = bool(system.get("securities", {}).get("paper_trading", False))

        if company == "ls" and product == "overseas_stock":
            ls = LS.get_instance()
            if getattr(ls, "token_manager", None) is not None:
                ls.token_manager.configure_trading_mode(paper_trading)
            if not ls.is_logged_in():
                await ls.async_login(
                        appkey=system.get("securities", {}).get("appkey", None),
                        appsecretkey=system.get("securities", {}).get("appsecretkey", None),
                        paper_trading=paper_trading,
                    )

            # 보유잔고에서 확인하기
            acc_result = await ls.overseas_stock().accno().cosoq00201(
                    body=COSOQ00201.COSOQ00201InBlock1(
                        # BaseDt=datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d")
                    )
                ).req_async()

            held_isus = set()
            for blk in acc_result.block4:
                shtn_isu_no = blk.ShtnIsuNo
                if shtn_isu_no is not None:
                    held_isus.add(str(shtn_isu_no).strip())

                held_symbols.append(
                    HeldSymbolOverseasStock(
                        CrcyCode=blk.CrcyCode,
                        ShtnIsuNo=shtn_isu_no,
                        AstkBalQty=blk.AstkBalQty,
                        AstkSellAbleQty=blk.AstkSellAbleQty,
                        PnlRat=blk.PnlRat,
                        BaseXchrat=blk.BaseXchrat,
                        PchsAmt=blk.PchsAmt,
                        FcurrMktCode=blk.FcurrMktCode
                    )
                )

            # res_symbols_from_conditions에서
            exchcds: set[str] = set()
            for symbol in res_symbols_from_conditions:
                exchcds.add(symbol.get("exchcd"))

            for exchcd in exchcds:
                # 미체결에서도 확인하기
                not_acc_result = await ls.overseas_stock().accno().cosaq00102(
                    body=COSAQ00102.COSAQ00102InBlock1(
                        QryTpCode="1",
                        BkseqTpCode="1",
                        OrdMktCode=exchcd,
                        BnsTpCode="0",
                        SrtOrdNo="999999999",
                        OrdDt=datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d"),
                        ExecYn="2",
                        CrcyCode="USD",
                        ThdayBnsAppYn="0",
                        LoanBalHldYn="0"
                    )
                ).req_async()

                if not_acc_result.block3:
                    for blk in not_acc_result.block3:
                        isu_no = blk.IsuNo
                        if isu_no is not None:
                            held_isus.add(str(isu_no).strip())

                        non_trade_symbols.append(
                            NonTradedSymbolOverseasStock(
                                OrdTime=blk.OrdTime,
                                OrdNo=blk.OrdNo,
                                OrgOrdNo=blk.OrgOrdNo,
                                ShtnIsuNo=blk.ShtnIsuNo,
                                MrcAbleQty=blk.MrcAbleQty,
                                OrdQty=blk.OrdQty,
                                OvrsOrdPrc=blk.OvrsOrdPrc,
                                OrdprcPtnCode=blk.OrdprcPtnCode,
                                OrdPtnCode=blk.OrdPtnCode,
                                MrcTpCode=blk.MrcTpCode,
                                OrdMktCode=blk.OrdMktCode,
                                UnercQty=blk.UnercQty,
                                CnfQty=blk.CnfQty,
                                CrcyCode=blk.CrcyCode,
                                RegMktCode=blk.RegMktCode,
                                IsuNo=blk.IsuNo,
                                BnsTpCode=blk.BnsTpCode
                            )
                        )

            if held_isus:
                non_held_symbols = []
                for m_symbol in res_symbols_from_conditions:
                    m_isu_no = m_symbol.get("symbol")

                    if m_isu_no is None or str(m_isu_no).strip() not in held_isus:
                        non_held_symbols.append(m_symbol)
                return non_held_symbols, held_symbols, non_trade_symbols

            return res_symbols_from_conditions, held_symbols, non_trade_symbols

        if company == "ls" and product == "overseas_futures":
            ls = LS.get_instance()
            if getattr(ls, "token_manager", None) is not None:
                ls.token_manager.configure_trading_mode(paper_trading)
            if not ls.is_logged_in():
                await ls.async_login(
                    appkey=system.get("securities", {}).get("appkey", None),
                    appsecretkey=system.get("securities", {}).get("appsecretkey", None),
                    paper_trading=paper_trading,
                )

            ny_time = datetime.now(ZoneInfo("America/New_York"))
            query_date = ny_time.strftime("%Y%m%d")

            held_positions: Dict[str, Set[str]] = {}

            def register_position(symbol_code: Optional[str], side_value: Optional[Union[str, int]]) -> None:
                code = str(symbol_code or "").strip()
                normalized_side = self._normalize_futures_side(side_value)
                if not code:
                    return

                bucket = held_positions.setdefault(code, set())
                if normalized_side is None:
                    # Keep legacy behavior for symbols without directional data by tagging a wildcard entry.
                    bucket.add("__any__")
                else:
                    bucket.discard("__any__")
                    bucket.add(normalized_side)

            try:

                # 잔고 보유종목 조회
                balance_resp = await ls.overseas_futureoption().accno().CIDBQ01500(
                    body=CIDBQ01500.CIDBQ01500InBlock1(
                        RecCnt=1,
                        QryDt=query_date,
                        BalTpCode="2",
                    )
                ).req_async()
            except Exception as exc:
                symbol_logger.exception(f"해외선물 잔고 조회에 실패했습니다: {exc}")
                pg_listener.emit_exception(
                    exceptions.OrderExecutionException(
                        message="해외선물 잔고 조회에 실패했습니다.",
                        data={"details": str(exc)},
                    )
                )
                balance_resp = None

            if balance_resp and getattr(balance_resp, "block2", None):
                for blk in balance_resp.block2:
                    symbol_code = str(getattr(blk, "IsuCodeVal", "") or "").strip()

                    # 해외선물 모의투자에서 지원 안 하는 종목일 수 있어서 확인하기
                    o3105_symbol = await ls.get_instance().overseas_futureoption().market().o3105(
                        body=o3105.O3105InBlock(
                            symbol=symbol_code
                        )
                    ).req_async()

                    if not o3105_symbol.block or not o3105_symbol.block.Symbol:
                        if ls.token_manager.paper_trading:
                            symbol_logger.warning(f"해외선물 잔고 종목 조회 중단: 종목코드 {symbol_code}는(은) 모의투자API에서 조회할 수 없는 종목입니다.")
                        symbol_logger.warning(f"해외선물 잔고 종목 조회 중단: 종목코드 {symbol_code}는(은) 지원되지 않는 종목입니다.")
                        continue

                    if symbol_code:
                        register_position(symbol_code, getattr(blk, "BnsTpCode", None))

                        def _clean_str(value):
                            if isinstance(value, str):
                                value = value.strip()
                            return value or None

                        def _clean_float(value):
                            if value in (None, ""):
                                return None
                            try:
                                return float(value)
                            except (TypeError, ValueError):
                                return None

                        entry_data = {
                            "IsuCodeVal": symbol_code,
                            "IsuNm": _clean_str(getattr(blk, "IsuNm", None)),
                            "BnsTpCode": _clean_str(getattr(blk, "BnsTpCode", None)),
                            "DueDt": _clean_str(getattr(blk, "DueDt", None)),
                            "CrcyCodeVal": _clean_str(getattr(blk, "CrcyCodeVal", None)),
                            "PosNo": _clean_str(getattr(blk, "PosNo", None)),
                        }

                        for field_name in (
                            "BalQty",
                            "OrdAbleAmt",
                            "OvrsDrvtNowPrc",
                            "AbrdFutsEvalPnlAmt",
                            "PchsPrc",
                            "MaintMgn",
                            "CsgnMgn",
                        ):
                            entry_data[field_name] = _clean_float(getattr(blk, field_name, None))

                        entry: HeldSymbolOverseasFutures = {
                            key: value for key, value in entry_data.items() if value is not None
                        }

                    held_symbols.append(entry)

            try:
                cidbq01800_resp = await ls.overseas_futureoption().accno().CIDBQ01800(
                    body=CIDBQ01800.CIDBQ01800InBlock1(
                        IsuCodeVal="",
                        OrdDt="",
                        OrdStatCode="2",
                    )
                ).req_async()
            except Exception as exc:
                order_logger.exception(f"해외선물 미체결 주문 조회에 실패했습니다 ({symbol_code}): {exc}")
                pg_listener.emit_exception(
                    exceptions.OrderExecutionException(
                        message="해외선물 미체결 주문 조회에 실패했습니다.",
                        data={"symbol": symbol_code, "details": str(exc)},
                    )
                )

            if cidbq01800_resp and getattr(cidbq01800_resp, "block2", None):
                for blk in cidbq01800_resp.block2:
                    try:
                        pending_qty = int(getattr(blk, "UnercQty", 0) or 0)
                    except (TypeError, ValueError):
                        pending_qty = 0

                    if pending_qty <= 0:
                        continue

                    symbol_code = blk.IsuCodeVal

                    # 해외선물 모의투자에서 지원 안 하는 종목일 수 있어서 확인하기
                    exist_symbol = await ls.get_instance().overseas_futureoption().market().o3105(
                        body=o3105.O3105InBlock(
                            symbol=symbol_code
                        )
                    ).req_async()

                    if not exist_symbol.block or not exist_symbol.block.Symbol:
                        if ls.token_manager.paper_trading:
                            symbol_logger.warning(f"해외선물 미체결 종목 조회 중단: 종목코드 {symbol_code}는(은) 모의투자API에서 조회할 수 없는 종목입니다.")
                        symbol_logger.warning(f"해외선물 미체결 종목 조회 중단: 종목코드 {symbol_code}는(은) 지원되지 않는 종목입니다.")
                        continue

                    def _attr_str(name: str) -> Optional[str]:
                        raw = getattr(blk, name, None)
                        if raw is None:
                            return None
                        raw_str = str(raw).strip()
                        return raw_str or None

                    def _attr_int(name: str) -> Optional[int]:
                        raw = getattr(blk, name, None)
                        if raw in (None, ""):
                            return None
                        try:
                            return int(raw)
                        except (TypeError, ValueError):
                            return None

                    def _attr_float(name: str) -> Optional[float]:
                        raw = getattr(blk, name, None)
                        if raw in (None, ""):
                            return None
                        try:
                            return float(raw)
                        except (TypeError, ValueError):
                            return None

                    non_trade_symbol: NonTradedSymbolOverseasFutures = {
                        key: value
                        for key, value in {
                            "OvrsFutsOrdNo": _attr_str("OvrsFutsOrdNo"),
                            "OvrsFutsOrgOrdNo": _attr_str("OvrsFutsOrgOrdNo"),
                            "IsuCodeVal": _attr_str("IsuCodeVal"),
                            "OrdDt": _attr_str("OrdDt"),
                            "OrdTime": _attr_str("OrdTime"),
                            "BnsTpCode": _attr_str("BnsTpCode"),
                            "FutsOrdStatCode": _attr_str("FutsOrdStatCode"),
                            "FutsOrdTpCode": _attr_str("FutsOrdTpCode"),
                            "AbrdFutsOrdPtnCode": _attr_str("AbrdFutsOrdPtnCode"),
                            "IsuNm": _attr_str("IsuNm"),
                            "UnercQty": pending_qty,
                            "OrdQty": _attr_int("OrdQty"),
                            "ExecQty": _attr_int("ExecQty"),
                            "OvrsDrvtOrdPrc": _attr_float("OvrsDrvtOrdPrc"),
                            "FcmOrdNo": _attr_str("FcmOrdNo"),
                            "FcmAcntNo": _attr_str("FcmAcntNo"),
                            "ExecBnsTpCode": _attr_str("ExecBnsTpCode"),
                            "CvrgYn": _attr_str("CvrgYn"),
                        }.items()
                        if value is not None
                    }

                    non_trade_symbols.append(non_trade_symbol)
                    register_position(symbol_code, _attr_str("BnsTpCode") or _attr_str("ExecBnsTpCode"))

            if held_positions:
                non_held_symbols = []
                for m_symbol in res_symbols_from_conditions:
                    candidate_code = None
                    if isinstance(m_symbol, dict):
                        candidate_code = m_symbol.get("symbol") or m_symbol.get("symbol_code")
                    elif hasattr(m_symbol, "get"):
                        candidate_code = m_symbol.get("symbol")
                    elif hasattr(m_symbol, "symbol"):
                        candidate_code = getattr(m_symbol, "symbol")

                    m_symbol_code = str(candidate_code or "").strip()
                    blocked_sides = held_positions.get(m_symbol_code, set()) if m_symbol_code else set()
                    strategy_side = self._strategy_position_side(m_symbol)

                    if not m_symbol_code:
                        non_held_symbols.append(m_symbol)
                        continue

                    if "__any__" in blocked_sides:
                        # Legacy fallback: once wildcard is set we treat the entire symbol as blocked.
                        continue

                    if not blocked_sides:
                        non_held_symbols.append(m_symbol)
                        continue

                    if strategy_side is None:
                        continue

                    if strategy_side in blocked_sides:
                        continue

                    non_held_symbols.append(m_symbol)

                return non_held_symbols, held_symbols, non_trade_symbols

            return res_symbols_from_conditions, held_symbols, non_trade_symbols

        return res_symbols_from_conditions, held_symbols, non_trade_symbols

    async def modify_order_execute(
        self,
        system: SystemType,
        symbols_from_strategy: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
        modify_order: OrderStrategyType,
        order_id: str,
    ):
        order_logger.debug(
            f"🛠️ 정정 주문 종목 {len(symbols_from_strategy)}개에 대해서 {order_id} 계산을 시작합니다."
        )
        dps = await self._setup_dps(system, modify_order)

        # 전략 조건 필터링 된 종목들, 보유, 미체결 종목들 가져오기
        non_held_symbols, held_symbols, non_trade_symbols = await self._block_duplicate_symbols(system, symbols_from_strategy)

        # 미체결 종목 없으면 넘기기
        if not non_trade_symbols:
            order_logger.warning(f" 정정할 미체결 종목이 없어서 {order_id}의 계산을 강제 종료합니다.")
            return

        # 미체결 종목 전략 계산으로
        modify_symbols, community_instance = await self.plugin_resolver.resolve_buysell_community(
            system_id=system.get("settings", {}).get("system_id", None),
            trade=modify_order,
            available_symbols=non_held_symbols,
            held_symbols=held_symbols,
            non_trade_symbols=non_trade_symbols,
            dps=dps,
        )

        if not modify_symbols:
            order_logger.warning(f"❌ {order_id}: 조건을 통과한 종목이 없어 정정 주문을 중단합니다")
            return

        order_logger.info(
            f"🟡 {order_id}: 플러그인이 정정 대상 {len(modify_symbols)}개 종목을 반환했습니다"
        )

        await self._execute_orders(
            system=system,
            symbols=modify_symbols,
            community_instance=community_instance,
            field="modify",
            order_id=order_id
        )

    async def cancel_order_execute(
        self,
        system: SystemType,
        symbols_from_strategy: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
        cancel_order: OrderStrategyType,
        order_id: str,
    ):
        order_logger.info(
            f"🗑️ {order_id}: 취소 주문 흐름을 시작합니다 (전략 종목 {len(symbols_from_strategy)}개)"
        )
        dps = await self._setup_dps(system, cancel_order)

        # 필터링, 보유, 미체결 종목들 가져오기
        non_held_symbols, held_symbols, non_trade_symbols = await self._block_duplicate_symbols(system, symbols_from_strategy)

        # 미체결 종목 없으면 넘기기
        if not non_trade_symbols:
            order_logger.warning(f"⚠️ {order_id}: 취소할 미체결 종목이 없어 흐름을 종료합니다")
            return

        # 미체결 종목 전략 계산으로
        cancel_symbols, community_instance = await self.plugin_resolver.resolve_buysell_community(
            system_id=system.get("settings", {}).get("system_id", None),
            trade=cancel_order,
            available_symbols=non_held_symbols,
            held_symbols=held_symbols,
            non_trade_symbols=non_trade_symbols,
            dps=dps,
        )

        await self._execute_orders(
            system=system,
            symbols=cancel_symbols,
            community_instance=community_instance,
            field="cancel",
            order_id=order_id
        )

        if cancel_symbols:
            order_logger.info(
                f"🔴 {order_id}: 플러그인이 취소 대상 {len(cancel_symbols)}개 종목을 반환했습니다"
            )
        else:
            order_logger.warning(
                f"❌ {order_id}: 취소 조건을 만족하는 종목이 없습니다"
            )

    async def _build_order_function(
        self,
        system: SystemType,
        symbol: Union[
            BaseNewOrderOverseasStockResponseType,
            BaseModifyOrderOverseasStockResponseType,
            BaseCancelOrderOverseasStockResponseType,
            BaseNewOrderOverseasFuturesResponseType,
            BaseModifyOrderOverseasFuturesResponseType,
            BaseCancelOrderOverseasFuturesResponseType,
        ],
        field: Literal["new", "modify", "cancel"]
    ):
        """
        Function that performs the actual order placement.
        """
        company = system.get("securities", {}).get("company", None)
        product = system.get("securities", {}).get("product", None)

        if company is None or not product:
            raise exceptions.NotExistCompanyException(
                message="No securities company or product configured in system."
            )

        if company != "ls":
            raise exceptions.NotExistCompanyException(
                message="Unsupported securities company configured in system."
            )

        ls = LS.get_instance()
        result = None

        if product == "overseas_stock":
            ord_ptn = symbol.get("ord_ptn_code")

            if ord_ptn in ("01", "02", "08"):
                result = await ls.overseas_stock().order().cosat00301(
                    body=COSAT00301.COSAT00301InBlock1(
                        OrdPtnCode=ord_ptn,
                        OrgOrdNo=symbol.get("org_ord_no", None),
                        OrdMktCode=symbol.get("ord_mkt_code"),
                        IsuNo=symbol.get("shtn_isu_no"),
                        OrdQty=symbol.get("ord_qty"),
                        OvrsOrdPrc=symbol.get("ovrs_ord_prc"),
                        OrdprcPtnCode=symbol.get("ordprc_ptn_code"),
                    )
                ).req_async()
            elif ord_ptn in ("07",):
                result = await ls.overseas_stock().order().cosat00311(
                    body=COSAT00311.COSAT00311InBlock1(
                        OrdPtnCode=ord_ptn,
                        OrgOrdNo=int(symbol.get("org_ord_no")),
                        OrdMktCode=symbol.get("ord_mkt_code"),
                        IsuNo=symbol.get("shtn_isu_no"),
                        OrdQty=symbol.get("ord_qty"),
                        OvrsOrdPrc=symbol.get("ovrs_ord_prc"),
                        OrdprcPtnCode=symbol.get("ordprc_ptn_code"),
                    )
                ).req_async()

        elif product == "overseas_futures":
            today = datetime.now().strftime("%Y%m%d")
            side_code = str(symbol.get("bns_tp_code", "2")).strip() or "2"

            if field == "new":
                result = await ls.overseas_futureoption().order().CIDBT00100(
                    body=CIDBT00100.CIDBT00100InBlock1(
                        OrdDt=symbol.get("ord_dt", today),
                        IsuCodeVal=symbol.get("isu_code_val"),
                        FutsOrdTpCode=symbol.get("futs_ord_tp_code", "1"),
                        BnsTpCode=side_code,
                        AbrdFutsOrdPtnCode=symbol.get("abrd_futs_ord_ptn_code", "2"),
                        CrcyCode=symbol.get("crcy_code", ""),
                        OvrsDrvtOrdPrc=float(symbol.get("ovrs_drvt_ord_prc", 0.0) or 0.0),
                        CndiOrdPrc=float(symbol.get("cndi_ord_prc", 0.0) or 0.0),
                        OrdQty=int(symbol.get("ord_qty", 1) or 1),
                        PrdtCode=symbol.get("prdt_code", ""),
                        DueYymm=symbol.get("due_yymm", ""),
                        ExchCode=symbol.get("exch_code", ""),
                    )
                ).req_async()

            elif field == "modify":
                result = await ls.overseas_futureoption().order().CIDBT00900(
                    body=CIDBT00900.CIDBT00900InBlock1(
                        OrdDt=symbol.get("ord_dt", today),
                        OvrsFutsOrgOrdNo=symbol.get("ovrs_futs_org_ord_no"),
                        IsuCodeVal=symbol.get("isu_code_val"),
                        FutsOrdTpCode=symbol.get("futs_ord_tp_code", "2"),
                        BnsTpCode=side_code,
                        FutsOrdPtnCode=symbol.get("futs_ord_ptn_code", "2"),
                        CrcyCodeVal=symbol.get("crcy_code_val", ""),
                        OvrsDrvtOrdPrc=float(symbol.get("ovrs_drvt_ord_prc", 0.0) or 0.0),
                        CndiOrdPrc=float(symbol.get("cndi_ord_prc", 0.0) or 0.0),
                        OrdQty=int(symbol.get("ord_qty", 1) or 1),
                        OvrsDrvtPrdtCode=symbol.get("ovrs_drvt_prdt_code", ""),
                        DueYymm=symbol.get("due_yymm", ""),
                        ExchCode=symbol.get("exch_code", ""),
                    )
                ).req_async()

            elif field == "cancel":
                result = await ls.overseas_futureoption().order().CIDBT01000(
                    body=CIDBT01000.CIDBT01000InBlock1(
                        OrdDt=symbol.get("ord_dt", today),
                        IsuCodeVal=symbol.get("isu_code_val"),
                        OvrsFutsOrgOrdNo=symbol.get("ovrs_futs_org_ord_no"),
                        FutsOrdTpCode=symbol.get("futs_ord_tp_code", "3"),
                        PrdtTpCode=symbol.get("prdt_tp_code", " "),
                        ExchCode=symbol.get("exch_code", " "),
                    )
                ).req_async()
            else:
                raise exceptions.OrderException(message=f"Unsupported order field '{field}' for futures.")

        else:
            raise exceptions.NotExistCompanyException(
                message=f"Unsupported product '{product}' configured in system."
            )

        if result is None:
            raise exceptions.OrderException(message="Failed to execute order: no response received.")

        side_code = str(symbol.get("bns_tp_code", "2")).strip() or "2"
        if field == "new":
            order_type = "submitted_new_buy" if side_code == "2" else "submitted_new_sell"
        elif field == "modify":
            order_type = "modify_buy" if side_code == "2" else "modify_sell"
        elif field == "cancel":
            order_type = "cancel_buy" if side_code == "2" else "cancel_sell"
        else:
            order_type = "submitted_new_buy"

        pg_listener.emit_real_order({
            "order_type": order_type,
            "message": result.rsp_msg,
            "response": result,
        })

        if result.error_msg:
            order_logger.error(f"❗️ 주문 전송에 실패했습니다: {result.error_msg}")
            raise exceptions.OrderException(
                message=f"Order placement failed: {result.error_msg}"
            )
        
        if result.block1 is None:
            order_logger.error(f"❗️ 주문 접수에 실패했습니다: {result.status_code} - {result.rsp_msg}")
            raise exceptions.OrderException(
                message=f"Order placement failed: {result.status_code} - {result.rsp_msg}"
            )

        return result

    async def _setup_dps(
        self,
        system: SystemType,
        trade: OrderStrategyType
    ) -> List[DpsTyped]:
        """Setup DPS (deposit) information for trading."""

        available_balance = float(trade.get("available_balance", 0.0))
        dps: List[DpsTyped] = [
            {
                "deposit": available_balance,
                "orderable_amount": available_balance,
                "currency": "USD"
            }
        ]
        is_ls = system.get("securities", {}).get("company", None) == "ls"
        product = system.get("securities", {}).get("product", "overseas_stock")

        if available_balance == 0.0 and is_ls:
            if product == "overseas_stock":
                cosoq02701 = await LS.get_instance().overseas_stock().accno().cosoq02701(
                    body=COSOQ02701.COSOQ02701InBlock1(
                        RecCnt=1,
                        CrcyCode="USD",
                    ),
                ).req_async()

                if cosoq02701 and getattr(cosoq02701, "block3", None):
                    dps[0]["deposit"] = cosoq02701.block3[0].FcurrDps
                    dps[0]["orderable_amount"] = cosoq02701.block3[0].FcurrOrdAbleAmt

            elif product == "overseas_futures":
                cidbq03000 = await LS.get_instance().overseas_futureoption().accno().CIDBQ03000(
                    body=CIDBQ03000.CIDBQ03000InBlock1(
                        AcntTpCode="1",
                        TrdDt="20251031",
                    )
                ).req_async()

                if cidbq03000 and getattr(cidbq03000, "block2", None):

                    block = None
                    for cid in cidbq03000.block2:
                        if cid.CrcyObjCode == "USD":
                            block = cid
                            break
                    dps[0]["deposit"] = block.OvrsFutsDps if block else 0.0
                    dps[0]["orderable_amount"] = block.AbrdFutsOrdAbleAmt if block else 0.0

        order_logger.debug(
            f"현재 예수금은 ${dps[0]['deposit']}이고 주문가능금액은 ${dps[0]['orderable_amount']}입니다."
        )
        return dps

    async def _execute_orders(
        self,
        system: SystemType,
        symbols: List[Union[
            BaseNewOrderOverseasStockResponseType,
            BaseModifyOrderOverseasStockResponseType,
            BaseCancelOrderOverseasStockResponseType,
            BaseNewOrderOverseasFuturesResponseType,
            BaseModifyOrderOverseasFuturesResponseType,
            BaseCancelOrderOverseasFuturesResponseType,
        ]],
        community_instance: Optional[Union[BaseOrderOverseasStock, BaseOrderOverseasFutures]],
        field: Literal["new", "modify", "cancel"],
        order_id: str,
    ) -> None:
        """Execute trades for the given symbols."""
        for symbol in symbols:

            if symbol.get("success") is False:
                order_logger.debug(
                    f"{order_id}: 조건을 통과하지 못한 종목 {self._symbol_label(symbol)}을(를) 건너뜁니다"
                )
                continue

            result = await self._build_order_function(system, symbol, field)

            ord_no = None
            if result is not None:
                block2 = getattr(result, "block2", None)
                ord_val = None
                if block2 is not None:
                    ord_val = getattr(block2, "OrdNo", None)
                    if ord_val is None:
                        ord_val = getattr(block2, "OvrsFutsOrdNo", None)
                ord_no = str(ord_val) if ord_val is not None else None

            await self.real_order_executor.send_data_community_instance(
                ordNo=ord_no,
                community_instance=community_instance
            )

            if result and result.block1 is None:
                continue

            product_key = system.get("securities", {}).get("product", "overseas_stock") or "overseas_stock"
            icon = self._field_icon(field)
            field_label = self._field_label(field)
            product_label = self._product_label(product_key)
            ord_display = ord_no or "-"

            order_logger.info(
                f"{icon} {order_id}: {product_label} {field_label} 주문 완료 ({self._symbol_label(symbol)}, 주문번호={ord_display})"
            )
