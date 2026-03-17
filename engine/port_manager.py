import aiosqlite
from core.config import settings
from core.exceptions import PortReservationError


class PortManager:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.sqlite_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('PRAGMA journal_mode=WAL;')
            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS reserved_ports (
                    port INTEGER PRIMARY KEY,
                    owner TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
            await db.commit()

    async def reserve(self, owner: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('PRAGMA journal_mode=WAL;')
            for port in range(settings.min_port, settings.max_port + 1):
                try:
                    await db.execute('INSERT INTO reserved_ports(port, owner) VALUES (?, ?)', (port, owner))
                    await db.commit()
                    return port
                except Exception:
                    continue
        raise PortReservationError('No free ports available in configured range')

    async def release(self, port: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM reserved_ports WHERE port = ?', (port,))
            await db.commit()
