from .token import Token
from .token.blocks import TokenInBlock, TokenRequest, TokenRequestHeader, TokenResponseHeader
from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias


class GenerateToken(metaclass=EnforceKoreanAliasMeta):

    @require_korean_alias
    def token(
        self,
        body: TokenInBlock
    ):
        """
        LS openAPI의 토큰을 생성합니다.
        Args:
            body (TokenInBlock): 토큰 생성을 위한 입력 데이터입니다.
        Returns:
            Token: 토큰 생성 결과를 포함하는 Token 인스턴스
        """

        request_data = TokenRequest(
            body=body,
        )

        return Token(request_data)

    접근토큰발급 = token
    접근토큰발급.__doc__ = "토큰을 생성합니다."


__all__ = [
    GenerateToken,
    TokenInBlock,
    TokenRequest,
    TokenRequestHeader,
    TokenResponseHeader,
    Token
]
