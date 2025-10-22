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

from typing import TYPE_CHECKING, List, Literal, Optional, TypedDict, Union
from zoneinfo import ZoneInfo
from programgarden_core import (
    SystemType, OrderStrategyType,
    pg_logger, exceptions, HeldSymbol,
    HeldSymbolOverseasStock,
    HeldSymbolOverseasFutures,
    NonTradedSymbol,
    NonTradedSymbolOverseasStock,
    NonTradedSymbolOverseasFutures,
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    OrderType
)
from programgarden_core import (
    BaseOrderOverseasStock,
    BaseOrderOverseasFutures,
    BaseNewOrderOverseasStockResponseType,
    BaseModifyOrderOverseasStockResponseType,
    BaseCancelOrderOverseasStockResponseType,
    BaseNewOrderOverseasFuturesResponseType,
    BaseModifyOrderOverseasFutureResponseType,
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
)

from programgarden.pg_listener import pg_listener
from programgarden.real_order_executor import RealOrderExecutor
from datetime import datetime

if TYPE_CHECKING:
    from .plugin_resolver import PluginResolver


class DpsTyped(TypedDict):
    fcurr_dps: float
    """예수금"""
    fcurr_ord_able_amt: float
    """주문 가능 금액"""


class BuySellExecutor:
    """Orchestrates execution of buy/sell condition plugins.

    The executor requires a `PluginResolver` which maps condition
    identifiers to concrete classes. It does not implement trading
    strategies itself; instead it prepares and runs plugin instances
    and returns whatever those plugins produce.

    Contract (high level):
        - Input: a `system` config (dict-like `SystemType`) and a list of
            `SymbolInfoOverseasStock` or `SymbolInfoOverseasFutures` items describing available symbols.
    - Output: a list of plugin execution responses (or None on error).
    - Error modes: missing plugin, incorrect plugin type, runtime
      exceptions inside plugin code. Errors are logged and result in
      a None return value from the internal executor.
    """

    def __init__(self, plugin_resolver: PluginResolver):
        # PluginResolver instance used to look up condition classes by id
        self.plugin_resolver = plugin_resolver
        self.real_order_executor = RealOrderExecutor()

    def _symbol_label(self, symbol: Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures, HeldSymbol, NonTradedSymbol]) -> str:
        if isinstance(symbol, dict):
            exch = symbol.get("exchcd") or symbol.get("OrdMktCode") or symbol.get("ExchCode") or symbol.get("OrdMktCodeVal") or "?"
            code = symbol.get("symbol") or symbol.get("ShtnIsuNo") or symbol.get("IsuNo") or symbol.get("IsuCodeVal") or symbol.get("IsuCode") or "?"
            return f"{exch}:{code}"
        return str(symbol)

    def _field_icon(self, field: str) -> str:
        return {"new": "🟢", "modify": "🟡", "cancel": "🔴"}.get(field, "✅")

    def _field_label(self, field: str) -> str:
        return {"new": "신규", "modify": "정정", "cancel": "취소"}.get(field, "처리")

    def _product_label(self, product: str) -> str:
        return {"overseas_stock": "해외주식", "overseas_futures": "해외선물"}.get(product, "해외주식")

    async def new_order_execute(
        self,
        system: SystemType,
        symbols_from_strategy: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
        new_order: OrderStrategyType,
        order_id: str,
        order_types: List[OrderType]
    ) -> None:
        """
        Execute a new order.
        Args:
            system (SystemType): The trading system configuration.
            symbols_from_strategy (list[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]): The list of symbols to trade.
            new_order (OrderStrategyType): The new order configuration.
            order_id (str): The unique identifier for the order.
            order_types (List[OrderType]): The types of orders to execute.
        """
        pg_logger.info(
            f"🛒 [ORDER] {order_id}: 신규 주문 진행을 시작합니다 (전략 종목 {len(symbols_from_strategy)}개)"
        )
        dps = await self._setup_dps(system, new_order)

        # 필터링, 보유, 미체결 종목들 가져오기
        non_held_symbols, held_symbols, non_trade_symbols = await self._block_duplicate_symbols(system, symbols_from_strategy)
        if new_order.get("block_duplicate_buy", True) and "new_buy" in order_types:
            symbols_from_strategy[:] = non_held_symbols

        if not symbols_from_strategy:
            # pg_logger.warning(f"No symbols to buy. order_id: {order_id}")
            pg_logger.info(f"⚪️ [ORDER] {order_id}: 중복 필터링 이후 실행할 종목이 없어 신규 주문을 종료합니다")
            return

        purchase_symbols, community_instance = await self.plugin_resolver.resolve_buysell_community(
            system_id=system.get("settings", {}).get("system_id", None),
            trade=new_order,
            symbols=symbols_from_strategy,
            held_symbols=held_symbols,
            non_trade_symbols=non_trade_symbols,
            dps=dps,
        )

        if not purchase_symbols:
            pg_logger.warning(f"❌ [ORDER] {order_id}: 조건을 통과한 종목이 없어 신규 주문을 중단합니다")
            return

        pg_logger.info(
            f"🎯 [ORDER] {order_id}: 플러그인이 실행 가능한 종목 {len(purchase_symbols)}개를 반환했습니다"
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
        symbols_from_strategy: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
    ):
        """
        Returns로는 중복 여부로 보유하지 않은 종목들과, 보유잔고 종목들과 미체결 종목들이 반환된다.
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

            # symbols_from_strategy에서
            exchcds: set[str] = set()
            for symbol in symbols_from_strategy:
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
                for m_symbol in symbols_from_strategy:
                    m_isu_no = m_symbol.get("symbol")

                    if m_isu_no is None or str(m_isu_no).strip() not in held_isus:
                        non_held_symbols.append(m_symbol)
                return non_held_symbols, held_symbols, non_trade_symbols

            return symbols_from_strategy, held_symbols, non_trade_symbols

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

            held_isus: set[str] = set()

            try:
                balance_resp = await ls.overseas_futureoption().accno().CIDBQ01500(
                    body=CIDBQ01500.CIDBQ01500InBlock1(
                        RecCnt=1,
                        QryDt=query_date,
                        BalTpCode="2",
                    )
                ).req_async()
            except Exception as exc:
                pg_logger.exception(f"해외선물 잔고 조회에 실패했습니다: {exc}")
                balance_resp = None

            if balance_resp and getattr(balance_resp, "block2", None):
                for blk in balance_resp.block2:
                    symbol_code = str(getattr(blk, "IsuCodeVal", "") or "").strip()
                    if symbol_code:
                        held_isus.add(symbol_code)

                    entry: HeldSymbolOverseasFutures = {
                        "IsuCodeVal": symbol_code,
                    }

                    isu_nm = getattr(blk, "IsuNm", None)
                    if isinstance(isu_nm, str) and isu_nm.strip():
                        entry["IsuNm"] = isu_nm.strip()

                    bns_tp_code = getattr(blk, "BnsTpCode", None)
                    if isinstance(bns_tp_code, str) and bns_tp_code.strip():
                        entry["BnsTpCode"] = bns_tp_code.strip()

                    for field_name in ("BalQty", "OrdAbleAmt", "OvrsDrvtNowPrc", "AbrdFutsEvalPnlAmt", "PchsPrc", "MaintMgn", "CsgnMgn"):
                        value = getattr(blk, field_name, None)
                        if value not in (None, ""):
                            try:
                                entry[field_name] = float(value)
                            except (TypeError, ValueError):
                                pass

                    due_dt = getattr(blk, "DueDt", None)
                    if isinstance(due_dt, str) and due_dt.strip():
                        entry["DueDt"] = due_dt.strip()

                    crcy_code = getattr(blk, "CrcyCodeVal", None)
                    if isinstance(crcy_code, str) and crcy_code.strip():
                        entry["CrcyCodeVal"] = crcy_code.strip()

                    pos_no = getattr(blk, "PosNo", None)
                    if isinstance(pos_no, str) and pos_no.strip():
                        entry["PosNo"] = pos_no.strip()

                    held_symbols.append(entry)

            strategy_symbols = {
                str(symbol.get("symbol") or "").strip()
                for symbol in symbols_from_strategy
                if symbol.get("symbol") is not None
            }
            strategy_symbols = {code for code in strategy_symbols if code}

            for symbol_code in strategy_symbols:
                try:
                    orders_resp = await ls.overseas_futureoption().accno().CIDBQ01800(
                        body=CIDBQ01800.CIDBQ01800InBlock1(
                            IsuCodeVal=symbol_code,
                            OrdDt=query_date,
                            OrdStatCode="2",
                        )
                    ).req_async()
                except Exception as exc:
                    pg_logger.exception(f"해외선물 미체결 주문 조회에 실패했습니다 ({symbol_code}): {exc}")
                    continue

                if not orders_resp or not getattr(orders_resp, "block2", None):
                    continue

                for blk in orders_resp.block2:
                    try:
                        pending_qty = int(getattr(blk, "UnercQty", 0) or 0)
                    except (TypeError, ValueError):
                        pending_qty = 0

                    if pending_qty <= 0:
                        continue

                    entry: NonTradedSymbolOverseasFutures = {
                        "OvrsFutsOrdNo": str(getattr(blk, "OvrsFutsOrdNo", "") or "").strip(),
                        "OvrsFutsOrgOrdNo": str(getattr(blk, "OvrsFutsOrgOrdNo", "") or "").strip(),
                        "IsuCodeVal": str(getattr(blk, "IsuCodeVal", "") or "").strip(),
                        "OrdDt": str(getattr(blk, "OrdDt", "") or "").strip(),
                        "OrdTime": str(getattr(blk, "OrdTime", "") or "").strip(),
                        "BnsTpCode": str(getattr(blk, "BnsTpCode", "") or "").strip(),
                        "FutsOrdStatCode": str(getattr(blk, "FutsOrdStatCode", "") or "").strip(),
                        "FutsOrdTpCode": str(getattr(blk, "FutsOrdTpCode", "") or "").strip(),
                        "AbrdFutsOrdPtnCode": str(getattr(blk, "AbrdFutsOrdPtnCode", "") or "").strip(),
                        "UnercQty": pending_qty,
                    }

                    isu_nm = getattr(blk, "IsuNm", None)
                    if isinstance(isu_nm, str) and isu_nm.strip():
                        entry["IsuNm"] = isu_nm.strip()

                    for field_name, caster in (("OrdQty", int), ("ExecQty", int)):
                        value = getattr(blk, field_name, None)
                        if value not in (None, ""):
                            try:
                                entry[field_name] = caster(value)
                            except (TypeError, ValueError):
                                pass

                    price_value = getattr(blk, "OvrsDrvtOrdPrc", None)
                    if price_value not in (None, ""):
                        try:
                            entry["OvrsDrvtOrdPrc"] = float(price_value)
                        except (TypeError, ValueError):
                            pass

                    fcm_ord_no = getattr(blk, "FcmOrdNo", None)
                    if isinstance(fcm_ord_no, str) and fcm_ord_no.strip():
                        entry["FcmOrdNo"] = fcm_ord_no.strip()

                    fcm_acnt_no = getattr(blk, "FcmAcntNo", None)
                    if isinstance(fcm_acnt_no, str) and fcm_acnt_no.strip():
                        entry["FcmAcntNo"] = fcm_acnt_no.strip()

                    exec_bns_code = getattr(blk, "ExecBnsTpCode", None)
                    if isinstance(exec_bns_code, str) and exec_bns_code.strip():
                        entry["ExecBnsTpCode"] = exec_bns_code.strip()

                    cvrg_yn = getattr(blk, "CvrgYn", None)
                    if isinstance(cvrg_yn, str) and cvrg_yn.strip():
                        entry["CvrgYn"] = cvrg_yn.strip()

                    non_trade_symbols.append(entry)
                    held_isus.add(symbol_code)

            if held_isus:
                non_held_symbols = []
                for m_symbol in symbols_from_strategy:
                    m_symbol_code = str(m_symbol.get("symbol") or "").strip()
                    if not m_symbol_code or m_symbol_code not in held_isus:
                        non_held_symbols.append(m_symbol)

                return non_held_symbols, held_symbols, non_trade_symbols

            return symbols_from_strategy, held_symbols, non_trade_symbols

        return symbols_from_strategy, held_symbols, non_trade_symbols

    async def modify_order_execute(
        self,
        system: SystemType,
        symbols_from_strategy: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
        modify_order: OrderStrategyType,
        order_id: str,
    ):
        pg_logger.info(
            f"🛠️ [ORDER] {order_id}: 정정 주문 흐름을 시작합니다 (전략 종목 {len(symbols_from_strategy)}개)"
        )
        dps = await self._setup_dps(system, modify_order)

        # 필터링, 보유, 미체결 종목들 가져오기
        non_held_symbols, held_symbols, non_trade_symbols = await self._block_duplicate_symbols(system, symbols_from_strategy)

        # 미체결 종목 없으면 넘기기
        if not non_trade_symbols:
            pg_logger.warning(f"⚠️ [ORDER] {order_id}: 정정할 미체결 종목이 없어 흐름을 종료합니다")
            return

        # 미체결 종목 전략 계산으로
        modify_symbols, community_instance = await self.plugin_resolver.resolve_buysell_community(
            system_id=system.get("settings", {}).get("system_id", None),
            trade=modify_order,
            symbols=non_held_symbols,
            held_symbols=held_symbols,
            non_trade_symbols=non_trade_symbols,
            dps=dps,
        )

        if not modify_symbols:
            pg_logger.warning(f"❌ [ORDER] {order_id}: 조건을 통과한 종목이 없어 정정 주문을 중단합니다")
            return

        pg_logger.info(
            f"🟡 [ORDER] {order_id}: 플러그인이 정정 대상 {len(modify_symbols)}개 종목을 반환했습니다"
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
        pg_logger.info(
            f"🗑️ [ORDER] {order_id}: 취소 주문 흐름을 시작합니다 (전략 종목 {len(symbols_from_strategy)}개)"
        )
        dps = await self._setup_dps(system, cancel_order)

        # 필터링, 보유, 미체결 종목들 가져오기
        non_held_symbols, held_symbols, non_trade_symbols = await self._block_duplicate_symbols(system, symbols_from_strategy)

        # 미체결 종목 없으면 넘기기
        if not non_trade_symbols:
            pg_logger.warning(f"⚠️ [ORDER] {order_id}: 취소할 미체결 종목이 없어 흐름을 종료합니다")
            return

        # 미체결 종목 전략 계산으로
        cancel_symbols, community_instance = await self.plugin_resolver.resolve_buysell_community(
            system_id=system.get("settings", {}).get("system_id", None),
            trade=cancel_order,
            symbols=non_held_symbols,
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
            pg_logger.info(
                f"🔴 [ORDER] {order_id}: 플러그인이 취소 대상 {len(cancel_symbols)}개 종목을 반환했습니다"
            )
        else:
            pg_logger.warning(
                f"❌ [ORDER] {order_id}: 취소 조건을 만족하는 종목이 없습니다"
            )

    async def _build_order_function(
        self,
        system: SystemType,
        symbol: Union[
            BaseNewOrderOverseasStockResponseType,
            BaseModifyOrderOverseasStockResponseType,
            BaseCancelOrderOverseasStockResponseType,
            BaseNewOrderOverseasFuturesResponseType,
            BaseModifyOrderOverseasFutureResponseType,
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
            pg_logger.error(f"❗️ [ORDER] 주문 전송에 실패했습니다: {result.error_msg}")
            raise exceptions.OrderException(
                message=f"Order placement failed: {result.error_msg}"
            )

        return result

    async def _setup_dps(
        self,
        system: SystemType,
        trade: OrderStrategyType
    ) -> DpsTyped:
        """Setup DPS (deposit) information for trading."""
        available_balance = float(trade.get("available_balance", 0.0))
        dps: DpsTyped = {
            "fcurr_dps": available_balance,
            "fcurr_ord_able_amt": available_balance,
        }
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
                    dps["fcurr_dps"] = cosoq02701.block3[0].FcurrDps
                    dps["fcurr_ord_able_amt"] = cosoq02701.block3[0].FcurrOrdAbleAmt
                    pg_logger.debug(
                        f"[ORDER] DPS: LS 해외주식 잔고 조회 결과 예수금={dps['fcurr_dps']} 주문가능금액={dps['fcurr_ord_able_amt']}"
                    )

            elif product == "overseas_futures":
                cidbq03000 = await LS.get_instance().overseas_futureoption().accno().CIDBQ03000(
                    body=CIDBQ03000.CIDBQ03000InBlock1(
                        AcntTpCode="1",
                        TrdDt="",
                    )
                ).req_async()

                # TODO: 여러 통화들 지원

                if cidbq03000 and getattr(cidbq03000, "block2", None):

                    block = None
                    for cid in cidbq03000.block2:
                        if cid.CrcyObjCode == "USD":
                            block = cid
                            break
                    dps["fcurr_dps"] = block.OvrsFutsDps if block else 0.0
                    dps["fcurr_ord_able_amt"] = block.AbrdFutsOrdAbleAmt if block else 0.0

        pg_logger.debug(
            f"[ORDER] DPS: 최종 예수금={dps['fcurr_dps']} 주문가능금액={dps['fcurr_ord_able_amt']}"
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
            BaseModifyOrderOverseasFutureResponseType,
            BaseCancelOrderOverseasFuturesResponseType,
        ]],
        community_instance: Optional[Union[BaseOrderOverseasStock, BaseOrderOverseasFutures]],
        field: Literal["new", "modify", "cancel"],
        order_id: str,
    ) -> None:
        """Execute trades for the given symbols."""
        for symbol in symbols:
            if symbol.get("success") is False:
                pg_logger.debug(
                    f"[ORDER] {order_id}: 조건을 통과하지 못한 종목 {self._symbol_label(symbol)}을(를) 건너뜁니다"
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

            if result and result.error_msg:
                pg_logger.error(f"❗️ [ORDER] {order_id}: 주문 전송에 실패했습니다 -> {result.error_msg}")
                continue

            product_key = system.get("securities", {}).get("product", "overseas_stock") or "overseas_stock"
            icon = self._field_icon(field)
            field_label = self._field_label(field)
            product_label = self._product_label(product_key)
            ord_display = ord_no or "-"
            pg_logger.info(
                f"{icon} [ORDER] {order_id}: {product_label} {field_label} 주문 완료 ({self._symbol_label(symbol)}, 주문번호={ord_display})"
            )
