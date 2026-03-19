from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite

from core.contracts import RunCheckpoint


class RunStateRepository:
    def __init__(self, sqlite_path: str):
        self.sqlite_path = sqlite_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_run_state (
                    run_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    progress REAL NOT NULL,
                    note TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def upsert(self, checkpoint: RunCheckpoint) -> None:
        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute(
                """
                INSERT INTO agent_run_state (run_id, agent_id, state, progress, note, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                  state=excluded.state,
                  progress=excluded.progress,
                  note=excluded.note,
                  updated_at=excluded.updated_at
                """,
                (
                    checkpoint.run_id,
                    checkpoint.agent_id,
                    checkpoint.state,
                    checkpoint.progress,
                    checkpoint.note,
                    checkpoint.updated_at.isoformat(),
                ),
            )
            await db.commit()

    async def start(self, run_id: str, agent_id: str, note: str = "") -> None:
        await self.upsert(
            RunCheckpoint(
                run_id=run_id,
                agent_id=agent_id,
                state="created",
                progress=0.0,
                note=note,
            )
        )

    async def update(self, run_id: str, agent_id: str, state: str, progress: float, note: str = "") -> None:
        await self.upsert(
            RunCheckpoint(
                run_id=run_id,
                agent_id=agent_id,
                state=state,
                progress=progress,
                note=note,
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def finish(self, run_id: str, agent_id: str, success: bool, note: str = "") -> None:
        await self.upsert(
            RunCheckpoint(
                run_id=run_id,
                agent_id=agent_id,
                state="done" if success else "failed",
                progress=1.0,
                note=note,
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def get(self, run_id: str) -> dict | None:
        async with aiosqlite.connect(self.sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT run_id, agent_id, state, progress, note, updated_at FROM agent_run_state WHERE run_id = ?",
                (run_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None
