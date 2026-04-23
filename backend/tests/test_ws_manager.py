"""ws_manager broadcast tests."""
from __future__ import annotations
import pytest


class FakeWS:
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[str] = []
        self.fail = fail

    async def send_text(self, data: str) -> None:
        if self.fail:
            raise RuntimeError("send fail")
        self.sent.append(data)

    async def accept(self) -> None:
        pass


async def test_broadcast_no_clients(tmp_workdir):
    from backend.services.ws_manager import WSManager
    m = WSManager()
    await m.broadcast({"hello": 1})  # must not raise


async def test_broadcast_to_clients(tmp_workdir):
    from backend.services.ws_manager import WSManager
    m = WSManager()
    a, b = FakeWS(), FakeWS()
    m.clients.update({a, b})
    await m.broadcast({"x": 1})
    assert len(a.sent) == 1 and len(b.sent) == 1
    assert '"x": 1' in a.sent[0]


async def test_broadcast_drops_dead_client(tmp_workdir):
    from backend.services.ws_manager import WSManager
    m = WSManager()
    good, bad = FakeWS(), FakeWS(fail=True)
    m.clients.update({good, bad})
    await m.broadcast({"y": 2})
    assert bad not in m.clients
    assert good in m.clients


async def test_broadcast_serialises_datetime(tmp_workdir):
    from backend.services.ws_manager import WSManager
    from datetime import datetime
    m = WSManager()
    a = FakeWS()
    m.clients.add(a)
    await m.broadcast({"when": datetime(2026, 1, 1)})
    assert "2026" in a.sent[0]  # default=str converted
