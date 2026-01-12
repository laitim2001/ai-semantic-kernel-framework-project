"""
Patrol Scheduler - 巡檢調度器

Sprint 82 - S82-1: 主動巡檢模式
負責定時巡檢任務的調度管理
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

# APScheduler 是可選依賴
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    HAS_APSCHEDULER = True
except ImportError:
    AsyncIOScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore
    HAS_APSCHEDULER = False

from .types import (
    PatrolConfig,
    PatrolPriority,
    PatrolStatus,
    ScheduledPatrol,
)

logger = logging.getLogger(__name__)


class PatrolScheduler:
    """
    巡檢調度器

    功能:
    - 管理定時巡檢任務
    - 支援 Cron 表達式調度
    - 支援手動觸發巡檢
    - 追蹤巡檢執行歷史
    """

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._patrols: Dict[str, ScheduledPatrol] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._is_running: bool = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """啟動調度器"""
        async with self._lock:
            if self._is_running:
                logger.warning("Scheduler is already running")
                return

            if not HAS_APSCHEDULER:
                logger.warning(
                    "APScheduler not installed. Scheduler will work in manual-only mode. "
                    "Install with: pip install apscheduler"
                )
                self._is_running = True
                return

            self._scheduler = AsyncIOScheduler(
                timezone="UTC",
                job_defaults={
                    "coalesce": True,
                    "max_instances": 1,
                    "misfire_grace_time": 60,
                },
            )
            self._scheduler.start()
            self._is_running = True
            logger.info("PatrolScheduler started successfully")

    async def stop(self) -> None:
        """停止調度器"""
        async with self._lock:
            if not self._is_running:
                logger.warning("Scheduler is not running")
                return

            if self._scheduler:
                self._scheduler.shutdown(wait=True)
                self._scheduler = None

            self._is_running = False
            logger.info("PatrolScheduler stopped successfully")

    async def schedule_patrol(
        self,
        patrol_config: PatrolConfig,
        callback: Callable,
    ) -> str:
        """
        配置定時巡檢

        Args:
            patrol_config: 巡檢配置
            callback: 巡檢執行回調函數

        Returns:
            job_id: 任務 ID
        """
        if not self._is_running:
            raise RuntimeError("Scheduler is not running. Call start() first.")

        async with self._lock:
            job_id = f"patrol_{patrol_config.patrol_id}_{uuid4().hex[:8]}"

            # 如果沒有 APScheduler，只存儲配置以供手動觸發
            if not HAS_APSCHEDULER or not self._scheduler:
                scheduled_patrol = ScheduledPatrol(
                    job_id=job_id,
                    patrol_config=patrol_config,
                    next_run=None,
                    last_run=None,
                    last_status=None,
                )
                self._patrols[patrol_config.patrol_id] = scheduled_patrol
                self._callbacks[patrol_config.patrol_id] = callback
                logger.info(
                    f"Registered patrol (manual-only mode): {patrol_config.name} "
                    f"(ID: {job_id})"
                )
                return job_id

            # 創建 Cron 觸發器
            trigger = CronTrigger.from_crontab(patrol_config.cron_expression)

            # 添加任務
            job = self._scheduler.add_job(
                self._execute_patrol_wrapper,
                trigger=trigger,
                args=[patrol_config, callback],
                id=job_id,
                name=patrol_config.name,
                replace_existing=True,
            )

            # 記錄已排程的巡檢
            scheduled_patrol = ScheduledPatrol(
                job_id=job_id,
                patrol_config=patrol_config,
                next_run=job.next_run_time,
                last_run=None,
                last_status=None,
            )
            self._patrols[patrol_config.patrol_id] = scheduled_patrol
            self._callbacks[patrol_config.patrol_id] = callback

            logger.info(
                f"Scheduled patrol: {patrol_config.name} "
                f"(ID: {job_id}, Cron: {patrol_config.cron_expression})"
            )

            return job_id

    async def cancel_patrol(self, patrol_id: str) -> bool:
        """
        取消巡檢任務

        Args:
            patrol_id: 巡檢 ID

        Returns:
            是否成功取消
        """
        async with self._lock:
            if patrol_id not in self._patrols:
                logger.warning(f"Patrol not found: {patrol_id}")
                return False

            scheduled = self._patrols[patrol_id]

            if self._scheduler:
                try:
                    self._scheduler.remove_job(scheduled.job_id)
                except Exception as e:
                    logger.error(f"Failed to remove job: {e}")

            del self._patrols[patrol_id]
            if patrol_id in self._callbacks:
                del self._callbacks[patrol_id]

            logger.info(f"Cancelled patrol: {patrol_id}")
            return True

    async def trigger_patrol(
        self,
        patrol_id: str,
        priority: PatrolPriority = PatrolPriority.HIGH,
    ) -> Optional[str]:
        """
        手動觸發巡檢

        Args:
            patrol_id: 巡檢 ID
            priority: 執行優先級

        Returns:
            execution_id: 執行 ID
        """
        if patrol_id not in self._patrols:
            logger.warning(f"Patrol not found: {patrol_id}")
            return None

        scheduled = self._patrols[patrol_id]
        callback = self._callbacks.get(patrol_id)

        if not callback:
            logger.error(f"Callback not found for patrol: {patrol_id}")
            return None

        execution_id = f"exec_{uuid4().hex[:12]}"

        # 異步執行巡檢
        asyncio.create_task(
            self._execute_patrol_wrapper(
                scheduled.patrol_config,
                callback,
                execution_id=execution_id,
                is_manual=True,
            )
        )

        logger.info(f"Triggered manual patrol: {patrol_id} (Execution: {execution_id})")
        return execution_id

    async def list_schedules(self) -> List[ScheduledPatrol]:
        """列出所有已排程的巡檢"""
        async with self._lock:
            result = []
            for patrol in self._patrols.values():
                # 更新下次執行時間
                if self._scheduler:
                    job = self._scheduler.get_job(patrol.job_id)
                    if job:
                        patrol.next_run = job.next_run_time
                result.append(patrol)
            return result

    async def get_schedule(self, patrol_id: str) -> Optional[ScheduledPatrol]:
        """獲取指定巡檢的排程信息"""
        async with self._lock:
            if patrol_id not in self._patrols:
                return None

            patrol = self._patrols[patrol_id]

            # 更新下次執行時間
            if self._scheduler:
                job = self._scheduler.get_job(patrol.job_id)
                if job:
                    patrol.next_run = job.next_run_time

            return patrol

    async def update_schedule(
        self,
        patrol_id: str,
        cron_expression: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """
        更新巡檢排程

        Args:
            patrol_id: 巡檢 ID
            cron_expression: 新的 Cron 表達式
            enabled: 是否啟用

        Returns:
            是否成功更新
        """
        async with self._lock:
            if patrol_id not in self._patrols:
                logger.warning(f"Patrol not found: {patrol_id}")
                return False

            scheduled = self._patrols[patrol_id]

            if cron_expression:
                scheduled.patrol_config.cron_expression = cron_expression

                if self._scheduler:
                    trigger = CronTrigger.from_crontab(cron_expression)
                    self._scheduler.reschedule_job(
                        scheduled.job_id,
                        trigger=trigger,
                    )

            if enabled is not None:
                scheduled.patrol_config.enabled = enabled

                if self._scheduler:
                    if enabled:
                        self._scheduler.resume_job(scheduled.job_id)
                    else:
                        self._scheduler.pause_job(scheduled.job_id)

            logger.info(f"Updated patrol schedule: {patrol_id}")
            return True

    async def _execute_patrol_wrapper(
        self,
        config: PatrolConfig,
        callback: Callable,
        execution_id: Optional[str] = None,
        is_manual: bool = False,
    ) -> None:
        """
        巡檢執行包裝器

        Args:
            config: 巡檢配置
            callback: 執行回調
            execution_id: 執行 ID
            is_manual: 是否手動觸發
        """
        patrol_id = config.patrol_id
        exec_id = execution_id or f"exec_{uuid4().hex[:12]}"
        start_time = datetime.utcnow()

        logger.info(
            f"Starting patrol: {config.name} "
            f"(ID: {patrol_id}, Execution: {exec_id}, Manual: {is_manual})"
        )

        try:
            # 執行回調
            await callback(config, exec_id)

            # 更新統計
            if patrol_id in self._patrols:
                self._patrols[patrol_id].last_run = start_time
                self._patrols[patrol_id].run_count += 1
                self._patrols[patrol_id].last_status = PatrolStatus.HEALTHY

            logger.info(f"Patrol completed successfully: {patrol_id} (Execution: {exec_id})")

        except Exception as e:
            logger.error(f"Patrol failed: {patrol_id} (Execution: {exec_id}) - {e}")

            if patrol_id in self._patrols:
                self._patrols[patrol_id].last_run = start_time
                self._patrols[patrol_id].run_count += 1
                self._patrols[patrol_id].failure_count += 1
                self._patrols[patrol_id].last_status = PatrolStatus.CRITICAL

    @property
    def is_running(self) -> bool:
        """調度器是否運行中"""
        return self._is_running

    @property
    def patrol_count(self) -> int:
        """已排程巡檢數量"""
        return len(self._patrols)
