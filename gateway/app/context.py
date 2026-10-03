from fastapi import Header

from . import config


async def get_context(x_user_id: str = Header(default=config.DEFAULT_USER_ID)) -> dict:
    return {"current_user_id": x_user_id}
