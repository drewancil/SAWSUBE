"""
SAWSUBE backend test suite — pytest + httpx ASGITransport.

Tests are grouped per module:
- test_image_processor.py
- test_scheduler.py
- test_watcher.py
- test_discovery.py
- test_ws_manager.py
- test_router_tv.py
- test_router_images.py
- test_router_schedules.py
- test_router_sources.py
- test_router_meta.py
- test_router_art.py
- test_tv_manager.py
- test_sources_*.py

All TV calls are mocked; no real network/TV access.
"""
