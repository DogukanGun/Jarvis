# -*- coding: utf-8 -*-
# core/honeypot.py

import time

from core.ssh_client import SSH
from core.models import ServerInfo, HoneypotDetector

class HoneypotEngine:
    def detect(self, ssh: SSH, server: ServerInfo, detector: HoneypotDetector) -> bool:
        score = 0
        score += self.analyze_command_output(server, detector)
        if detector.time_analysis:
            score += self.analyze_response_time(server)
        score += self.analyze_file_system(server)
        score += self.analyze_processes(server)
        if detector.network_analysis:
            score += self.analyze_network(ssh)
        score += self.behavioral_tests(ssh, server)
        score += self.detect_anomalies(server)
        score += self.advanced_honeypot_tests(ssh)
        score += self.performance_tests(ssh)
        server.honeypot_score = score
        return score >= 6

    def analyze_command_output(self, server: ServerInfo, detector: HoneypotDetector) -> int:
        score = 0
        for output in server.commands.values():
            lower_output = output.lower()
            for indicator in detector.suspicious_patterns:
                if indicator in lower_output:
                    score += 3
        return score

    def analyze_response_time(self, server: ServerInfo) -> int:
        # Very fast response < 10ms is suspicious
        return 2 if server.response_time_ms < 10 else 0

    def analyze_file_system(self, server: ServerInfo) -> int:
        score = 0
        ls_output = server.commands.get("ls_root", "")
        lower = ls_output.lower()
        for pattern in ["total 0", "total 4", "honeypot", "fake", "simulation"]:
            if pattern in lower:
                score += 1
        lines = [ln for ln in ls_output.strip().splitlines() if ln.strip()]
        if len(lines) < 5:
            score += 1
        return score

    def analyze_processes(self, server: ServerInfo) -> int:
        score = 0
        ps_output = server.commands.get("ps", "").lower()
        for proc in ["cowrie", "kippo", "honeypot", "honeyd", "artillery", "honeytrap", "glastopf", "python honeypot", "perl honeypot"]:
            if proc in ps_output:
                score += 2
        lines = [ln for ln in ps_output.strip().splitlines() if ln.strip()]
        if len(lines) < 5:
            score += 1
        return score

    def analyze_network(self, ssh: SSH) -> int:
        score = 0
        network_cfg = ssh.run(
            "ls -la /etc/network/interfaces /etc/sysconfig/network-scripts/ /etc/netplan/ 2>/dev/null | head -5").lower()
        if "total 0" in network_cfg or "no such file" in network_cfg or len(network_cfg.strip()) < 10:
            score += 1
        iface = ssh.run(
            "ip addr show 2>/dev/null | grep -E '^[0-9]+:' | head -5").lower()
        if any(x in iface for x in ("fake", "honeypot", "trap")) or len(iface.strip()) < 10:
            score += 1
        route = ssh.run("ip route show 2>/dev/null | head -3")
        if len(route.strip()) < 20:
            score += 1
        return score

    def behavioral_tests(self, ssh: SSH, server: ServerInfo) -> int:
        score = 0
        tmp_name = f"/tmp/test_{int(time.time())}"
        create_out = ssh.run(f"echo 'test' > {tmp_name}")
        if "error" in create_out.lower() or "permission denied" in create_out.lower():
            score += 1
        else:
            ssh.run(f"rm -f {tmp_name}")

        sensitive = ["/etc/passwd", "/etc/shadow", "/proc/version"]
        accessible = 0
        for f in sensitive:
            out = ssh.run(f"cat {f} 2>/dev/null | head -1")
            if "error" not in out.lower() and out.strip():
                accessible += 1
        if accessible == len(sensitive):
            score += 1

        system_cmds = ["id", "whoami", "pwd"]
        working = 0
        for cmd in system_cmds:
            out = ssh.run(cmd)
            if "error" not in out.lower() and out.strip():
                working += 1
        if working == 0:
            score += 2
        return score


    def advanced_honeypot_tests(self, ssh: SSH) -> int:
        score = 0
        cpu = ssh.run("cat /proc/cpuinfo | grep 'model name' | head -1").lower()
        if "qemu" in cpu or "virtual" in cpu:
            score += 1
        kernel = ssh.run("uname -r")
        if "generic" in kernel and len(kernel.strip()) < 20:
            score += 1
        pm_working = 0
        for pm in ("which apt", "which yum", "which pacman", "which zypper"):
            out = ssh.run(pm)
            if "not found" not in out and out.strip():
                pm_working += 1
        if pm_working == 0:
            score += 1
        services = ssh.run(
            "systemctl list-units --type=service --state=running 2>/dev/null | head -10")
        if "0 loaded units" in services or len(services.strip()) < 50:
            score += 1
        internet = ssh.run(
            "ping -c 1 8.8.8.8 2>/dev/null | grep '1 packets transmitted'")
        if not internet.strip():
            score += 1
        return score


    def performance_tests(self, ssh: SSH) -> int:
        score = 0
        io_test = ssh.run("time dd if=/dev/zero of=/tmp/test bs=1M count=10 2>&1")
        if "command not found" in io_test:
            score += 1
        ssh.run("rm -f /tmp/test")
        network_test = ssh.run("ss -tuln 2>/dev/null | wc -l").strip()
        if network_test.isdigit() and int(network_test) < 5:
            score += 1
        return score


    def detect_anomalies(self, server: ServerInfo) -> int:
        score = 0
        if server.hostname:
            suspicious = [
                "honeypot",
                "fake",
                "trap",
                "monitor",
                "sandbox",
                "test",
                "simulation",
                "gnu/linux",
                "preempt_dynamic",
            ]
            lower = server.hostname.lower()
            if any(x in lower for x in suspicious):
                score += 1
        uptime = server.commands.get("uptime", "")
        if any(x in uptime for x in ("0:", "min", "command not found")):
            score += 1
        history = server.commands.get("history", "")
        if len([ln for ln in history.strip().splitlines() if ln.strip()]) < 3:
            score += 1
        return score