# -*- coding: utf-8 -*-
# core/result_logger.py

import time
import logging
from typing import Optional, Callable

from core.config import FILE_PATH
from core.models import ServerInfo
from utils.file_manager import FileManager

logger = logging.getLogger(__name__)


class ResultLogger:
    def __init__(
        self,
        on_success: Optional[Callable[[ServerInfo], None]] = None,
        on_honeypot: Optional[Callable[[ServerInfo], None]] = None
    ):
        self.file_manager = FileManager()
        self.goods_file = FILE_PATH.GOODS_FILE
        self.goods_detailed_file = FILE_PATH.DETAILED_FILE
        self.honeypot_file = FILE_PATH.HONEYPOT_FILE
        self.debug_file = FILE_PATH.DEBUG_FILE
        self.on_success = on_success
        self.on_honeypot = on_honeypot

    def log_success(self, server: ServerInfo) -> None:
        simple = f"{server.ip}:{server.port}@{server.username}:{server.password}"
        self.file_manager.file_append(self.goods_file, simple + "\n")

        detailed = self._format_detailed_log(server)
        self.file_manager.file_append(self.goods_detailed_file, detailed + '\n')

        if self.on_success:
            self.on_success(server)

    def _format_detailed_log(self, server: ServerInfo) -> str:
        """Format server info as plain text log entry."""
        lines = [
            "=" * 60,
            "SSH SUCCESS",
            "=" * 60,
            f"Target: {server.ip}:{server.port}",
            f"Credentials: {server.username}:{server.password}",
            f"Hostname: {server.hostname}",
            f"OS: {server.os_info}",
            f"SSH Version: {server.ssh_version}",
            f"Response Time: {server.response_time_ms:.2f} ms",
            f"Open Ports: {server.open_ports}",
            f"Honeypot Score: {server.honeypot_score}",
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60
        ]
        return "\n".join(lines)
    
    def log_honeypot(self, server: ServerInfo) -> None:
        simple = f"{server.ip}:{server.port}@{server.username}:{server.password}"
        honeypot_info = (
            f'HONEYPOT: {simple} '
            f'(Score: {server.honeypot_score})\n'
        )
        self.file_manager.file_append(self.honeypot_file, honeypot_info)

        if self.on_honeypot:
            self.on_honeypot(server)
    
    def log_debug_file(self, RequestsMessage: str):
        self.file_manager.file_append(self.debug_file, RequestsMessage)