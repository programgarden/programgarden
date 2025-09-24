import aiohttp
import asyncio
import time
from typing import Callable, Optional
import requests

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    O3137InBlock,
    O3137OutBlock,
    O3137OutBlock1,
    O3137Request,
    O3137Response,
    O3137ResponseHeader,
)
from ....tr_base import TRRequestAbstract, OccursReqAbstract
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus

from programgarden_core.logs import pg_logger


class TrO3137(TRRequestAbstract, OccursReqAbstract):
    """해외선물옵션 차트 NTick 체결 조회 클래스입니다."""

    def __init__(
        self,
        request_data: O3137Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3137Request):
            raise TrRequestDataNotFoundException()

    def req(self) -> O3137Response:
        try:
            resp, resp_json, resp_headers = self.execute_sync(
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            result = O3137Response(
                header=O3137ResponseHeader.model_validate(resp_headers),
                block=O3137OutBlock.model_validate(resp_json.get("o3137OutBlock", None)) if resp_json.get("o3137OutBlock") is not None else None,
                block1=[O3137OutBlock1.model_validate(item) for item in resp_json.get("o3137OutBlock1", [])],
                rsp_cd=resp_json.get("rsp_cd", ""),
                rsp_msg=resp_json.get("rsp_msg", ""),
            )
            result.raw_data = resp
            return result

        except requests.RequestException as e:
            pg_logger.error(f"o3137 요청 실패: {e}")
            return O3137Response(
                header=None,
                block=None,
                block1=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

        except Exception as e:
            pg_logger.error(f"o3137 요청 중 예외 발생: {e}")
            return O3137Response(
                header=None,
                block=None,
                block1=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

    async def req_async(self) -> O3137Response:
        async with aiohttp.ClientSession() as session:
            return await self._req_async_with_session(session)

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> O3137Response:
        try:
            resp, resp_json, resp_headers = await self.execute_async_with_session(
                session=session,
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            result = O3137Response(
                header=O3137ResponseHeader.model_validate(resp_headers),
                block=O3137OutBlock.model_validate(resp_json.get("o3137OutBlock", None)) if resp_json.get("o3137OutBlock") is not None else None,
                block1=[O3137OutBlock1.model_validate(item) for item in resp_json.get("o3137OutBlock1", [])],
                rsp_cd=resp_json.get("rsp_cd", ""),
                rsp_msg=resp_json.get("rsp_msg", ""),
            )
            result.raw_data = resp
            return result

        except aiohttp.ClientError as e:
            pg_logger.error(f"o3137 비동기 요청 실패: {e}")
            return O3137Response(
                header=None,
                block=None,
                block1=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

        except Exception as e:
            pg_logger.error(f"o3137 비동기 요청 중 예외 발생: {e}")
            return O3137Response(
                header=None,
                block=None,
                block1=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

    def occurs_req(self, callback: Optional[Callable[[Optional[O3137Response], RequestStatus], None]] = None, delay: int = 1) -> list[O3137Response]:
        results: list[O3137Response] = []

        callback and callback(None, RequestStatus.REQUEST)
        response = self.req()
        callback and callback(response, RequestStatus.RESPONSE)
        results.append(response)

        while getattr(response.header, "tr_cont", "N") == "Y":
            pg_logger.debug(f"계속 조회 중... {response.header.tr_cont}")
            callback and callback(response, RequestStatus.OCCURS_REQUEST)

            time.sleep(delay)

            self.request_data.header.tr_cont_key = response.header.tr_cont_key
            self.request_data.header.tr_cont = response.header.tr_cont
            if response.block is not None:
                self.request_data.body["o3137InBlock"].cts_seq = response.block.cts_seq
                self.request_data.body["o3137InBlock"].cts_daygb = response.block.cts_daygb

            response = self.req()

            if response.error_msg is not None:
                callback and callback(response, RequestStatus.FAIL)
                break

            results.append(response)
            callback and callback(response, RequestStatus.RESPONSE)

        callback and callback(None, RequestStatus.COMPLETE)
        return results

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[O3137Response], RequestStatus], None]] = None, delay: int = 1) -> list[O3137Response]:
        results: list[O3137Response] = []

        async with aiohttp.ClientSession() as session:
            callback and callback(None, RequestStatus.REQUEST)
            response = await self._req_async_with_session(session)
            callback and callback(response, RequestStatus.RESPONSE)

            results.append(response)

            while getattr(response.header, "tr_cont", "N") == "Y":
                pg_logger.debug("계속 조회 중...")
                callback and callback(response, RequestStatus.OCCURS_REQUEST)

                await asyncio.sleep(delay)

                self.request_data.header.tr_cont_key = response.header.tr_cont_key
                self.request_data.header.tr_cont = response.header.tr_cont
                if response.block is not None:
                    self.request_data.body["o3137InBlock"].cts_seq = response.block.cts_seq
                    self.request_data.body["o3137InBlock"].cts_daygb = response.block.cts_daygb

                response = await self._req_async_with_session(session)

                if response.error_msg is not None:
                    callback and callback(response, RequestStatus.FAIL)
                    break

                results.append(response)
                callback and callback(response, RequestStatus.RESPONSE)

            callback and callback(None, RequestStatus.COMPLETE)
            await session.close()
            callback and callback(None, RequestStatus.CLOSE)
            return results


__all__ = [
    TrO3137,
    O3137InBlock,
    O3137OutBlock,
    O3137OutBlock1,
    O3137Request,
    O3137Response,
    O3137ResponseHeader,
]
