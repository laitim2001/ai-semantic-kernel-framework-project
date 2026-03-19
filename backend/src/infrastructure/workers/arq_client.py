"""ARQ Client — interface for submitting background jobs.

Provides a thin wrapper around the ARQ Redis pool for enqueuing
tasks from the main application. Falls back to direct execution
when ARQ is not available.

Sprint 136 — Phase 39 E2E Assembly D.
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_arq_client: Optional["ARQClient"] = None


class ARQClient:
    """Client for submitting jobs to the ARQ worker queue.

    Args:
        redis_url: Redis connection URL for ARQ.
        queue_name: Name of the task queue.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        queue_name: str = "ipa:arq:queue",
    ) -> None:
        self._redis_url = redis_url or os.getenv(
            "REDIS_URL",
            f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}",
        )
        self._queue_name = queue_name
        self._pool: Any = None
        self._available = False

    async def initialize(self) -> bool:
        """Initialize the ARQ Redis connection pool."""
        try:
            from arq import create_pool
            from arq.connections import RedisSettings

            redis_settings = RedisSettings.from_dsn(self._redis_url)
            self._pool = await create_pool(redis_settings)
            self._available = True
            logger.info("ARQClient: connected to Redis at %s", self._redis_url)
            return True
        except ImportError:
            logger.warning("ARQClient: arq package not installed, using direct execution fallback")
            self._available = False
            return False
        except Exception as e:
            logger.warning("ARQClient: Redis connection failed: %s", e)
            self._available = False
            return False

    @property
    def is_available(self) -> bool:
        """Whether ARQ is available for job submission."""
        return self._available

    async def enqueue(
        self,
        function_name: str,
        *args: Any,
        job_id: Optional[str] = None,
        timeout: int = 600,
        **kwargs: Any,
    ) -> Optional[str]:
        """Enqueue a job to the ARQ worker.

        Args:
            function_name: Name of the registered task function.
            job_id: Optional explicit job ID.
            timeout: Job timeout in seconds.

        Returns:
            Job ID if queued successfully, None if fallback.
        """
        if not self._available or self._pool is None:
            logger.info(
                "ARQClient: not available, job '%s' will use direct execution",
                function_name,
            )
            return None

        try:
            job = await self._pool.enqueue_job(
                function_name,
                *args,
                _job_id=job_id,
                _job_try=1,
                _timeout=timeout,
                **kwargs,
            )
            logger.info("ARQClient: enqueued job '%s' id=%s", function_name, job.job_id)
            return job.job_id
        except Exception as e:
            logger.error("ARQClient: enqueue failed: %s", e)
            return None

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Check the status of a queued job."""
        if not self._available or self._pool is None:
            return {"job_id": job_id, "status": "unknown", "arq_available": False}

        try:
            from arq.jobs import Job
            job = Job(job_id, self._pool)
            status = await job.status()
            result = await job.result_info()
            return {
                "job_id": job_id,
                "status": status.value if status else "unknown",
                "result": result,
            }
        except Exception as e:
            return {"job_id": job_id, "status": "error", "error": str(e)}

    async def close(self) -> None:
        """Close the Redis connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None


def get_arq_client() -> ARQClient:
    """Return the global ARQ client singleton."""
    global _arq_client
    if _arq_client is None:
        _arq_client = ARQClient()
    return _arq_client
