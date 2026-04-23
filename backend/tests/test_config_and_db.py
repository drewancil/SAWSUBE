"""Config and database init tests."""
from __future__ import annotations


def test_settings_defaults(tmp_workdir):
    from backend.config import settings
    assert settings.DB_PATH.endswith("sawsube.db")
    assert "sawsube" in settings.REDDIT_USER_AGENT.lower()


async def test_init_db_idempotent(tmp_workdir):
    from backend.database import init_db
    await init_db()
    await init_db()  # second call must not raise


async def test_foreign_keys_enabled(tmp_workdir):
    """SQLite FK pragma must be on in every session."""
    from backend.database import init_db, SessionLocal
    from sqlalchemy import text
    await init_db()
    async with SessionLocal() as s:
        r = await s.execute(text("PRAGMA foreign_keys"))
        assert r.scalar_one() == 1


async def test_get_session_yields_session(tmp_workdir):
    from backend.database import init_db, get_session
    from sqlalchemy.ext.asyncio import AsyncSession
    await init_db()
    gen = get_session()
    s = await gen.__anext__()
    try:
        assert isinstance(s, AsyncSession)
    finally:
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass
