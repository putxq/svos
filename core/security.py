from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from core.config import settings


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(api_key_header)):
    # Development mode: no key configured -> allow requests.
    if not settings.api_key:
        return

    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
