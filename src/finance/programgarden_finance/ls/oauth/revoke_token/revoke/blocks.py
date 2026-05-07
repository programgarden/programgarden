"""Pydantic models for LS Securities OpenAPI access-token revocation (접근토큰 폐기).

Revokes a previously-issued access token. Inherits the OAuth header chain
from ``oauth.generate_token.token``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan, Phase 5 OAuth caveat):
    - ``token_type_hint`` 2-way ('access_token' / 'refresh_token') is
      LS-source-declared verbatim. Whether refresh tokens are actually
      supported is not asserted here — preserved as the source declares.
    - ``code`` / ``message`` semantics in the response block are LS-defined
      and not declared in detail in the available source.
"""

from typing import Dict, Literal, Optional

from programgarden_finance.ls.oauth.generate_token import (
    TokenRequestHeader,
    TokenResponseHeader,
)
from pydantic import BaseModel, Field, PrivateAttr
from requests import Response


class RevokeRequestHeader(TokenRequestHeader):
    """Revoke request header. Inherits the LS OAuth header schema."""
    pass


class RevokeResponseHeader(TokenResponseHeader):
    """Revoke response header. Inherits the LS OAuth header schema."""
    pass


class RevokeInBlock(BaseModel):
    """revokeInBlock — input block for the access-token revocation request."""

    appkey: str = Field(
        ...,
        title="앱Key (App key)",
        description="Customer-issued LS Securities app key.",
        examples=["YOUR_APP_KEY"],
    )
    appsecretkey: str = Field(
        ...,
        title="앱비밀Key (App secret key)",
        description="Customer-issued LS Securities app secret key.",
        examples=["YOUR_APP_SECRET"],
    )
    token: str = Field(
        ...,
        title="접근토큰 (Access token)",
        description="Bearer access token to revoke.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type_hint: Literal["access_token", "refresh_token"] = Field(
        ...,
        title="토큰 유형 hint (Token type hint)",
        description="Token type hint. LS source declares 2-way: 'access_token' or 'refresh_token'. Refresh-token support is not asserted; preserved verbatim per source.",
        examples=["access_token"],
    )


class RevokeRequest(BaseModel):
    """Revoke request envelope."""

    header: RevokeRequestHeader
    body: Dict[Literal["revokeInBlock"], RevokeInBlock]


class RevokeOutBlock(BaseModel):
    """revokeOutBlock — access-token revocation response block."""

    code: int = Field(
        ...,
        title="응답코드 (Response code)",
        description="LS-defined response code. Code semantics not declared in detail in the available source.",
        examples=[0, 200],
    )
    message: str = Field(
        ...,
        title="응답메시지 (Response message)",
        description="LS-defined response message.",
        examples=["success"],
    )


class RevokeResponse(BaseModel):
    """Revoke response envelope."""

    header: Optional[RevokeResponseHeader]
    block: Optional[RevokeOutBlock]

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
