"""Low-level reachability helpers shared by the audit and health-check tools."""

from __future__ import annotations

import platform
import re
import socket
import subprocess
import time
from typing import List, Optional, Tuple


def ping_host(host: str, timeout: float = 2.0) -> bool:
    """Return True if a single ICMP echo gets a reply.

    Uses the system ``ping`` binary so no raw-socket privileges are needed.
    """
    if platform.system().lower() == "windows":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, int(timeout))), host]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 3
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return result.returncode == 0


def tcp_check(host: str, port: int, timeout: float = 2.0) -> Tuple[bool, Optional[float]]:
    """Try a TCP connect. Returns (is_open, latency_ms or None)."""
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, round((time.monotonic() - start) * 1000, 1)
    except OSError:
        return False, None


def parse_ports(value: Optional[str]) -> List[int]:
    """Parse a port list such as ``"80;443|8080 22"`` into ``[80, 443, 8080, 22]``.

    Separators: semicolon, pipe or whitespace (commas are avoided because the
    value usually lives inside a CSV cell). Raises ValueError on bad input.
    """
    if not value:
        return []
    ports: List[int] = []
    for token in re.split(r"[;|\s]+", value.strip()):
        if not token:
            continue
        port = int(token)
        if not 1 <= port <= 65535:
            raise ValueError(f"port out of range: {port}")
        ports.append(port)
    return ports
