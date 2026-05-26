from fastapi import Header, HTTPException


async def get_current_user_id(x_user_id: int = Header(alias="X-User-Id")) -> int:
    """
    User identity injected by Tuan's auth gateway (T2-M3).
    The gateway validates the JWT and forwards X-User-Id to downstream services.
    Replace the Header dependency with JWT extraction once T2-M3 ships.
    """
    if x_user_id <= 0:
        raise HTTPException(status_code=401, detail="Invalid user identity")
    return x_user_id
