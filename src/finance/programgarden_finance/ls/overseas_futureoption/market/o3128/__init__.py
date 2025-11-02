import aiohttp
import asyncio
import time
from typing import Callable, Optional, Dict, Any
import requests

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    O3128InBlock,
    O3128OutBlock,
    O3128OutBlock1,
    O3128Request,
    O3128Response,
    O3128ResponseHeader,
)
from ....tr_base import TRRequestAbstract, OccursReqAbstract
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus

from programgarden_core.logs import pg_logger


class TrO3128(TRRequestAbstract, OccursReqAbstract):
    """해외선물옵션 차트 일주월 조회 클래스입니다."""

    def __init__(
        self,
        request_data: O3128Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3128Request):
            raise TrRequestDataNotFoundException()

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> O3128Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("o3128OutBlock")
        block1_data = resp_json.get("o3128OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = O3128ResponseHeader.model_validate(resp_headers)

        parsed_block = None
        parsed_block1: list[O3128OutBlock1] = []
        if exc is None and not is_error_status:
            if block_data is not None:
                parsed_block = O3128OutBlock.model_validate(block_data)
            parsed_block1 = [O3128OutBlock1.model_validate(item) for item in block1_data]

        error_msg = ""
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"o3128 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"o3128 request failed with status: {error_msg}")

        result = O3128Response(
            header=header,
            block=parsed_block,
            block1=parsed_block1,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> O3128Response:
        try:
            resp, resp_json, resp_headers = self.execute_sync(
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            return self._build_response(resp, resp_json, resp_headers, None)

        except requests.RequestException as e:
            return self._build_response(None, None, None, e)

        except Exception as e:
            return self._build_response(None, None, None, e)

    async def req_async(self) -> O3128Response:
        async with aiohttp.ClientSession() as session:
            return await self._req_async_with_session(session)

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> O3128Response:
        try:
            resp, resp_json, resp_headers = await self.execute_async_with_session(
                session=session,
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            return self._build_response(resp, resp_json, resp_headers, None)

        except aiohttp.ClientError as e:
            return self._build_response(None, None, None, e)

        except Exception as e:
            return self._build_response(None, None, None, e)

    def occurs_req(self, callback: Optional[Callable[[Optional[O3128Response], RequestStatus], None]] = None, delay: int = 1) -> list[O3128Response]:
        results: list[O3128Response] = []

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
                # continuous key for o3128 uses cts_date
                self.request_data.body["o3128InBlock"].cts_date = response.block.cts_date

            response = self.req()

            if response.error_msg is not None:
                callback and callback(response, RequestStatus.FAIL)
                break

            results.append(response)
            callback and callback(response, RequestStatus.RESPONSE)

        callback and callback(None, RequestStatus.COMPLETE)
        return results

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[O3128Response], RequestStatus], None]] = None, delay: int = 1) -> list[O3128Response]:
        results: list[O3128Response] = []

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
                    self.request_data.body["o3128InBlock"].cts_date = response.block.cts_date

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
    TrO3128,
    O3128InBlock,
    O3128OutBlock,
    O3128OutBlock1,
    O3128Request,
    O3128Response,
    O3128ResponseHeader,
]
