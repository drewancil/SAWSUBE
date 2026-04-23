"""Meta router (history, stats) tests."""
from __future__ import annotations


async def test_stats_empty(app_client):
    r = await app_client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["images"] == 0
    assert body["tvs"] == 0
    assert body["schedules_active"] == 0


async def test_stats_after_upload(app_client, jpeg_bytes):
    await app_client.post("/api/images/upload",
                         files={"files": ("a.jpg", jpeg_bytes(), "image/jpeg")})
    r = await app_client.get("/api/stats")
    body = r.json()
    assert body["images"] == 1
    assert body["storage_bytes"] > 0


async def test_history_empty(app_client):
    r = await app_client.get("/api/history")
    assert r.status_code == 200
    assert r.json() == []


async def test_history_filtered(app_client):
    from backend.database import SessionLocal
    from backend.models.history import History
    from backend.models.tv import TV
    from backend.models.image import Image
    async with SessionLocal() as s:
        s.add(TV(name="A", ip="10.0.0.1"))
        s.add(TV(name="B", ip="10.0.0.2"))
        s.add(Image(local_path="/x/1.jpg", filename="1.jpg", file_hash="h1",
                    file_size=10, width=1, height=1))
        s.add(Image(local_path="/x/2.jpg", filename="2.jpg", file_hash="h2",
                    file_size=10, width=1, height=1))
        await s.commit()
        s.add(History(tv_id=1, image_id=1, trigger="manual"))
        s.add(History(tv_id=2, image_id=2, trigger="schedule"))
        await s.commit()
    r = await app_client.get("/api/history?tv_id=1")
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["tv_id"] == 1
