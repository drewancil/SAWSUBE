"""Schedule router tests."""
from __future__ import annotations
from unittest.mock import AsyncMock, patch


async def _add_tv(c) -> int:
    r = await c.post("/api/tvs", json={"name": "T", "ip": "10.0.0.1"})
    return r.json()["id"]


async def test_create_list_update_delete(app_client):
    tv_id = await _add_tv(app_client)
    with patch("backend.routers.schedule.install_schedule", new=AsyncMock(return_value=None)), \
         patch("backend.routers.schedule.remove_schedule", new=AsyncMock(return_value=None)):
        r = await app_client.post("/api/schedules",
                                  json={"tv_id": tv_id, "name": "Daily", "mode": "random",
                                        "interval_mins": 30, "days_of_week": "0,1,2,3,4"})
        assert r.status_code == 200
        sid = r.json()["id"]

        r = await app_client.get("/api/schedules")
        assert len(r.json()) == 1

        r = await app_client.put(f"/api/schedules/{sid}",
                                 json={"tv_id": tv_id, "name": "Updated", "mode": "sequential",
                                       "interval_mins": 15, "days_of_week": "0,1,2,3,4"})
        assert r.json()["name"] == "Updated"
        assert r.json()["mode"] == "sequential"

        r = await app_client.post(f"/api/schedules/{sid}/toggle")
        assert r.json()["is_active"] is False

        r = await app_client.delete(f"/api/schedules/{sid}")
        assert r.json()["ok"] is True
        r = await app_client.get("/api/schedules")
        assert r.json() == []


async def test_update_404(app_client):
    r = await app_client.put("/api/schedules/9999",
                             json={"tv_id": 1, "name": "x", "mode": "random",
                                   "interval_mins": 1, "days_of_week": "0"})
    assert r.status_code == 404


async def test_delete_404(app_client):
    r = await app_client.delete("/api/schedules/9999")
    assert r.status_code == 404


async def test_trigger_calls_fire(app_client):
    with patch("backend.routers.schedule.fire_schedule", new=AsyncMock(return_value=None)) as m:
        r = await app_client.post("/api/schedules/42/trigger")
        assert r.status_code == 200
        m.assert_awaited_once_with(42)
