from connexion.exceptions import ProblemException

from app.trace import TokenInfo, set_token_info


def decode_token(token: str) -> TokenInfo:
    # TODO: fix token verification
    token_info = TokenInfo.create(user={'id': 'test'})
    if not token_info or token_info.user.id is None:
        raise ProblemException(
            status=401,
            title='Provided token is not valid',
            detail='Provided token is not valid',
            ext={'code': 'Provided token is not valid'}
        )
    set_token_info(token_info)
    return token_info
