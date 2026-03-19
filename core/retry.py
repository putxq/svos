import asyncio
from collections.abc import Callable
from functools import wraps


def async_retry(
    attempts: int = 3,
    delay_seconds: float = 0.5,
    backoff: float = 2.0,
    retry_exceptions: tuple[type[BaseException], ...] = (Exception,),
):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            wait = delay_seconds
            for _ in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except retry_exceptions as exc:
                    last_error = exc
                    await asyncio.sleep(wait)
                    wait *= backoff
            raise last_error

        return wrapper

    return decorator
