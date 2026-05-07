"""Pydantic models for LS Securities OpenAPI access-token issuance (접근토큰 발급).

POSTs an OAuth2-style ``client_credentials`` grant to obtain a Bearer access
token used for downstream LS Securities REST / WebSocket calls.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan, Phase 5 OAuth caveat):
    - ``grant_type`` and ``scope`` constants are LS-source-declared as fixed
      string literals; the plan flags LS OAuth handling as potentially
      diverging from standard OAuth2, so values are preserved verbatim with
      no inferred OAuth2 semantics.
    - ``token_type`` is LS-source-declared as ``Bearer``.
    - ``expires_in`` is the access-token lifetime in seconds per LS source;
      no exact lifetime value is asserted.
    - The request content-type is ``application/x-www-form-urlencoded`` per
      LS source; this is enforced at the request envelope level, not via
      field metadata.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import OAuthRequestHeader, OAuthResponseHeader, SetupOptions


class TokenRequestHeader(OAuthRequestHeader):
    """Token-issuance request header. Inherits the standard LS OAuth header schema."""
    pass


class TokenResponseHeader(OAuthResponseHeader):
    """Token-issuance response header. Inherits the standard LS OAuth header schema."""
    pass


class TokenInBlock(BaseModel):
    """tokenInBlock — input block for the access-token issuance request."""

    grant_type: Literal["client_credentials"] = Field(
        default="client_credentials",
        title="권한부여 Type (Grant type)",
        description="OAuth grant type. LS source declares this as fixed literal 'client_credentials'.",
        examples=["client_credentials"],
    )
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
    scope: Literal["oob"] = Field(
        default="oob",
        title="scope (Scope)",
        description="OAuth scope. LS source declares this as fixed literal 'oob'.",
        examples=["oob"],
    )


class TokenRequest(BaseModel):
    """Token-issuance request envelope."""

    header: TokenRequestHeader = TokenRequestHeader(content_type="application/x-www-form-urlencoded")
    body: TokenInBlock
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="token"
    )


class TokenOutBlock(BaseModel):
    """tokenOutBlock — access-token issuance response block."""

    access_token: str = Field(
        ...,
        title="접근토큰 (Access token)",
        description="Bearer access token used in subsequent LS Securities REST / WebSocket calls.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    expires_in: int = Field(
        ...,
        title="유효기간(초) (Lifetime in seconds)",
        description="Access-token lifetime in seconds per LS source. Exact value not asserted.",
        examples=[86400],
    )
    scope: Literal["oob"] = Field(
        ...,
        title="scope (Scope)",
        description="OAuth scope. LS source declares this as fixed literal 'oob'.",
        examples=["oob"],
    )
    token_type: Literal["Bearer"] = Field(
        ...,
        title="토큰 유형 (Token type)",
        description="Token type. LS source declares this as fixed literal 'Bearer'.",
        examples=["Bearer"],
    )


class TokenResponse(BaseModel):
    """Token-issuance response envelope."""

    header: Optional[TokenResponseHeader]
    block: Optional[TokenOutBlock]

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
