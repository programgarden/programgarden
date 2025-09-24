import aiohttp
import requests

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    TokenRequest,
    TokenResponse,
    TokenRequestHeader,
    TokenResponseHeader,
    TokenOutBlock
)
from ....tr_base import TRRequestAbstract
from ....config import URLS
from programgarden_core.logs import pg_logger


class Token(TRRequestAbstract):
    """
    접근 토큰을 발급받기 위한 요청을 처리합니다.
    """

    def __init__(
        self,
        request_data: TokenRequest,
    ):
        """
        TrG3190 생성자

        Args:
            request_data (TokenRequest): 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, TokenRequest):
            raise TrRequestDataNotFoundException()

    async def req_async(self) -> TokenResponse:
        try:
            if self.on_rate_limit == "stop":
                if self.is_rate_limited():
                    raise ValueError("Rate limit exceeded")
                await self.record_request_async()
            else:  # wait
                await self.wait_until_available_async()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=URLS.OAUTH_URL,
                    headers=self.request_data.header.model_dump(by_alias=True),
                    data=self.request_data.body.model_dump(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response.raise_for_status()
                    raw = await response.json()

                    return TokenResponse(
                        header=TokenResponseHeader.model_validate(response.headers),
                        block=TokenOutBlock.model_validate(raw) if raw is not None else None,
                    )

        except aiohttp.ClientError as e:
            pg_logger.error(f"Token 요청 실패: {e}")

            return TokenResponse(
                header=None,
                block=None,
                error_msg=str(e),
            )

        except Exception as e:
            pg_logger.error(f"Token 요청 중 예외 발생: {e}")

            return TokenResponse(
                header=None,
                block=None,
                error_msg=str(e),
            )

    def req(self) -> TokenResponse:
        try:
            if self.on_rate_limit == "stop":
                if self.is_rate_limited():
                    raise ValueError("Rate limit exceeded")
                self.record_request()
            else:
                self.wait_until_available()

            # Set the content type in headers if not already set
            headers = self.request_data.header.model_dump(by_alias=True)
            response = requests.post(
                url=URLS.OAUTH_URL,
                headers=headers,
                data=self.request_data.body.model_dump(),
                timeout=10,
            )

            response.raise_for_status()

            raw = response.json()

            result = TokenResponse(
                header=TokenResponseHeader.model_validate(response.headers),
                block=TokenOutBlock.model_validate(raw) if raw is not None else None,
            )
            result.raw_data = response

            return result

        except requests.RequestException as e:
            pg_logger.error(f"Token 요청 실패: {e}")

            return TokenResponse(
                header=None,
                block=None,
                error_msg=str(e),
            )

        except Exception as e:
            pg_logger.error(f"Token 요청 중 예외 발생: {e}")

            return TokenResponse(
                header=None,
                block=None,
                error_msg=str(e),
            )


__all__ = [
    Token,
    TokenRequest,
    TokenResponse,
    TokenRequestHeader,
    TokenResponseHeader,
]
