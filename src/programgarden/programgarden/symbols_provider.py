"""
LS Securities symbol provider integration.

This module implements a small adapter around the LS (LS증권) finance
client to fetch available symbols for a given product. The adapter exposes
a single async provider class that external developers can call to retrieve
a list of `SymbolInfo` records.
"""

from typing import List, Optional, Union

from programgarden_core import (
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    OrderType,
    symbol_logger,
    SecuritiesAccountType,
)
from programgarden_finance import LS, g3190, COSOQ00201, g3104, COSAQ00102, o3101, CIDBQ01800, o3105
from datetime import date, datetime
import pytz


class SymbolProvider:
    async def get_symbols(
        self,
        order_type: Optional[OrderType],
        securities: SecuritiesAccountType
    ) -> List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]:
        """
        Retrieve a list of symbols for the requested company and product.
        """

        company = securities.get("company", "ls")
        product = securities.get("product", "overseas_stock")

        if company != "ls":
            return []

        ls = LS.get_instance()
        if not ls.is_logged_in():
            return []

        symbols: List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]] = []
        if product == "overseas_stock":
            if order_type == "new_buy" or order_type is None:
                symbols.extend(await self.get_stock_market_symbols(ls))
            elif order_type == "new_sell":
                symbols.extend(await self.get_stock_account_symbols(ls))

            elif order_type in ["modify_buy", "modify_sell", "cancel_buy", "cancel_sell"]:
                symbols.extend(await self.get_stock_non_trade_symbols(ls))

        elif product == "overseas_futures":
            if order_type in ("new_buy", "new_sell", None):
                symbols.extend(await self.get_future_market_symbols(ls))
            elif order_type in ["modify_buy", "modify_sell", "cancel_buy", "cancel_sell"]:
                symbols.extend(
                    await self.get_future_non_trade_symbols(ls)
                )

        else:
            symbol_logger.warning(f"Unsupported product: {product}")

        return symbols

    async def get_stock_account_symbols(self, ls: LS) -> List[SymbolInfoOverseasStock]:
        """Retrieve account symbols for overseas stocks."""
        tmp: List[SymbolInfoOverseasStock] = []
        response = await ls.overseas_stock().accno().cosoq00201(
                    COSOQ00201.COSOQ00201InBlock1(
                        RecCnt=1,
                        BaseDt=date.today().strftime("%Y%m%d"),
                        CrcyCode="ALL",
                        AstkBalTpCode="00"
                    )
                ).req_async()

        for block in response.block4:

            result = await ls.overseas_stock().market().g3104(
                body=g3104.G3104InBlock(
                    keysymbol=block.FcurrMktCode+block.ShtnIsuNo.strip(),
                    exchcd=block.FcurrMktCode,
                    symbol=block.ShtnIsuNo.strip()
                )
            ).req_async()

            if not result:
                continue

            tmp.append(
                SymbolInfoOverseasStock(
                    symbol=block.ShtnIsuNo.strip(),
                    exchcd=block.FcurrMktCode,
                    mcap=result.block.shareprc,
                    product_type="overseas_stock",
                )
            )

        return tmp

    async def get_stock_market_symbols(self, ls: LS) -> List[SymbolInfoOverseasStock]:
        """Retrieve buy symbols for overseas stocks."""
        overseas_stock = ls.overseas_stock()
        tmp: List[SymbolInfoOverseasStock] = []

        await overseas_stock.market().g3190(
                                body=g3190.G3190InBlock(
                                                delaygb="R",
                                                natcode="US",
                                                exgubun="2",
                                                readcnt=500,
                                                cts_value="",
                                )
                ).occurs_req_async(
                                callback=lambda response, _: tmp.extend(
                                                SymbolInfoOverseasStock(
                                                    symbol=block.symbol.strip(),
                                                    exchcd=block.exchcd,
                                                    mcap=block.share*block.clos,
                                                    product_type="overseas_stock",
                                                )
                                                for block in response.block1
                                ) if response and hasattr(response, "block1") and response.block1 else None
                )

        return tmp

    async def get_stock_non_trade_symbols(self, ls: LS) -> List[SymbolInfoOverseasStock]:
        """Retrieve non-trade symbols for overseas stocks."""
        tmp: List[SymbolInfoOverseasStock] = []

        ny_tz = pytz.timezone("America/New_York")
        ny_time = datetime.now(ny_tz)

        for exchcd in ["81", "82"]:
            response = await ls.overseas_stock().accno().cosaq00102(
                        COSAQ00102.COSAQ00102InBlock1(
                            RecCnt=1,
                            QryTpCode="1",
                            BkseqTpCode="1",
                            OrdMktCode=exchcd,
                            BnsTpCode="0",
                            IsuNo="",
                            SrtOrdNo=999999999,
                            OrdDt=ny_time.strftime("%Y%m%d"),
                            ExecYn="2",
                            CrcyCode="USD",
                            ThdayBnsAppYn="0",
                            LoanBalHldYn="0"
                        )
                    ).req_async()

            for block in response.block3:
                result = await ls.overseas_stock().market().g3104(
                    body=g3104.G3104InBlock(
                        keysymbol=block.OrdMktCode+block.ShtnIsuNo.strip(),
                        exchcd=block.OrdMktCode,
                        symbol=block.ShtnIsuNo.strip()
                    )
                ).req_async()

                if not result:
                    continue

                tmp.append(
                    SymbolInfoOverseasStock(
                        symbol=block.ShtnIsuNo.strip(),
                        exchcd=block.OrdMktCode,
                        mcap=result.block.shareprc,
                        OrdNo=block.OrdNo,
                        product_type="overseas_stock",
                    )
                )

        return tmp

    async def get_future_market_symbols(self, ls: LS) -> List[SymbolInfoOverseasFutures]:
        """Retrieve tradable overseas futures symbols."""

        tmp: List[SymbolInfoOverseasFutures] = []

        response = await ls.overseas_futureoption().market().o3101(
            body=o3101.O3101InBlock(
                gubun="1"
            )
        ).req_async()

        if not response or not getattr(response, "block", None):
            return tmp

        for block in response.block:
            try:
                symbol_code = block.Symbol.strip()
            except AttributeError:
                symbol_code = block.Symbol

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
                contract_size = float(block.CtrtPrAmt)
                symbol_info["contract_size"] = contract_size
            except (TypeError, ValueError):
                pass

            try:
                unit_price = float(block.UntPrc)  # 호가단위가격
                symbol_info["unit_price"] = unit_price
            except (TypeError, ValueError):
                pass

            try:
                min_change_amount = float(block.MnChgAmt)  # 최소변동액
                symbol_info["min_change_amount"] = min_change_amount
            except (TypeError, ValueError):
                pass

            try:
                maintenance_margin = float(block.MntncMgn)  # 유지증거금
                symbol_info["maintenance_margin"] = maintenance_margin
            except (TypeError, ValueError):
                pass

            try:
                opening_margin = float(block.OpngMgn)  # 개시증거금
                symbol_info["opening_margin"] = opening_margin
            except (TypeError, ValueError):
                pass

            tmp.append(symbol_info)

        return tmp

    async def get_future_non_trade_symbols(self, ls: LS) -> List[SymbolInfoOverseasFutures]:
        """Retrieve pending overseas futures orders for modify/cancel workflows."""

        tmp: List[SymbolInfoOverseasFutures] = []

        try:
            response = await ls.overseas_futureoption().accno().CIDBQ01800(
                body=CIDBQ01800.CIDBQ01800InBlock1(
                    RecCnt=1,
                    IsuCodeVal="",  # 빈 문자열로 계좌 내 전체 미체결 주문을 조회합니다.
                    OrdDt="",
                    OrdStatCode="2",
                    BnsTpCode="0",
                    QryTpCode="1",
                    OrdPtnCode="00",
                    OvrsDrvtFnoTpCode="A",
                )
            ).req_async()
        except Exception as exc:
            symbol_logger.exception(f"해외선물 미체결 주문 조회에 실패했습니다: {exc}")
            return tmp

        if not response or not getattr(response, "block2", None):
            return tmp

        for block in response.block2:
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
                "OrdNo": block.OvrsFutsOrdNo
            }

            req = await ls.overseas_futureoption().market().o3105(
                body=o3105.O3105InBlock(
                    symbol=symbol_code
                )
            ).req_async()

            if not req or not getattr(req, "block", None):
                if ls.token_manager.paper_trading:
                    symbol_logger.info(f"모의투자API 환경에서 해외선물 미체결 주문의 종목 정보를 조회하지 못했습니다: {symbol_code}")
                symbol_logger.warning(f"해외선물 미체결 주문의 종목 정보를 조회하지 못했습니다: {symbol_code}")
                continue

            futures_info["exchcd"] = req.block.ExchCd
            futures_info["due_yymm"] = req.block.MtrtDt
            futures_info["prdt_code"] = req.block.GdsCd
            futures_info["currency_code"] = req.block.CrncyCd
            futures_info["contract_size"] = float(req.block.CtrtPrAmt)
            futures_info["position_side"] = block.BnsTpCode == "1" and "short" or block.BnsTpCode == "2" and "long" or "flat"
            futures_info["unit_price"] = float(req.block.UntPrc)
            futures_info["min_change_amount"] = float(req.block.MnChgAmt)
            futures_info["maintenance_margin"] = float(req.block.MntncMgn)
            futures_info["opening_margin"] = float(req.block.OpngMgn)

            tmp.append(futures_info)

        return tmp
