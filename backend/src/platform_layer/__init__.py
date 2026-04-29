"""
platform_layer — V2 platform layer (governance / identity / observability impl / workers).

Distinct from `agent_harness/` (which owns ABC contracts) — this layer
implements platform-wide infrastructure that crosses category lines.

Why named `platform_layer` instead of `platform`:
    Sprint 49.1 Day 5 discovered that naming this package `platform`
    shadows Python's stdlib `platform` module when the package is on
    sys.path (which `PYTHONPATH=src` does). This broke any test
    framework that imported a transitive dep using
    `platform.python_implementation()` / `platform.system()` (e.g.
    pytest+faker, httpx via FastAPI TestClient, rich via httpx).
    Renamed to `platform_layer` to avoid the conflict. The 17.md
    interface single-source registry is unaffected (no contract type
    is owned here).
"""
