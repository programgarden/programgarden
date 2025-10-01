import asyncio
import threading
from typing import Any, Dict, List, Optional, Union
from programgarden_finance import LS, AS0, AS1, AS2, AS3, AS4
from programgarden_core import (
    OrderRealResponseType, SystemType, pg_logger,
    BaseOrderOverseasStock
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

        company = system.get("securities", {}).get("company", None)
        if len(system.get("orders", [])) > 0 and company == "ls":
            self.buy_sell_order_real = LS.get_instance().overseas_stock().real()
            await self.buy_sell_order_real.connect()
            # store the currently running event loop so synchronous callbacks
            # (from the LS library) can schedule coroutines back onto it
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # no running loop (should not happen here because we're in async fn)
                self._loop = None
            self.buy_sell_order_real.AS0().on_as0_message(listener=self._as0_message_dispatcher)
            self.buy_sell_order_real.AS1().on_as1_message(listener=self._as1_message_dispatcher)
            self.buy_sell_order_real.AS2().on_as2_message(listener=self._as2_message_dispatcher)
            self.buy_sell_order_real.AS3().on_as3_message(listener=self._as3_message_dispatcher)
            self.buy_sell_order_real.AS4().on_as4_message(listener=self._as4_message_dispatcher)

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
            self.__dispatch_real_order_message(ord_key, response.model_dump())

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 접수 완료",
                "response": response.model_dump(),
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
            self.__dispatch_real_order_message(ord_key, response.model_dump())

            if response.body.sUnercQty == 0:
                # 주문이 모두 체결되었으므로 더 이상 메시지를 받을 필요가 없음
                self._order_community_instance_map.pop(ord_key, None)

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 체결 완료",
                "response": response.model_dump(),
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
            self.__dispatch_real_order_message(ord_key, response.model_dump())

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 정정 완료",
                "response": response.model_dump(),
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

            self.__dispatch_real_order_message(ord_key, response.model_dump())

            self._order_community_instance_map.pop(ord_key, None)

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 취소 완료",
                "response": response.model_dump(),
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
            self.__dispatch_real_order_message(ord_key, response.model_dump())

            self._order_community_instance_map.pop(ord_key, None)

            order_type = self._order_type_from_response(
                bns_tp=response.body.sBnsTp,
                ord_xct_ptn_code=response.body.sOrdxctPtnCode,
            )
            pg_listener.emit_real_order({
                "order_type": order_type,
                "message": "주문 거부됨",
                "response": response.model_dump(),
            })
        except Exception:
            pg_logger.exception("Error in AS4 dispatcher")

    async def send_data_community_instance(
            self,
            ordNo: str,
            community_instance: Optional[Union[BaseOrderOverseasStock]]
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
                    order_type = self._order_type_from_response(
                        bns_tp=real_order_response.get("body", {}).get("sBnsTp", ""),
                        ord_xct_ptn_code=real_order_response.get("body", {}).get("sOrdxctPtnCode", ""),
                    )
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

    def __dispatch_real_order_message(self, ord_key: str, response: Dict[str, Any]) -> None:
        """Dispatch order response to the registered community instance or queue it.

        This centralizes async/sync handler delivery and pending queueing.

        If we have a stored event loop (the main async loop started
        in `real_order_websockets`), schedule coroutines/thread jobs
        safely from synchronous callback contexts. Otherwise try to
        schedule on the current loop or fall back to a thread.
        """

        order_type = self._order_type_from_response(
            bns_tp=response.get("body", {}).get("sBnsTp", ""),
            ord_xct_ptn_code=response.get("body", {}).get("sOrdxctPtnCode", ""),
        )

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
