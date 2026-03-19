import asyncio
from pathlib import Path

from infrastructure.run_state_repository import RunStateRepository


def test_run_state_repository_lifecycle(tmp_path: Path):
    db = tmp_path / "runstate.db"

    async def _run():
        repo = RunStateRepository(str(db))
        await repo.init()
        await repo.start("r-1", "board", note="created")
        await repo.update("r-1", "board", "running", 0.4, note="working")
        await repo.finish("r-1", "board", success=True, note="done")
        row = await repo.get("r-1")
        assert row is not None
        assert row["state"] == "done"
        assert float(row["progress"]) == 1.0

    asyncio.run(_run())
