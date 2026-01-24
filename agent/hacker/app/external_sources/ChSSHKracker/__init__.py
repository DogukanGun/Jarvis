# -*- coding: utf-8 -*-
"""
ChSSHKracker - Advanced SSH Brute Force Tool

Programmatic interface for SSH credential testing.
"""

from .ChSshKracker import (
    ChSSHKracker,
    AttackConfig,
    AttackResult
)
from .core.models import ServerInfo
from .core.config import Config, Globals
from .core.stats import Stats

__version__ = '1.0.0'

__all__ = [
    'ChSSHKracker',
    'AttackConfig',
    'AttackResult',
    'ServerInfo',
    'Config',
    'Globals',
    'Stats',
]
