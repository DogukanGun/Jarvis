"""Scapy interactive packet manipulation tool wrapper."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.tools.base import (
    AuthLevel,
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)
from app.tools.executor import PythonExecutor
from app.tools.registry import ToolRegistry


class ScapyTool(BaseTool):
    """Interactive packet manipulation library. Craft, send, sniff, and analyse
    network packets using Scapy's Python API."""

    def __init__(self) -> None:
        self._executor = PythonExecutor()

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="scapy",
            display_name="Scapy",
            category=ToolCategory.network,
            description=(
                "Interactive packet manipulation library. Craft, send, sniff, "
                "and analyze network packets."
            ),
            capabilities=[
                "packet_craft",
                "packet_send",
                "packet_sniff",
                "port_scan",
                "traceroute",
                "arp_scan",
            ],
            auth_level=AuthLevel.medium,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    required=True,
                    choices=[
                        "arp_scan",
                        "port_scan",
                        "ping",
                        "traceroute",
                        "sniff",
                        "custom",
                    ],
                    description="Action to perform.",
                ),
                ToolParameter(
                    name="target",
                    type="string",
                    required=False,
                    description="Target IP or CIDR (e.g. 192.168.1.0/24).",
                ),
                ToolParameter(
                    name="ports",
                    type="string",
                    required=False,
                    default="1-1024",
                    description="Port range for scanning (e.g. '1-1024' or '22,80,443').",
                ),
                ToolParameter(
                    name="interface",
                    type="string",
                    required=False,
                    description="Network interface to use.",
                ),
                ToolParameter(
                    name="count",
                    type="integer",
                    required=False,
                    default=10,
                    description="Number of packets to capture (sniff action).",
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    required=False,
                    default=30,
                    description="Timeout in seconds for operations.",
                ),
                ToolParameter(
                    name="custom_code",
                    type="string",
                    required=False,
                    description="Custom Scapy code (DISABLED for security).",
                ),
            ],
            output_format="json",
        )

    # ------------------------------------------------------------------ #
    # Execute
    # ------------------------------------------------------------------ #

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action: str = params["action"]
        target: str | None = params.get("target")
        ports: str = params.get("ports", "1-1024")
        interface: str | None = params.get("interface")
        count: int = params.get("count", 10)
        timeout: int = params.get("timeout", 30)

        if action == "custom":
            return ToolResult(
                tool_name="scapy",
                success=False,
                error=(
                    "Custom code execution is disabled for security reasons. "
                    "Use one of the predefined actions instead: "
                    "arp_scan, port_scan, ping, traceroute, sniff."
                ),
            )

        if action in ("arp_scan", "port_scan", "ping", "traceroute") and not target:
            return ToolResult(
                tool_name="scapy",
                success=False,
                error=f"Parameter 'target' is required for action '{action}'.",
            )

        dispatch = {
            "arp_scan": lambda: self._arp_scan(target, interface, timeout),
            "port_scan": lambda: self._port_scan(target, ports, timeout),
            "ping": lambda: self._ping(target, timeout),
            "traceroute": lambda: self._traceroute(target, timeout),
            "sniff": lambda: self._sniff(interface, count, timeout),
        }

        func = dispatch.get(action)
        if func is None:
            return ToolResult(
                tool_name="scapy",
                success=False,
                error=f"Unsupported action '{action}'.",
            )

        result = await self._executor.execute(func)
        result.tool_name = "scapy"

        if result.success:
            result.structured_output = self.parse_output(result.raw_output)

        return result

    # ------------------------------------------------------------------ #
    # Scapy action callables (run in thread pool via PythonExecutor)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _arp_scan(target: str, interface: str | None, timeout: int) -> str:
        from scapy.all import ARP, Ether, conf, srp

        if interface:
            conf.iface = interface

        pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=target)
        ans, _ = srp(pkt, timeout=timeout, verbose=False)

        hosts: List[Dict[str, str]] = []
        for _, rcv in ans:
            hosts.append({"ip": rcv.psrc, "mac": rcv.hwsrc})

        return json.dumps({"hosts": hosts, "host_count": len(hosts)})

    @staticmethod
    def _port_scan(target: str, ports: str, timeout: int) -> str:
        from scapy.all import IP, TCP, sr1

        port_list = _parse_ports(ports)
        results: List[Dict[str, Any]] = []

        for port in port_list:
            pkt = IP(dst=target) / TCP(dport=port, flags="S")
            resp = sr1(pkt, timeout=min(timeout, 3), verbose=False)

            if resp is None:
                status = "filtered"
            elif resp.haslayer(TCP):
                tcp_flags = resp[TCP].flags
                if tcp_flags == 0x12:  # SYN-ACK
                    status = "open"
                elif tcp_flags == 0x14:  # RST-ACK
                    status = "closed"
                else:
                    status = "unknown"
            else:
                status = "unknown"

            results.append({
                "port": port,
                "status": status,
                "protocol": "tcp",
            })

        open_ports = [r for r in results if r["status"] == "open"]
        return json.dumps({
            "target": target,
            "ports_scanned": len(port_list),
            "open_count": len(open_ports),
            "results": results,
        })

    @staticmethod
    def _ping(target: str, timeout: int) -> str:
        from scapy.all import ICMP, IP, sr1

        pkt = IP(dst=target) / ICMP()
        resp = sr1(pkt, timeout=timeout, verbose=False)

        if resp is None:
            return json.dumps({
                "target": target,
                "alive": False,
                "rtt_ms": None,
            })

        rtt_ms = round((resp.time - pkt.sent_time) * 1000, 2)
        return json.dumps({
            "target": target,
            "alive": True,
            "ttl": resp.ttl,
            "rtt_ms": rtt_ms,
        })

    @staticmethod
    def _traceroute(target: str, timeout: int) -> str:
        from scapy.all import traceroute as scapy_traceroute

        result, _ = scapy_traceroute(target, maxttl=30, timeout=timeout, verbose=False)

        hops: List[Dict[str, Any]] = []
        for snd, rcv in result:
            hops.append({
                "ttl": snd.ttl,
                "ip": rcv.src,
                "rtt_ms": round((rcv.time - snd.sent_time) * 1000, 2),
            })

        # Sort by TTL for ordered output
        hops.sort(key=lambda h: h["ttl"])

        return json.dumps({
            "target": target,
            "hop_count": len(hops),
            "hops": hops,
        })

    @staticmethod
    def _sniff(interface: str | None, count: int, timeout: int) -> str:
        from scapy.all import sniff as scapy_sniff

        kwargs: Dict[str, Any] = {"count": count, "timeout": timeout}
        if interface:
            kwargs["iface"] = interface

        packets = scapy_sniff(**kwargs)

        summaries: List[Dict[str, str]] = []
        for pkt in packets:
            summaries.append({
                "summary": pkt.summary(),
                "length": len(pkt),
            })

        return json.dumps({
            "packet_count": len(summaries),
            "packets": summaries,
        })

    # ------------------------------------------------------------------ #
    # Parse
    # ------------------------------------------------------------------ #

    def parse_output(self, raw: str) -> Dict[str, Any]:
        """Parse the JSON string returned by the action callables."""
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"raw": raw}


# -------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------- #

def _parse_ports(port_str: str) -> List[int]:
    """Parse a port specification like '22,80,443' or '1-1024' into a list of ints."""
    ports: List[int] = []
    for part in port_str.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                ports.extend(range(int(start), int(end) + 1))
            except ValueError:
                continue
        else:
            try:
                ports.append(int(part))
            except ValueError:
                continue
    return ports


ToolRegistry.register(ScapyTool())
