# -*- coding: utf-8 -*-
# core/counter.py

import threading


class Counter:
    def __init__(self, value: int = 0):
        self.value: int = value
        self.lock = threading.Lock()

    def increment(self):
        with self.lock:
            self.value += 1

    def get(self):
        with self.lock:
            return self.value