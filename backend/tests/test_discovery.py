"""Discovery service tests (probe + ssdp_scan with mocks)."""
from __future__ import annotations
import socket
from unittest.mock import AsyncMock, patch, MagicMock
import pytest


async def test_discover_no_devices(tmp_workdir):
    from backend.services import discovery
    with patch("backend.services.discovery._ssdp_scan", return_value=[]):
        result = await discovery.discover_tvs(timeout=0.1)
    assert result == []


async def test_discover_probes_each_ip(tmp_workdir):
    from backend.services import discovery
    fake_info = {"ip": "10.0.0.1", "model": "QN65LS03BAFXZA", "name": "Frame", "frame": True}
    with patch("backend.services.discovery._ssdp_scan", return_value=["10.0.0.1"]), \
         patch("backend.services.discovery._probe", new=AsyncMock(return_value=fake_info)):
        out = await discovery.discover_tvs(timeout=0.1)
    assert out == [fake_info]


async def test_probe_ok(tmp_workdir):
    from backend.services import discovery

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"device": {"modelName": "QN65", "name": "Frame", "type": "Samsung",
                                "FrameTVSupport": "true", "wifiMac": "AA:BB"}}

    class FakeClient:
        async def get(self, url):
            return FakeResponse()

    info = await discovery._probe(FakeClient(), "10.0.0.5")
    assert info["ip"] == "10.0.0.5"
    assert info["model"] == "QN65"
    assert info["frame"] is True


async def test_probe_failure_returns_none(tmp_workdir):
    from backend.services import discovery

    class FakeClient:
        async def get(self, url):
            raise RuntimeError("net")

    info = await discovery._probe(FakeClient(), "10.0.0.5")
    assert info is None
