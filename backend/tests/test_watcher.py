"""Watcher / scan_folder_now tests."""
from __future__ import annotations
import os
import asyncio
import shutil


async def test_scan_folder_now_empty(tmp_workdir, tmp_path):
    from backend.services.watcher import scan_folder_now
    from backend.database import init_db
    await init_db()
    p = tmp_path / "empty"
    p.mkdir()
    n = await scan_folder_now(str(p))
    assert n == 0


async def test_scan_folder_now_ingests_jpegs(tmp_workdir, tmp_path, make_jpeg):
    from backend.services.watcher import scan_folder_now
    from backend.database import init_db, SessionLocal
    from backend.models.image import Image
    from sqlalchemy import select
    await init_db()
    folder = tmp_path / "imgs"
    folder.mkdir()
    # Create real JPEGs inside the folder
    for i in range(3):
        src = make_jpeg(f"src_{i}.jpg", color=(i * 30, 0, 0))
        shutil.copy(src, folder / f"img_{i}.jpg")
    n = await scan_folder_now(str(folder))
    assert n == 3
    async with SessionLocal() as s:
        rows = (await s.execute(select(Image))).scalars().all()
        assert len(rows) == 3


async def test_scan_folder_now_dedupes(tmp_workdir, tmp_path, make_jpeg):
    from backend.services.watcher import scan_folder_now
    from backend.database import init_db
    await init_db()
    folder = tmp_path / "dup"
    folder.mkdir()
    src = make_jpeg("a.jpg", color=(50, 50, 50))
    shutil.copy(src, folder / "a.jpg")
    shutil.copy(src, folder / "b.jpg")  # identical content → same hash
    n = await scan_folder_now(str(folder))
    assert n == 1


async def test_scan_folder_now_missing_dir(tmp_workdir):
    from backend.services.watcher import scan_folder_now
    n = await scan_folder_now("/no/such/folder/xyz")
    assert n == 0


async def test_handler_debounce_cancels_prior(tmp_workdir):
    """_Handler._enqueue must cancel prior pending task for same path."""
    from backend.services.watcher import _Handler
    loop = asyncio.get_running_loop()
    h = _Handler(loop, folder_id=1)
    # Pre-populate a pending task to verify it's cancelled
    async def long_op():
        await asyncio.sleep(60)
    t1 = asyncio.ensure_future(long_op())
    h._pending["/x/a.jpg"] = t1
    # Trigger another enqueue for same path — should cancel t1 and replace
    h._enqueue("/x/a.jpg")
    # Allow the call_soon_threadsafe scheduled callback to run
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert t1.cancelled() or t1.done()
    # Cleanup any new pending
    new_task = h._pending.get("/x/a.jpg")
    if new_task and not new_task.done():
        new_task.cancel()
        try:
            await new_task
        except (asyncio.CancelledError, Exception):
            pass


def test_handler_ignores_unsupported(tmp_workdir):
    from backend.services.watcher import _Handler
    import asyncio as _a
    loop = _a.new_event_loop()
    try:
        h = _Handler(loop, folder_id=1)
        h._enqueue("/x/file.txt")  # unsupported
        # Drain pending callbacks then check map empty
        loop.call_soon(loop.stop)
        loop.run_forever()
        assert "/x/file.txt" not in h._pending
    finally:
        loop.close()
