import asyncio
import threading
from typing import Any, Dict, List, Optional, Union
from programgarden_finance import LS, AS0, AS1, AS2, AS3, AS4, TC1, TC2, TC3
from programgarden_core import (
    OrderRealResponseType, SystemType, pg_logger,
    BaseOrderOverseasStock, BaseOrderOverseasFuture,
)
from programgarden.pg_listener import pg_listener


class RealOrderExecutor:
    """
    주문 상태에 대한 실시간 수신기
    """

    def __init__(self):
        # map ordNo -> community instance that created the order
        self._order_community_instance_map: Dict[str, Any] = {}
        # pending messages received before the instance was registered
        # ordNo -> list[response]
        self._pending_order_messages: Dict[str, List[Dict[Any, Any]]] = {}
        # simple lock to protect access to the two maps from multiple threads
        # callbacks from the LS library may come from non-async threads.
        self._lock = threading.Lock()

    async def real_order_websockets(
        self,
        system: SystemType,
    ):
        """
        Real-time order tracking function
        """

        securities = system.get("securities", {})
        company = securities.get("company", None)
        product = securities.get("product", "overseas_stock")
        if len(system.get("orders", [])) > 0 and company == "ls":
            if product == "overseas_stock":
                self.buy_sell_order_real = LS.get_instance().overseas_stock().real()
            elif product == "overseas_futures":
                self.buy_sell_order_real = LS.get_instance().overseas_futureoption().real()
            else:
                pg_logger.warning(f"Unsupported product for real order websocket: {product}")
                return

            await self.buy_sell_order_real.connect()
            # store the currently running event loop so synchronous callbacks
            # (from the LS library) can schedule coroutines back onto it
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # no running loop (should not happen here because we're in async fn)
                self._loop = None

            if product == "overseas_stock":
                self.buy_sell_order_real.AS0().on_as0_message(listener=self._as0_message_dispatcher)
                self.buy_sell_order_real.AS1().on_as1_message(listener=self._as1_message_dispatcher)
                self.buy_sell_order_real.AS2().on_as2_message(listener=self._as2_message_dispatcher)
                self.buy_sell_order_real.AS3().on_as3_message(listener=self._as3_message_dispatcher)
                self.buy_sell_order_real.AS4().on_as4_message(listener=self._as4_message_dispatcher)
            else:
                self.buy_sell_order_real.TC1().on_tc1_message(listener=self._tc1_message_dispatcher)
                self.buy_sell_order_real.TC2().on_tc2_message(listener=self._tc2_message_dispatcher)
                self.buy_sell_order_real.TC3().on_tc3_message(listener=self._tc3_message_dispatcher)

            self._stop_event = asyncio.Event()
            await self._stop_event.wait()

    def _as0_message_dispatcher(
        self,
        response: AS0.AS0RealResponse
    ):
        """
        실시간 주문 메세지 디스패치이다.
        커뮤니티의 전략 인스턴스를 찾아서 on_real_order_receive 함수를 호출한다.
        on_real_order_receive는 주문번호의 쌍을 이루고 있는 함수이고
        주문이 발생할때마다 데이터와 함께 on_real_order_receive가 호출된다.
        """
        try:
            ordNo = response.body.sOrdNo
            if ordNo is None:
                return

            ord_key = str(ordNo)
            payload = response.model_dump()

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 접수 완료",
                "response": payload,
            })

        except Exception as e:
            pg_logger.error(e)

    def _as1_message_dispatcher(
        self,
        response: AS1.AS1RealResponse
    ) -> None:
        try:
            ordNo = response.body.sOrdNo
            if ordNo is None:
                return

            ord_key = str(ordNo)
            payload = response.model_dump()

            if response.body.sUnercQty == 0:
                # 주문이 모두 체결되었으므로 더 이상 메시지를 받을 필요가 없음
                self._order_community_instance_map.pop(ord_key, None)

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 체결 완료",
                "response": payload,
            })

        except Exception:
            pg_logger.exception("Error in AS1 dispatcher")

    def _as2_message_dispatcher(
        self,
        response: AS2.AS2RealResponse
    ) -> None:
        try:
            sOrdNo = response.body.sOrdNo
            if sOrdNo is None:
                return

            ord_key = str(sOrdNo)
            payload = response.model_dump()

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 정정 완료",
                "response": payload,
            })

        except Exception:
            pg_logger.exception("Error in AS2 dispatcher")

    def _as3_message_dispatcher(
        self,
        response: AS3.AS3RealResponse
    ) -> None:
        try:
            ordNo = response.body.sOrdNo
            if ordNo is None:
                return

            ord_key = str(ordNo)

            payload = response.model_dump()

            self._order_community_instance_map.pop(ord_key, None)

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 취소 완료",
                "response": payload,
            })

        except Exception:
            pg_logger.exception("Error in AS3 dispatcher")

    def _as4_message_dispatcher(
        self,
        response: AS4.AS4RealResponse
    ) -> None:
        try:
            ordNo = response.body.sOrdNo
            if ordNo is None:
                return

            ord_key = str(ordNo)
            # pass a dict (model_dump) so the dispatcher can treat the
            # response uniformly (it expects a dict-like object)
            payload = response.model_dump()

            self._order_community_instance_map.pop(ord_key, None)

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 거부됨",
                "response": payload,
            })
        except Exception:
            pg_logger.exception("Error in AS4 dispatcher")

    def _tc1_message_dispatcher(
        self,
        response: TC1.TC1RealResponse
    ) -> None:
        try:
            if response.body is None:
                return

            ord_no = getattr(response.body, "ordr_no", None)
            ord_key = str(ord_no) if ord_no else None
            payload = response.model_dump()

            order_type = self._futures_order_type("TC1", payload.get("body", {}))

            if ord_key:
                self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)

            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": payload.get("rsp_msg") or self._order_message_from_type(order_type),
                "response": payload,
            })

        except Exception:
            pg_logger.exception("Error in TC1 dispatcher")

    def _tc2_message_dispatcher(
        self,
        response: TC2.TC2RealResponse
    ) -> None:
        try:
            if response.body is None:
                return

            ord_no = getattr(response.body, "ordr_no", None)
            ord_key = str(ord_no) if ord_no else None
            payload = response.model_dump()

            order_type = self._futures_order_type("TC2", payload.get("body", {}))

            if ord_key:
                self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
                if order_type in {"reject_buy", "reject_sell"}:
                    self._order_community_instance_map.pop(ord_key, None)

            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": payload.get("rsp_msg") or self._order_message_from_type(order_type),
                "response": payload,
            })

        except Exception:
            pg_logger.exception("Error in TC2 dispatcher")

    def _tc3_message_dispatcher(
        self,
        response: TC3.TC3RealResponse
    ) -> None:
        try:
            if response.body is None:
                return

            ord_no = getattr(response.body, "ordr_no", None)
            ord_key = str(ord_no) if ord_no else None
            payload = response.model_dump()

            order_type = self._futures_order_type("TC3", payload.get("body", {}))

            if ord_key:
                self.__dispatch_real_order_message(ord_key, payload, order_type=order_type)
                if order_type in {"filled_new_buy", "filled_new_sell", "cancel_complete_buy", "cancel_complete_sell"}:
                    self._order_community_instance_map.pop(ord_key, None)

            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": payload.get("rsp_msg") or self._order_message_from_type(order_type),
                "response": payload,
            })

        except Exception:
            pg_logger.exception("Error in TC3 dispatcher")

    async def send_data_community_instance(
        self,
        ordNo: str,
        community_instance: Optional[Union[BaseOrderOverseasStock, BaseOrderOverseasFuture]],
    ) -> None:
        """
        Send order result data to the community plugin instance's
        `on_real_order_receive` method after an order is placed.

        The order number is used as the key. If there are queued messages
        for this order number, they will be delivered in FIFO order.
        """
        if ordNo:
            # register the community instance (may be None)
            with self._lock:
                self._order_community_instance_map[ordNo] = community_instance

                # peek pending messages for this ordNo. Only remove (pop)
                # them if we're actually going to deliver them. If the
                # community_instance is None we should keep queued messages
                # for later registration instead of dropping them.
                pending = None
                if community_instance is not None:
                    # remove pending list so future dispatches won't re-append
                    pending = self._pending_order_messages.pop(ordNo, None)

            if pending and community_instance is not None:
                for real_order_response in pending:
                    # compute order type from the pending message and deliver
                    order_type = self._determine_order_type_from_payload(real_order_response)
                    handler = getattr(community_instance, "on_real_order_receive", None)
                    if handler:
                        # asyncio.iscoroutinefunction returns False for bound
                        # instance methods in some Python versions, so check
                        # the underlying function if present.
                        func_to_check = getattr(handler, "__func__", handler)
                        if asyncio.iscoroutinefunction(func_to_check):
                            await handler(order_type, real_order_response)
                        else:
                            await asyncio.to_thread(handler, order_type, real_order_response)

    def __dispatch_real_order_message(
        self,
        ord_key: str,
        response: Dict[str, Any],
        order_type: Optional[OrderRealResponseType] = None,
    ) -> None:
        """Dispatch order response to the registered community instance or queue it.

        This centralizes async/sync handler delivery and pending queueing.

        If we have a stored event loop (the main async loop started
        in `real_order_websockets`), schedule coroutines/thread jobs
        safely from synchronous callback contexts. Otherwise try to
        schedule on the current loop or fall back to a thread.
        """

        if order_type is None:
            order_type = self._determine_order_type_from_payload(response)

        instance = self._order_community_instance_map.get(ord_key)
        if instance:
            handler = getattr(instance, "on_real_order_receive", None)

            if handler:
                loop: Optional[asyncio.AbstractEventLoop] = getattr(self, "_loop", None)
                # handle bound coroutine methods by checking __func__ fallback
                func_to_check = getattr(handler, "__func__", handler)
                if asyncio.iscoroutinefunction(func_to_check):
                    coro = handler(order_type, response)

                    if loop is not None and getattr(loop, "is_running", lambda: False)():
                        try:
                            asyncio.run_coroutine_threadsafe(coro, loop)
                        except Exception:
                            pg_logger.exception("Failed to schedule coroutine with run_coroutine_threadsafe")
                    else:
                        # try to create task on current running loop (if any)
                        try:
                            asyncio.create_task(coro)
                        except RuntimeError:
                            # no running loop at all; run the coroutine in a new thread
                            import threading

                            def _run_coro_in_thread(c):
                                try:
                                    asyncio.run(c)
                                except Exception:
                                    pg_logger.exception("Error running coroutine in fallback thread")

                            threading.Thread(target=_run_coro_in_thread, args=(coro,), daemon=True).start()
                else:
                    # synchronous handler: run in thread, prefer scheduling via loop
                    if loop is not None and getattr(loop, "is_running", lambda: False)():
                        try:
                            # schedule creation of a background task that runs the sync handler
                            loop.call_soon_threadsafe(asyncio.create_task, asyncio.to_thread(handler, order_type, response))
                        except Exception:
                            pg_logger.exception("Failed to schedule sync handler on loop; running in thread")
                            import threading

                            threading.Thread(target=handler, args=(order_type, response), daemon=True).start()
                    else:
                        # no loop available, run handler in its own thread
                        import threading

                        threading.Thread(target=handler, args=(order_type, response), daemon=True).start()
        else:
            # queue message until instance is registered
            self._pending_order_messages.setdefault(ord_key, []).append(response)

    def _order_type_from_response(self, bns_tp: str, ord_xct_ptn_code: str) -> Optional[OrderRealResponseType]:
        """Derive unified order_type string from an AS0/AS1 response-like object."""
        try:
            order_category_type: Optional[OrderRealResponseType] = None
            if bns_tp == "2":
                if ord_xct_ptn_code == "01":
                    order_category_type = "submitted_new_buy"
                elif ord_xct_ptn_code == "11":
                    order_category_type = "filled_new_buy"
                elif ord_xct_ptn_code == "03":
                    order_category_type = "cancel_request_buy"
                elif ord_xct_ptn_code == "12":
                    order_category_type = "modify_buy"
                elif ord_xct_ptn_code == "13":
                    order_category_type = "cancel_complete_buy"
                elif ord_xct_ptn_code == "14":
                    order_category_type = "reject_buy"
            elif bns_tp == "1":
                if ord_xct_ptn_code == "01":
                    order_category_type = "submitted_new_sell"
                elif ord_xct_ptn_code == "11":
                    order_category_type = "filled_new_sell"
                elif ord_xct_ptn_code == "03":
                    order_category_type = "cancel_request_sell"
                elif ord_xct_ptn_code == "12":
                    order_category_type = "modify_sell"
                elif ord_xct_ptn_code == "13":
                    order_category_type = "cancel_complete_sell"
                elif ord_xct_ptn_code == "14":
                    order_category_type = "reject_sell"
            return order_category_type
        except Exception:
            pg_logger.exception("Error computing order_category_type from response")
            return None

    def _futures_order_type(self, tr_cd: Optional[str], body: Dict[str, Any]) -> Optional[OrderRealResponseType]:
        """Map overseas futures real-time payloads to unified order type values."""

        if not body:
            return None

        side_code = str(body.get("s_b_ccd", "") or "").strip()
        is_buy = side_code == "2"

        def choose(buy: OrderRealResponseType, sell: OrderRealResponseType) -> OrderRealResponseType:
            return buy if is_buy else sell

        order_code = str(body.get("ordr_ccd", "") or "").strip()
        tr_cd = (tr_cd or "").upper().strip()

        if tr_cd == "TC1":
            return choose("submitted_new_buy", "submitted_new_sell")

        if tr_cd == "TC2":
            reject_code = str(body.get("rfsl_cd", "") or "").strip()
            if reject_code and reject_code not in {"0", "00"}:
                return choose("reject_buy", "reject_sell")

            if order_code in {"1", "01"}:
                return choose("modify_buy", "modify_sell")
            if order_code in {"2", "02"}:
                return choose("cancel_buy", "cancel_sell")
            return choose("submitted_new_buy", "submitted_new_sell")

        if tr_cd == "TC3":
            if order_code in {"2", "02"}:
                return choose("cancel_complete_buy", "cancel_complete_sell")
            return choose("filled_new_buy", "filled_new_sell")

        return None

    def _determine_order_type_from_payload(self, payload: Dict[str, Any]) -> Optional[OrderRealResponseType]:
        """Infer order type from a generic real-time payload for stocks or futures."""

        if not payload:
            return None

        body: Dict[str, Any] = payload.get("body") or {}
        header: Dict[str, Any] = payload.get("header") or {}
        tr_cd = header.get("tr_cd")

        if tr_cd and str(tr_cd).upper().startswith("AS"):
            return self._order_type_from_response(
                bns_tp=body.get("sBnsTp", ""),
                ord_xct_ptn_code=body.get("sOrdxctPtnCode", ""),
            )

        if tr_cd and str(tr_cd).upper().startswith("TC"):
            return self._futures_order_type(tr_cd, body)

        if "sBnsTp" in body or "sOrdxctPtnCode" in body:
            return self._order_type_from_response(
                bns_tp=body.get("sBnsTp", ""),
                ord_xct_ptn_code=body.get("sOrdxctPtnCode", ""),
            )

        if "s_b_ccd" in body:
            return self._futures_order_type(tr_cd, body)

        return None

    def _order_message_from_type(self, order_type: Optional[OrderRealResponseType]) -> str:
        """Provide human-friendly fallback messages for emitted order events."""

        message_map = {
            "submitted_new_buy": "주문 접수 완료",
            "submitted_new_sell": "주문 접수 완료",
            "filled_new_buy": "주문 체결 완료",
            "filled_new_sell": "주문 체결 완료",
            "cancel_request_buy": "주문 취소 접수",
            "cancel_request_sell": "주문 취소 접수",
            "modify_buy": "주문 정정 완료",
            "modify_sell": "주문 정정 완료",
            "cancel_complete_buy": "주문 취소 완료",
            "cancel_complete_sell": "주문 취소 완료",
            "reject_buy": "주문 거부됨",
            "reject_sell": "주문 거부됨",
        }

        return message_map.get(order_type, "주문 이벤트")
