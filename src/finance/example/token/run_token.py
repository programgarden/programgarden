import asyncio
from dotenv import dotenv_values
from programgarden_finance.ls.oauth.generate_token import GenerateToken
from programgarden_core import pg_logger

from programgarden_finance.ls.oauth.generate_token.token.blocks import (
    TokenInBlock,
)

config = dotenv_values(".env")


async def test_req_token():
    response = GenerateToken().token(
        TokenInBlock(
            appkey=config["APPKEY_FUTURE"],
            appsecretkey=config["APPSECRET_FUTURE"],
        )
    )

    access_token = (await response.req_async()).block.access_token
    pg_logger.debug(f"Access Token: {access_token}")


if __name__ == "__main__":
    asyncio.run(test_req_token())
