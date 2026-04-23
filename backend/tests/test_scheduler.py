"""Scheduler logic tests."""
from __future__ import annotations
from datetime import datetime, time


def test_in_window_full_week(tmp_workdir):
    from backend.services.scheduler import _in_window
    from backend.models.schedule import Schedule
    s = Schedule(tv_id=1, days_of_week="0,1,2,3,4,5,6")
    # any datetime should match
    assert _in_window(s, datetime(2026, 1, 5, 13, 0)) is True  # Monday


def test_in_window_filter_days(tmp_workdir):
    from backend.services.scheduler import _in_window
    from backend.models.schedule import Schedule
    s = Schedule(tv_id=1, days_of_week="5,6")  # Sat, Sun only
    assert _in_window(s, datetime(2026, 1, 5, 12, 0)) is False  # Mon
    assert _in_window(s, datetime(2026, 1, 10, 12, 0)) is True  # Sat


def test_in_window_time_range(tmp_workdir):
    from backend.services.scheduler import _in_window
    from backend.models.schedule import Schedule
    s = Schedule(tv_id=1, days_of_week="0,1,2,3,4,5,6",
                 time_from=time(9, 0), time_to=time(17, 0))
    assert _in_window(s, datetime(2026, 1, 5, 12, 0)) is True
    assert _in_window(s, datetime(2026, 1, 5, 8, 0)) is False
    assert _in_window(s, datetime(2026, 1, 5, 18, 0)) is False


def test_in_window_midnight_crossover(tmp_workdir):
    from backend.services.scheduler import _in_window
    from backend.models.schedule import Schedule
    s = Schedule(tv_id=1, days_of_week="0,1,2,3,4,5,6",
                 time_from=time(22, 0), time_to=time(6, 0))
    assert _in_window(s, datetime(2026, 1, 5, 23, 0)) is True
    assert _in_window(s, datetime(2026, 1, 5, 5, 0)) is True
    assert _in_window(s, datetime(2026, 1, 5, 12, 0)) is False


async def test_eligible_excludes_recent(tmp_workdir):
    from backend.database import init_db, SessionLocal
    from backend.models.image import Image
    from backend.models.history import History
    from backend.models.schedule import Schedule
    from backend.models.tv import TV
    from backend.services.scheduler import _eligible_images

    await init_db()
    async with SessionLocal() as s:
        s.add(TV(name="X", ip="10.0.0.1"))
        for i in range(10):
            s.add(Image(local_path=f"/x/{i}.jpg", filename=f"{i}.jpg",
                        file_hash=f"h{i}", file_size=100, width=10, height=10))
        await s.commit()
        # mark images 1..5 as recently shown for tv_id=1
        for i in range(1, 6):
            s.add(History(tv_id=1, image_id=i, trigger="manual"))
        await s.commit()
        sched = Schedule(tv_id=1, mode="random", days_of_week="0,1,2,3,4,5,6")
        eligible = await _eligible_images(s, sched)
        ids = sorted([x.id for x in eligible])
        # Recent 5 excluded (since pool >5 remain)
        assert all(i not in ids for i in [1, 2, 3, 4, 5])


async def test_eligible_recent_pool_too_small(tmp_workdir):
    """When excluding recent would empty pool, return all."""
    from backend.database import init_db, SessionLocal
    from backend.models.image import Image
    from backend.models.history import History
    from backend.models.schedule import Schedule
    from backend.models.tv import TV
    from backend.services.scheduler import _eligible_images

    await init_db()
    async with SessionLocal() as s:
        s.add(TV(name="X", ip="10.0.0.1"))
        for i in range(3):
            s.add(Image(local_path=f"/x/{i}.jpg", filename=f"{i}.jpg",
                        file_hash=f"h{i}", file_size=100, width=10, height=10))
        await s.commit()
        for i in range(1, 4):
            s.add(History(tv_id=1, image_id=i, trigger="manual"))
        await s.commit()
        sched = Schedule(tv_id=1, mode="random", days_of_week="0,1,2,3,4,5,6")
        eligible = await _eligible_images(s, sched)
        assert len(eligible) == 3  # fallback to all
