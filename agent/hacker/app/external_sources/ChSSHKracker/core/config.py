# -*- coding: utf-8 -*-
# core/config.py

import re
import threading

__version__ = '1.0.0'
SCRIPT_NAME = 'ChSSHKracker'  # Script name
SCRIPT_DESCRIPTION = (
    'A powerful, high-performance SSH brute force tool written in Python 3.9 with enhanced multi-layer worker architecture'
    ', advanced honeypot detection, real-time statistics, and comprehensive system reconnaissance capabilities'
)  # Script description

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')



class Globals:
    _total_tasks: int = 0
    _stop_event = threading.Event()
    _success_map_lock = threading.Lock()
    _success_ip_port: set[str] = set()
    _start_time_monotonic: float = 0.0

class Config:
    IP_FILE: str = ''
    USERNAME_FILE: str = ''
    PASSWORD_FILE: str = ''
    COMBO_FILE: str = ''
    USE_COMBO: bool = False
    TIMEOUT: int = 5
    MAX_WORKERS: int = 25
    CONCURRENT_PER_WORKER: int = 25


class FILE_PATH:
    DEBUG_FILE: str = 'data/debug.log'
    COMBO_FILE: str = 'data/COMBO.TXT'
    GOODS_FILE: str = 'data/SSH-GOODS.TXT'
    DETAILED_FILE: str = 'data/SSH-DETAILES.TXT'
    HONEYPOT_FILE: str = 'data/HONEYPOTS.TXT'
