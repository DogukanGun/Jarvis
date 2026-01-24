# -*- coding: utf-8 -*-
# core/recon.py

import re
from typing import Dict, Iterable, List, Optional, Tuple

from core.models import ServerInfo
from core.ssh_client import SSH


class ReconSystem:
    def gather_system_info(self, ssh: SSH, server: ServerInfo) -> None:
        """Execute a suite of commands and populate ServerInfo."""
        commands = {
            "hostname": "hostname",
            "uname": "uname -a",
            "whoami": "whoami",
            "pwd": "pwd",
            "ls_root": "ls -la /",
            "ps": "ps aux | head -10",
            "netstat": "netstat -tulpn | head -10",
            "history": "history | tail -5",
            "ssh_version": "ssh -V",
            "uptime": "uptime",
            "mount": "mount | head -5",
            "env": "env | head -10",
        }
        for name, cmd in commands.items():
            out = ssh.run(cmd)
            server.commands[name] = out
            if name == "hostname":
                server.hostname = out.strip()
            elif name == "uname":
                server.os_info = out.strip()
            elif name == "ssh_version":
                server.ssh_version = out.strip()

        server.open_ports = self.scan_local_ports(server.commands.get("netstat", ""))


    def scan_local_ports(self, netstat_output: str) -> List[str]:
        ports: List[str] = []
        port_regex = re.compile(r":(\d+)\s")
        for line in netstat_output.splitlines():
            for match in port_regex.findall(line):
                if match not in ports:
                    ports.append(match)
        return ports