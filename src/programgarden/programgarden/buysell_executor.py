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
`BaseBuyOverseasStock` from `programgarden_core`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, TypedDict, Union
from zoneinfo import ZoneInfo
from programgarden_core import (
    SystemType, SymbolInfo,
    BaseBuyOverseasStockResponseType, BaseSellOverseasStockResponseType,
    pg_logger, BaseBuyOverseasStock, exceptions, NewBuyTradeType, HeldSymbol,
    NonTradedSymbol, NewSellTradeType, BaseSellOverseasStock,
    OrderCategoryType
)
from programgarden_finance import LS, COSAT00301, COSOQ00201, COSAQ00102, COSOQ02701

from programgarden.pg_listener import pg_listener
from programgarden.real_order_executor import RealOrderExecutor
from datetime import datetime

if TYPE_CHECKING:
    from .plugin_resolver import PluginResolver


class DpsTyped(TypedDict):
    fcurr_dps: float
    fcurr_ord_able_amt: float


class BuySellExecutor:
    """Orchestrates execution of buy/sell condition plugins.

    The executor requires a `PluginResolver` which maps condition
    identifiers to concrete classes. It does not implement trading
    strategies itself; instead it prepares and runs plugin instances
    and returns whatever those plugins produce.

    Contract (high level):
    - Input: a `system` config (dict-like `SystemType`) and a list of
      `SymbolInfo` items describing available symbols.
    - Output: a list of plugin execution responses (or None on error).
    - Error modes: missing plugin, incorrect plugin type, runtime
      exceptions inside plugin code. Errors are logged and result in
      a None return value from the internal executor.
    """

    def __init__(self, plugin_resolver: PluginResolver):
        # PluginResolver instance used to look up condition classes by id
        self.plugin_resolver = plugin_resolver
        self.real_order_executor = RealOrderExecutor()

    async def new_buy_execute(
        self,
        system: SystemType,
        symbols_from_strategy: List[SymbolInfo],
        new_buy: NewBuyTradeType,
        order_id: str,
    ) -> None:
        """
        Public entrypoint to perform buy execution for a system.
        """

        # 예수금 세팅
        available_balance = float(new_buy.get("available_balance", 0.0))
        dps: DpsTyped = {
            "fcurr_dps": available_balance,
            "fcurr_ord_able_amt": available_balance,
        }
        is_ls = system.get("securities", {}).get("company", None) == "ls"

        if available_balance == 0.0 and is_ls:
            # 예수금 가져오기
            cosoq02701 = await LS.get_instance().overseas_stock().accno().cosoq02701(
                body=COSOQ02701.COSOQ02701InBlock1(
                    RecCnt=1,
                    CrcyCode="USD",
                ),
            ).req_async()

            dps["fcurr_dps"] = cosoq02701.block3[0].FcurrDps
            dps["fcurr_ord_able_amt"] = cosoq02701.block3[0].FcurrOrdAbleAmt

        # 필터링, 보유, 미체결 종목들 가져오기
        filtered_symbols, held_symbols, non_trade_symbols = await self._block_duplicate_symbols(system, symbols_from_strategy)

        # 종목 보유중이면 막기
        if new_buy.get("block_duplicate_trade", True):
            symbols_from_strategy[:] = filtered_symbols

        if not symbols_from_strategy:
            pg_logger.warning(f"No symbols to buy. order_id: {order_id}")
            return

        purchase_symbols, community_instance = await self.plugin_resolver.resolve_buysell_community(
            system_id=system.get("settings", {}).get("system_id", None),
            trade=new_buy,
            symbols=symbols_from_strategy,
            held_symbols=held_symbols,
            non_trade_symbols=non_trade_symbols,
            dps=dps,
        )

        if not purchase_symbols:
            pg_logger.warning(f"No symbols match the order strategy. order_id: {order_id}")
            return

        for symbol in purchase_symbols:
            if not symbol.get("success"):
                continue

            # 주문 함수 구성
            result = await self._build_order_function(
                system=system,
                trade_type="submitted_new_buy",
                symbol=symbol
            )

            ord_no = None
            if result is not None:
                block2 = getattr(result, "block2", None)
                ord_val = getattr(block2, "OrdNo", None) if block2 is not None else None
                ord_no = str(ord_val) if ord_val is not None else None

            await self.real_order_executor.send_data_community_instance(
                ordNo=ord_no,
                community_instance=community_instance
            )

            pg_logger.info(f"🟢 New buy order executed for order '{order_id}'")

    async def _block_duplicate_symbols(
        self,
        system: SystemType,
        symbols_from_strategy: List[SymbolInfo],
    ):
        """
        Filter out only the stocks that are not held

        Returns로는 중복 여부 필터링한 종목들과, 보유잔고 종목들과 미체결 종목들이 반환된다.
        """

        held_symbols: List[HeldSymbol] = []
        non_trade_symbols: List[NonTradedSymbol] = []

        company = system.get("securities", {}).get("company", "")
        product = system.get("securities", {}).get("product", [])
        if company == "ls" and product == "overseas_stock":
            ls = LS.get_instance()
            if not ls.is_logged_in():
                await ls.async_login(
                        appkey=system.get("securities", {}).get("appkey", None),
                        appsecretkey=system.get("securities", {}).get("appsecretkey", None)
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
                    HeldSymbol(
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
                        BnsTpCode="2",
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
                            NonTradedSymbol(
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
                filtered = []
                for m_symbol in symbols_from_strategy:
                    m_isu_no = m_symbol.get("symbol")

                    if m_isu_no is None or str(m_isu_no).strip() not in held_isus:
                        filtered.append(m_symbol)
                return filtered, held_symbols, non_trade_symbols

            return [], held_symbols, non_trade_symbols

    async def new_sell_execute(
        self,
        system: SystemType,
        symbols_from_strategy: List[SymbolInfo],
        new_sell: NewSellTradeType,
        order_id: str,
    ) -> Optional[Union[BaseBuyOverseasStock, BaseSellOverseasStock]]:
        """
        Public entrypoint to perform sell execution for a system.
        """

        filtered_symbols, held_symbols, non_trade_symbols = await self._block_duplicate_symbols(system, symbols_from_strategy)

        symbols, community_instance = await self.plugin_resolver.resolve_buysell_community(
            system_id=system.get("settings", {}).get("system_id", None),
            trade=new_sell,
            symbols=symbols_from_strategy,
            held_symbols=held_symbols,
            non_trade_symbols=non_trade_symbols,
        )

        if not symbols:
            pg_logger.warning("No symbols found for sell strategy.")

            return

        for symbol in symbols:
            if not symbol.get("success"):
                continue

            result = await self._build_order_function(
                system=system,
                trade_type="submitted_new_sell",
                symbol=symbol
            )

            await self.real_order_executor.send_data_community_instance(
                ordNo=str(result.block2.OrdNo),
                community_instance=community_instance
            )

            if result.error_msg:
                pg_logger.error(f"Order placement failed: {result.error_msg}")

                continue

            pg_logger.info(f"🟢 New buy order executed for order '{order_id}'")

    async def _build_order_function(
        self,
        system: SystemType,
        trade_type: OrderCategoryType,
        symbol: Union[BaseBuyOverseasStockResponseType, BaseSellOverseasStockResponseType]
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

        if company == "ls":

            ls = LS.get_instance()

            if product == "overseas_stock":
                # unify buy/sell order placement
                ord_ptn = "02" if trade_type == "submitted_new_buy" else "01"
                result: COSAT00301.COSAT00301Response = await ls.overseas_stock().order().cosat00301(
                    body=COSAT00301.COSAT00301InBlock1(
                        OrdPtnCode=ord_ptn,
                        OrgOrdNo=None,
                        OrdMktCode=symbol.get("ord_mkt_code"),
                        IsuNo=symbol.get("isu_no"),
                        OrdQty=symbol.get("ord_qty"),
                        OvrsOrdPrc=symbol.get("ovrs_ord_prc"),
                        OrdprcPtnCode=symbol.get("ordprc_ptn_code"),
                    )
                ).req_async()

                pg_listener.emit_real_order({
                    "order_type": trade_type,
                    "message": result.rsp_msg,
                    "symbol": symbol,
                    "response": result,
                })

                if result.error_msg:
                    pg_logger.error(f"Order placement failed: {result.error_msg}")
                    raise exceptions.OrderException(
                        message=f"Order placement failed: {result.error_msg}"
                    )

                return result
