from typing import Any

from core.config import settings
from core.exceptions import ConfigError, DatabaseError

try:
    import asyncpg
except Exception:  # pragma: no cover
    asyncpg = None


class PostgresDatabase:
    def __init__(self):
        if not settings.postgres_dsn:
            raise ConfigError("POSTGRES_DSN is not configured")
        if asyncpg is None:
            raise ConfigError("asyncpg is not installed")
        self._pool = None

    async def connect(self):
        try:
            self._pool = await asyncpg.create_pool(
                dsn=settings.postgres_dsn,
                min_size=settings.postgres_pool_min_size,
                max_size=settings.postgres_pool_max_size,
            )
        except Exception as exc:
            raise DatabaseError(f"Failed to connect PostgreSQL: {exc}") from exc

    async def disconnect(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def fetch(self, query: str, *args) -> list[dict[str, Any]]:
        if not self._pool:
            raise DatabaseError("Pool is not initialized")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(r) for r in rows]

    async def execute(self, query: str, *args) -> str:
        if not self._pool:
            raise DatabaseError("Pool is not initialized")
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)
