# -*- coding: utf-8 -*-
# core/models.py

from typing import Dict, List
from dataclasses import dataclass, field

@dataclass
class SSHTask:
    ip: str
    port: str
    username: str
    password: str


@dataclass
class ServerInfo:
    ip: str = ''
    port: str = ''
    username: str = ''
    password: str = ''
    is_honeypot: bool = False
    honeypot_score: int = 0
    ssh_version: str = ""
    os_info: str = ""
    hostname: str = ""
    response_time_ms: float = 0.0
    commands: Dict[str, str] = field(default_factory=dict)
    open_ports: List[str] = field(default_factory=list)


@dataclass
class HoneypotDetector:
    suspicious_patterns: List[str] = field(
        default_factory=lambda: [
            "fake",
            "simulation",
            "honeypot",
            "trap",
            "monitor",
            "cowrie",
            "kippo",
            "artillery",
            "honeyd",
            "ssh-honeypot",
            "honeytrap",
            "/opt/honeypot",
            "/var/log/honeypot",
        ]
    )
    time_analysis: bool = True
    command_analysis: bool = True
    network_analysis: bool = True
