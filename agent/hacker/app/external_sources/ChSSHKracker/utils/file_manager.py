# -*- UTF-8 -*-
# utils/file_manager.py

import os
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class FileManager:
    @staticmethod
    def read_lines(path: str) -> List[str]:
        """Read non-empty, stripped lines from a file."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as file_read:
                return [line.strip() for line in file_read if line.strip()]
        except Exception as e:
            logger.error(f"Failed to read file: {path} - {e}")
            return []

    @staticmethod
    def file_append(path: str, data: str) -> None:
        """Append data to file, creating it if needed; swallow I/O errors to keep pipeline running."""
        try:
            path_dir = os.path.dirname(path)
            if path_dir and not os.path.exists(path_dir):
                os.makedirs(path_dir, exist_ok=True)
            with open(path, mode="a", encoding="utf-8", errors="ignore") as file_append:
                file_append.write(data)
        except Exception as e:
            logger.error(f"Failed writing to: {path} - {e}")

    @staticmethod
    def create_combo_file(user_file: str, pass_file: str, combo_path: str) -> None:
        """Generate username:password combinations and persist to combo file."""
        usernames = FileManager.read_lines(user_file)
        passwords = FileManager.read_lines(pass_file)
        try:
            combo_dir = os.path.dirname(combo_path)
            if combo_dir and not os.path.exists(combo_dir):
                os.makedirs(combo_dir, exist_ok=True)
            with open(combo_path, mode="w", encoding="utf-8", errors="ignore") as combo_file:
                for u in usernames:
                    for p in passwords:
                        combo_file.write(f"{u}:{p}\n")
        except Exception as e:
            logger.error(f"Failed to create combo file: {combo_path} - {e}")

    @staticmethod
    def parse_combo(path: str) -> List[Tuple[str, str]]:
        """Parse combo file of username:password into tuples."""
        lines = FileManager.read_lines(path)
        combos: List[Tuple[str, str]] = []
        for line in lines:
            if ":" in line:
                u, p = line.split(":", 1)
                combos.append((u, p))
        return combos

    @staticmethod
    def parse_targets(path: str) -> List[Tuple[str, str]]:
        """Parse targets file of ip:port into tuples. Missing port defaults to 22."""
        lines = FileManager.read_lines(path)
        targets: List[Tuple[str, str]] = []
        for line in lines:
            if ":" in line:
                ip, port = line.rsplit(":", 1)
                targets.append((ip.strip(), port.strip()))
            else:
                targets.append((line.strip(), "22"))
        return targets
