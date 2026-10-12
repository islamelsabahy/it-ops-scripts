"""Network audit: ping + expected-port check for a CSV inventory of hosts.

Usage:
    python -m itops.network_audit --hosts sample-data/hosts.example.csv --out reports

Input CSV columns: name, ip, role, ports   (ports separated by ';', optional)
Output: audit_<timestamp>.csv and audit_<timestamp>.md in the --out folder.
Exit code: 0 if every host is UP, 1 if any host is DEGRADED, 2 if any is DOWN.
"""

from __future__ import annotations

import argparse
import csv
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from . import netcheck


def read_hosts(path: Path) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = [
            {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            for row in csv.DictReader(fh)
        ]
    return [r for r in rows if r.get("ip")]


def audit_host(row: Dict[str, str], timeout: float = 2.0) -> Dict[str, object]:
    """Check one host. Status is UP, DEGRADED (reachable but an expected port is
    closed) or DOWN (no ping and no open port)."""
    ip = row["ip"]
    expected = netcheck.parse_ports(row.get("ports"))
    pinged = netcheck.ping_host(ip, timeout)
    open_ports: List[int] = []
    closed_ports: List[int] = []
    for port in expected:
        is_open, _ = netcheck.tcp_check(ip, port, timeout)
        (open_ports if is_open else closed_ports).append(port)

    if not pinged and not open_ports:
        status = "DOWN"
    elif closed_ports:
        status = "DEGRADED"
    else:
        status = "UP"

    return {
        "name": row.get("name", ""),
        "ip": ip,
        "role": row.get("role", ""),
        "site": row.get("site", ""),
        "type": row.get("type", ""),
        "ping": pinged,
        "open_ports": open_ports,
        "closed_ports": closed_ports,
        "status": status,
    }


def run_audit(rows: List[Dict[str, str]], timeout: float = 2.0, workers: int = 32):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda r: audit_host(r, timeout), rows))


def exit_code(results) -> int:
    statuses = {r["status"] for r in results}
    if "DOWN" in statuses:
        return 2
    if "DEGRADED" in statuses:
        return 1
    return 0


def write_reports(results, out_dir: Path, title: str = "Network Audit") -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"audit_{stamp}.csv"
    md_path = out_dir / f"audit_{stamp}.md"

    fields = ["name", "ip", "role", "status", "ping", "open_ports", "closed_ports"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(fields)
        for r in results:
            writer.writerow(
                [
                    r["name"], r["ip"], r["role"], r["status"], r["ping"],
                    ";".join(map(str, r["open_ports"])),
                    ";".join(map(str, r["closed_ports"])),
                ]
            )

    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("UP", "DEGRADED", "DOWN")}
    lines = [
        f"# {title}",
        "",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"**UP:** {counts['UP']}  |  **DEGRADED:** {counts['DEGRADED']}  |  **DOWN:** {counts['DOWN']}",
        "",
        "| Name | IP | Role | Status | Ping | Closed ports |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: (x["status"] == "UP", x["name"])):
        lines.append(
            f"| {r['name']} | {r['ip']} | {r['role']} | {r['status']} | "
            f"{'yes' if r['ping'] else 'no'} | {', '.join(map(str, r['closed_ports'])) or '-'} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"csv": csv_path, "md": md_path}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ping + port audit for a host inventory CSV.")
    parser.add_argument("--hosts", required=True, type=Path, help="CSV inventory")
    parser.add_argument("--out", type=Path, default=Path("reports"), help="report folder")
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--workers", type=int, default=32)
    args = parser.parse_args(argv)

    rows = read_hosts(args.hosts)
    if not rows:
        print("No hosts found in the CSV.", file=sys.stderr)
        return 2
    results = run_audit(rows, args.timeout, args.workers)
    paths = write_reports(results, args.out)
    print(f"Checked {len(results)} hosts -> {paths['md']}")
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
