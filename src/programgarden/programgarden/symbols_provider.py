"""
LS Securities symbol provider integration.

This module implements a small adapter around the LS (LS증권) finance
client to fetch available symbols for a given product. The adapter exposes
a single async provider class that external developers can call to retrieve
a list of `SymbolInfo` records.
"""

from typing import List, Literal, Optional, Union
from zoneinfo import ZoneInfo

from programgarden_core import (
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    OrderType,
    symbol_logger,
    SecuritiesAccountType,
)
from programgarden_finance import LS, g3190, COSOQ00201, g3104, COSAQ00102, o3101, CIDBQ01800, o3105, CIDBQ01500
from datetime import date, datetime
import pytz


class SymbolProvider:
    async def get_symbols(
        self,
        order_type: Optional[OrderType],
        securities: SecuritiesAccountType,
        product: Literal["overseas_stock", "overseas_futures"] = "overseas_stock",
        futures_outstanding_only: bool = False,
    ) -> List[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]:
        """
        Retrieve a list of symbols for the requested company and product.

        outstanding_only: 미결제 종목도 조회하기 위함
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
            if order_type in ("new_buy", "new_sell", None) and not futures_outstanding_only:
                symbols.extend(
                    await self.get_future_market_symbols(ls)
                )
            elif order_type in ["modify_buy", "modify_sell", "cancel_buy", "cancel_sell"]:
                symbols.extend(
                    await self.get_future_non_trade_symbols(
                        ls=ls,
                        order_type=order_type
                    )
                )

            # TODO: 해외선물은 매수/매도와 상관없이 보유종목 반환을 해주어야 미결제 체결을 한다.
            if futures_outstanding_only:
                symbols.extend(
                    await self.get_future_account_symbols(ls)
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
        """해외선물 시장의 전체 종목 반환"""

        tmp: List[SymbolInfoOverseasFutures] = []

        o3101_res = await ls.overseas_futureoption().market().o3101(
            body=o3101.O3101InBlock(
                gubun="1"
            )
        ).req_async()

        if not o3101_res or not getattr(o3101_res, "block", None):
            return tmp

        for block in o3101_res.block:
            try:
                symbol_code = block.Symbol.strip()
            except AttributeError:
                symbol_code = block.Symbol

            # 모의투자는 홍콩거래소만 지원됩니다.
            if ls.token_manager.paper_trading:
                if block.ExchCd.strip() != "HKEX":
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

    async def get_future_non_trade_symbols(
            self,
            ls: LS,
            order_type: Optional[OrderType] = None
    ) -> List[SymbolInfoOverseasFutures]:
        """미체결 종목들 반환"""

        tmp: List[SymbolInfoOverseasFutures] = []

        BnsTpCode = "0"
        if order_type == "modify_buy" or order_type == "cancel_buy":
            BnsTpCode = "2"
        elif order_type == "modify_sell" or order_type == "cancel_sell":
            BnsTpCode = "1"

        try:
            cidbq01800_response = await ls.overseas_futureoption().accno().CIDBQ01800(
                body=CIDBQ01800.CIDBQ01800InBlock1(
                    RecCnt=1,
                    IsuCodeVal="",  # 빈 문자열로 계좌 내 전체 미체결 주문을 조회합니다.
                    OrdDt="",
                    OrdStatCode="2",
                    BnsTpCode=BnsTpCode,
                    QryTpCode="1",
                    OrdPtnCode="00",
                    OvrsDrvtFnoTpCode="A",
                )
            ).req_async()
        except Exception as exc:
            symbol_logger.exception(f"해외선물 미체결 주문 조회에 실패했습니다: {exc}")
            return tmp

        if not cidbq01800_response or not getattr(cidbq01800_response, "block2", None):
            return tmp

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
                "OrdNo": block.OvrsFutsOrdNo
            }

            # 모의투자에서도 사용 가능한 종목인지 확인하기 위해서 시세 요청
            # 모의투자 종목은 시세 요청에서 데이터가 나오지 않는다.
            exist_req = await ls.overseas_futureoption().market().o3105(
                body=o3105.O3105InBlock(
                    symbol=symbol_code
                )
            ).req_async()

            if not exist_req or not getattr(exist_req, "block", None):
                if ls.token_manager.paper_trading:
                    symbol_logger.warning(f"모의투자API에서 지원되지 않는 종목입니다: {symbol_code}")
                symbol_logger.warning(f"해외선물API에서 지원되지 않는 종목입니다: {symbol_code}")
                continue

            futures_info["exchcd"] = exist_req.block.ExchCd
            futures_info["due_yymm"] = exist_req.block.MtrtDt
            futures_info["prdt_code"] = exist_req.block.GdsCd
            futures_info["currency_code"] = exist_req.block.CrncyCd
            futures_info["contract_size"] = float(exist_req.block.CtrtPrAmt)
            futures_info["position_side"] = block.BnsTpCode == "1" and "short" or block.BnsTpCode == "2" and "long" or "flat"
            futures_info["unit_price"] = float(exist_req.block.UntPrc)
            futures_info["min_change_amount"] = float(exist_req.block.MnChgAmt)
            futures_info["maintenance_margin"] = float(exist_req.block.MntncMgn)
            futures_info["opening_margin"] = float(exist_req.block.OpngMgn)

            tmp.append(futures_info)

        return tmp

    async def get_future_account_symbols(self, ls: LS) -> List[SymbolInfoOverseasFutures]:
        """보유 종목들 반환"""

        tmp: List[SymbolInfoOverseasFutures] = []

        ny_time = datetime.now(ZoneInfo("America/New_York"))
        query_date = ny_time.strftime("%Y%m%d")

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
            symbol_logger.exception(f"해외선물 보유 종목 조회에 실패했습니다: {exc}")
            return tmp

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

                futures_info: SymbolInfoOverseasFutures = {
                    "symbol": symbol_code,
                    "product_type": "overseas_futures",
                    "position_side": blk.BnsTpCode == "1" and "short" or blk.BnsTpCode == "2" and "long" or "flat",
                }

                # 모의투자에서도 사용 가능한 종목인지 확인하기 위해서 시세 요청
                # 모의투자 종목은 시세 요청에서 데이터가 나오지 않는다.
                exist_req = await ls.overseas_futureoption().market().o3105(
                    body=o3105.O3105InBlock(
                        symbol=symbol_code
                    )
                ).req_async()

                if not exist_req or not getattr(exist_req, "block", None):
                    if ls.token_manager.paper_trading:
                        symbol_logger.warning(f"모의투자API에서 지원되지 않는 종목입니다: {symbol_code}")
                    symbol_logger.warning(f"해외선물API에서 지원되지 않는 종목입니다: {symbol_code}")
                    continue

                futures_info["exchcd"] = exist_req.block.ExchCd
                futures_info["due_yymm"] = exist_req.block.MtrtDt
                futures_info["prdt_code"] = exist_req.block.GdsCd
                futures_info["currency_code"] = exist_req.block.CrncyCd
                futures_info["contract_size"] = float(exist_req.block.CtrtPrAmt)
                futures_info["position_side"] = blk.BnsTpCode == "1" and "short" or blk.BnsTpCode == "2" and "long" or "flat"
                futures_info["unit_price"] = float(exist_req.block.UntPrc)
                futures_info["min_change_amount"] = float(exist_req.block.MnChgAmt)
                futures_info["maintenance_margin"] = float(exist_req.block.MntncMgn)
                futures_info["opening_margin"] = float(exist_req.block.OpngMgn)

                tmp.append(futures_info)

        return tmp