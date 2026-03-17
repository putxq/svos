import json
import aiosqlite

from core.config import settings


class AgentRegistry:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.sqlite_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('PRAGMA journal_mode=WAL;')
            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    sovereignty TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    task TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    passed_constitution INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
            await db.commit()

    async def register_agent(self, *, agent_id: str, name: str, agent_type: str, sovereignty: str, port: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('PRAGMA journal_mode=WAL;')
            await db.execute(
                '''
                INSERT INTO agents(agent_id, name, type, sovereignty, port, status)
                VALUES (?, ?, ?, ?, ?, 'registered')
                ''',
                (agent_id, name, agent_type, sovereignty, port),
            )
            await db.commit()

    async def get_agent(self, agent_id: str) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT agent_id, name, type, sovereignty, port, status FROM agents WHERE agent_id = ?',
                (agent_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                'agent_id': row[0],
                'name': row[1],
                'type': row[2],
                'sovereignty': row[3],
                'port': row[4],
                'status': row[5],
            }

    async def save_decision(self, *, agent_id: str, task: str, decision: str, passed_constitution: bool) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''
                INSERT INTO decisions(agent_id, task, decision, passed_constitution)
                VALUES (?, ?, ?, ?)
                ''',
                (agent_id, task, decision, 1 if passed_constitution else 0),
            )
            await db.commit()
