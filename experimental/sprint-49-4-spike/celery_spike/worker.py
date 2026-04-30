"""Spike: Celery worker startup. Run via:

    celery -A tasks worker --loglevel=info --concurrency=4

NOT production code.
"""

from __future__ import annotations

from tasks import app  # noqa: F401

# Worker is started via `celery -A tasks worker` CLI, not by running this file directly.
# This file exists only to make the package importable.

if __name__ == "__main__":
    print("Use: celery -A tasks worker --loglevel=info --concurrency=4")
