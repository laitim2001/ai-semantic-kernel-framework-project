# =============================================================================
# IPA Platform - Concurrent Optimizer
# =============================================================================
# Sprint 12: S12-3 Concurrent Execution Optimization
#
# Provides concurrent execution optimization utilities:
# - Batch processing with semaphore control
# - Worker pool management
# - Timeout and retry handling
# - Resource-aware execution
#
# Target: Achieve 3x throughput improvement through intelligent concurrency
# =============================================================================

from dataclasses import dataclass, field
from typing import (
    Dict, Any, List, Optional, Callable, TypeVar, Generic,
    Coroutine, Union, Tuple
)
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
import asyncio
import time
import logging
import functools

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class ConcurrencyConfig:
    """
    並發配置

    Attributes:
        max_workers: 最大工作者數量
        batch_size: 批次大小
        timeout_seconds: 操作超時時間（秒）
        semaphore_limit: 信號量限制
        use_thread_pool: 是否使用執行緒池（用於 CPU 密集型任務）
        retry_count: 重試次數
        retry_backoff: 重試退避因子
        preserve_order: 是否保持結果順序
    """
    max_workers: int = 10
    batch_size: int = 50
    timeout_seconds: float = 30.0
    semaphore_limit: int = 100
    use_thread_pool: bool = False
    retry_count: int = 3
    retry_backoff: float = 1.5
    preserve_order: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "max_workers": self.max_workers,
            "batch_size": self.batch_size,
            "timeout_seconds": self.timeout_seconds,
            "semaphore_limit": self.semaphore_limit,
            "use_thread_pool": self.use_thread_pool,
            "retry_count": self.retry_count,
            "retry_backoff": self.retry_backoff,
            "preserve_order": self.preserve_order,
        }


@dataclass
class ExecutionResult(Generic[T]):
    """
    執行結果

    Attributes:
        index: 原始索引（用於保持順序）
        result: 執行結果
        error: 錯誤信息（如有）
        duration_ms: 執行時間（毫秒）
        retries: 重試次數
    """
    index: int
    result: Optional[T] = None
    error: Optional[str] = None
    duration_ms: float = 0
    retries: int = 0

    @property
    def success(self) -> bool:
        """是否成功"""
        return self.error is None


@dataclass
class BatchExecutionStats:
    """
    批次執行統計

    Attributes:
        total_items: 總項目數
        successful: 成功數
        failed: 失敗數
        total_duration_ms: 總執行時間（毫秒）
        avg_duration_ms: 平均執行時間
        throughput_per_second: 吞吐量（項目/秒）
    """
    total_items: int
    successful: int
    failed: int
    total_duration_ms: float
    avg_duration_ms: float
    throughput_per_second: float

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "total_items": self.total_items,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": self.successful / self.total_items if self.total_items > 0 else 0,
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": self.avg_duration_ms,
            "throughput_per_second": self.throughput_per_second,
        }


class ConcurrentOptimizer:
    """
    並發優化器

    提供優化的並行執行功能：
    - 批次並行執行
    - 信號量控制
    - 超時處理
    - 自動重試
    - 工作池管理

    Example:
        >>> config = ConcurrencyConfig(max_workers=10, batch_size=50)
        >>> optimizer = ConcurrentOptimizer(config)
        >>>
        >>> async def process_item(item):
        ...     return await some_async_operation(item)
        >>>
        >>> results = await optimizer.execute_batch(items, process_item)
    """

    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        """
        初始化並發優化器

        Args:
            config: 並發配置
        """
        self.config = config or ConcurrencyConfig()
        self._semaphore = asyncio.Semaphore(self.config.semaphore_limit)
        self._thread_pool: Optional[ThreadPoolExecutor] = None

        if self.config.use_thread_pool:
            self._thread_pool = ThreadPoolExecutor(
                max_workers=self.config.max_workers
            )

        logger.info(f"ConcurrentOptimizer initialized with config: {self.config.to_dict()}")

    async def execute_batch(
        self,
        items: List[T],
        processor: Callable[[T], Coroutine[Any, Any, R]],
        preserve_order: Optional[bool] = None
    ) -> Tuple[List[ExecutionResult[R]], BatchExecutionStats]:
        """
        批次並行執行

        將項目分批並行處理，支援信號量控制和順序保持。

        Args:
            items: 待處理項目列表
            processor: 異步處理函數
            preserve_order: 是否保持結果順序（覆蓋配置）

        Returns:
            (執行結果列表, 執行統計)
        """
        preserve_order = preserve_order if preserve_order is not None else self.config.preserve_order
        all_results: List[ExecutionResult[R]] = []
        start_time = time.perf_counter()

        # 分批處理
        for batch_start in range(0, len(items), self.config.batch_size):
            batch_end = min(batch_start + self.config.batch_size, len(items))
            batch = items[batch_start:batch_end]

            batch_results = await self._process_batch(
                batch, processor, batch_start
            )
            all_results.extend(batch_results)

        # 計算統計
        total_duration = (time.perf_counter() - start_time) * 1000
        successful = sum(1 for r in all_results if r.success)

        stats = BatchExecutionStats(
            total_items=len(items),
            successful=successful,
            failed=len(items) - successful,
            total_duration_ms=total_duration,
            avg_duration_ms=total_duration / len(items) if items else 0,
            throughput_per_second=len(items) / (total_duration / 1000) if total_duration > 0 else 0,
        )

        # 按順序排序（如果需要）
        if preserve_order:
            all_results.sort(key=lambda r: r.index)

        logger.info(
            f"Batch execution completed: {stats.successful}/{stats.total_items} "
            f"successful, throughput: {stats.throughput_per_second:.1f}/s"
        )

        return all_results, stats

    async def _process_batch(
        self,
        batch: List[T],
        processor: Callable[[T], Coroutine[Any, Any, R]],
        start_index: int
    ) -> List[ExecutionResult[R]]:
        """
        處理單個批次

        Args:
            batch: 批次項目
            processor: 處理函數
            start_index: 起始索引

        Returns:
            執行結果列表
        """
        async def process_with_semaphore(item: T, index: int) -> ExecutionResult[R]:
            async with self._semaphore:
                return await self._execute_with_retry(item, processor, index)

        tasks = [
            process_with_semaphore(item, start_index + i)
            for i, item in enumerate(batch)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理異常結果
        processed_results: List[ExecutionResult[R]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ExecutionResult(
                    index=start_index + i,
                    error=str(result),
                ))
            else:
                processed_results.append(result)

        return processed_results

    async def _execute_with_retry(
        self,
        item: T,
        processor: Callable[[T], Coroutine[Any, Any, R]],
        index: int
    ) -> ExecutionResult[R]:
        """
        帶重試的執行

        Args:
            item: 待處理項目
            processor: 處理函數
            index: 項目索引

        Returns:
            執行結果
        """
        last_error: Optional[str] = None
        retries = 0

        for attempt in range(self.config.retry_count + 1):
            start_time = time.perf_counter()
            try:
                # 帶超時執行
                result = await asyncio.wait_for(
                    processor(item),
                    timeout=self.config.timeout_seconds
                )
                duration = (time.perf_counter() - start_time) * 1000

                return ExecutionResult(
                    index=index,
                    result=result,
                    duration_ms=duration,
                    retries=retries,
                )

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.config.timeout_seconds}s"
                retries = attempt

            except Exception as e:
                last_error = str(e)
                retries = attempt

            # 重試退避
            if attempt < self.config.retry_count:
                backoff = self.config.retry_backoff ** attempt
                await asyncio.sleep(backoff)
                logger.debug(
                    f"Retrying item {index} (attempt {attempt + 2}/"
                    f"{self.config.retry_count + 1})"
                )

        duration = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            index=index,
            error=last_error,
            duration_ms=duration,
            retries=retries,
        )

    async def execute_with_timeout(
        self,
        coros: List[Coroutine[Any, Any, T]],
        timeout: Optional[float] = None
    ) -> List[Union[T, Exception]]:
        """
        帶超時的並行執行

        Args:
            coros: 協程列表
            timeout: 超時時間（覆蓋配置）

        Returns:
            結果列表（包含成功結果和異常）
        """
        timeout = timeout or self.config.timeout_seconds

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*coros, return_exceptions=True),
                timeout=timeout
            )
            return list(results)
        except asyncio.TimeoutError:
            logger.warning(f"Batch execution timed out after {timeout}s")
            return [TimeoutError(f"Execution timed out after {timeout}s")]

    def execute_sync_in_thread(
        self,
        func: Callable[[T], R],
        items: List[T]
    ) -> List[ExecutionResult[R]]:
        """
        在執行緒池中執行同步函數

        適用於 CPU 密集型或阻塞型操作。

        Args:
            func: 同步處理函數
            items: 待處理項目

        Returns:
            執行結果列表
        """
        if not self._thread_pool:
            self._thread_pool = ThreadPoolExecutor(
                max_workers=self.config.max_workers
            )

        results: List[ExecutionResult[R]] = []
        futures: List[Tuple[int, Future]] = []

        for i, item in enumerate(items):
            future = self._thread_pool.submit(self._execute_sync, func, item, i)
            futures.append((i, future))

        for index, future in futures:
            try:
                result = future.result(timeout=self.config.timeout_seconds)
                results.append(result)
            except Exception as e:
                results.append(ExecutionResult(
                    index=index,
                    error=str(e),
                ))

        return results

    def _execute_sync(
        self,
        func: Callable[[T], R],
        item: T,
        index: int
    ) -> ExecutionResult[R]:
        """同步執行包裝器"""
        start_time = time.perf_counter()
        try:
            result = func(item)
            duration = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(
                index=index,
                result=result,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(
                index=index,
                error=str(e),
                duration_ms=duration,
            )

    def create_worker_pool(
        self,
        num_workers: Optional[int] = None
    ) -> "WorkerPool":
        """
        建立工作池

        Args:
            num_workers: 工作者數量（覆蓋配置）

        Returns:
            WorkerPool 實例
        """
        return WorkerPool(
            num_workers=num_workers or self.config.max_workers,
            semaphore=self._semaphore,
            timeout=self.config.timeout_seconds,
        )

    def get_optimal_workers(
        self,
        task_type: str = "io_bound",
        available_cpus: Optional[int] = None
    ) -> int:
        """
        獲取最佳工作者數量

        根據任務類型和可用資源計算最佳並發數。

        Args:
            task_type: 任務類型 ("io_bound" 或 "cpu_bound")
            available_cpus: 可用 CPU 數量

        Returns:
            建議的工作者數量
        """
        import os
        cpus = available_cpus or os.cpu_count() or 4

        if task_type == "cpu_bound":
            # CPU 密集型：使用 CPU 數量
            return cpus
        else:
            # I/O 密集型：可以使用更多工作者
            return min(cpus * 4, self.config.semaphore_limit)

    async def shutdown(self) -> None:
        """關閉並發優化器"""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)
            self._thread_pool = None
        logger.info("ConcurrentOptimizer shutdown complete")


class WorkerPool:
    """
    工作池

    管理一組工作者協程，用於持續處理任務隊列。

    Example:
        >>> pool = optimizer.create_worker_pool(num_workers=5)
        >>> await pool.start()
        >>>
        >>> await pool.submit(async_task_1)
        >>> await pool.submit(async_task_2)
        >>>
        >>> results = await pool.shutdown()
    """

    def __init__(
        self,
        num_workers: int,
        semaphore: asyncio.Semaphore,
        timeout: float = 30.0
    ):
        """
        初始化工作池

        Args:
            num_workers: 工作者數量
            semaphore: 共享信號量
            timeout: 任務超時時間
        """
        self.num_workers = num_workers
        self.semaphore = semaphore
        self.timeout = timeout
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._results: List[Any] = []
        self._running = False
        self._completed_count = 0
        self._error_count = 0

    async def start(self) -> None:
        """啟動工作池"""
        if self._running:
            return

        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.num_workers)
        ]
        logger.info(f"WorkerPool started with {self.num_workers} workers")

    async def _worker(self, worker_id: int) -> None:
        """
        工作者協程

        持續從隊列中獲取任務並執行。
        """
        logger.debug(f"Worker {worker_id} started")

        while self._running:
            try:
                # 嘗試獲取任務（帶超時以便檢查運行狀態）
                task = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )

                if task is None:  # 終止信號
                    break

                async with self.semaphore:
                    try:
                        result = await asyncio.wait_for(
                            task(),
                            timeout=self.timeout
                        )
                        self._results.append(result)
                        self._completed_count += 1
                    except Exception as e:
                        logger.error(f"Worker {worker_id} task error: {e}")
                        self._error_count += 1
                        self._results.append(e)

                self._queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

        logger.debug(f"Worker {worker_id} stopped")

    async def submit(self, task: Callable[[], Coroutine[Any, Any, T]]) -> None:
        """
        提交任務

        Args:
            task: 異步任務函數（無參數）
        """
        if not self._running:
            raise RuntimeError("WorkerPool is not running")
        await self._queue.put(task)

    async def submit_many(
        self,
        tasks: List[Callable[[], Coroutine[Any, Any, T]]]
    ) -> None:
        """
        批量提交任務

        Args:
            tasks: 任務列表
        """
        for task in tasks:
            await self.submit(task)

    async def wait_until_done(self) -> None:
        """等待所有已提交的任務完成"""
        await self._queue.join()

    async def shutdown(self, wait: bool = True) -> List[Any]:
        """
        關閉工作池

        Args:
            wait: 是否等待所有任務完成

        Returns:
            所有執行結果列表
        """
        if wait:
            await self._queue.join()

        self._running = False

        # 發送終止信號
        for _ in range(self.num_workers):
            await self._queue.put(None)

        # 等待所有工作者完成
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        logger.info(
            f"WorkerPool shutdown: {self._completed_count} completed, "
            f"{self._error_count} errors"
        )

        return self._results

    @property
    def pending_count(self) -> int:
        """待處理任務數"""
        return self._queue.qsize()

    @property
    def completed_count(self) -> int:
        """已完成任務數"""
        return self._completed_count

    @property
    def error_count(self) -> int:
        """錯誤數"""
        return self._error_count

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        return {
            "num_workers": self.num_workers,
            "pending": self.pending_count,
            "completed": self.completed_count,
            "errors": self.error_count,
            "running": self._running,
        }
