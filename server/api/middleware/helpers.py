from etebase_fastapi.dependencies import get_authenticated_user
from asgiref.sync import sync_to_async
from server.api.billing import calculate_limits


@sync_to_async()
def get_user_is_collab(key):
    user = get_authenticated_user(key)
    return user.userprofile.is_collaborator


@sync_to_async()
def get_team_limits(key):
    user = get_authenticated_user(key)
    return calculate_limits(user.team)


def get_key_from_headers(headers):
    auth_list = [v[1].decode("utf-8") for i, v in enumerate(headers) if v[0] == b"authorization"]
    if len(auth_list):
        return auth_list.pop()
    else:
        return None
