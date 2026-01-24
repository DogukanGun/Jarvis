# -*- coding: utf-8 -*-
# core/stats.py

import threading

from core.counter import Counter

_stats_lock = threading.Lock()

class Stats:
    Goods = Counter()
    Errors = Counter()
    Honeypots = Counter()
