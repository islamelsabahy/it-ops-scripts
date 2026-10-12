"""CCTV / PBX / access-control health check, grouped by site.

Usage:
    python -m itops.device_health --devices sample-data/devices.example.csv --out reports

Input CSV columns: name, type, site, ip, ports
    type examples: nvr, camera, pbx, access-controller
Typical ports: NVR web 80/443, RTSP 554, PBX web 80/443, SIP 5060.

Only outages (DOWN or DEGRADED) are listed in the "needs attention" section so
the report can be sent straight to the site engineer or vendor.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .network_audit import exit_code, read_hosts, run_audit


def build_report(results) -> str:
    by_site = defaultdict(list)
    for r in results:
        by_site[r["site"] or "Unassigned"].append(r)

    total_bad = sum(1 for r in results if r["status"] != "UP")
    lines = [
        "# Device Health Report (CCTV / PBX / Access control)",
        "",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        f"Devices checked: {len(results)}  |  Needing attention: {total_bad}",
        "",
    ]
    for site in sorted(by_site):
        devices = by_site[site]
        bad = [d for d in devices if d["status"] != "UP"]
        lines.append(f"## {site} ({len(devices) - len(bad)}/{len(devices)} healthy)")
        lines.append("")
        if not bad:
            lines.append("All devices healthy.")
        else:
            lines.append("| Device | Type | IP | Status | Closed ports |")
            lines.append("|---|---|---|---|---|")
            for d in sorted(bad, key=lambda x: x["name"]):
                lines.append(
                    f"| {d['name']} | {d['type']} | {d['ip']} | {d['status']} | "
                    f"{', '.join(map(str, d['closed_ports'])) or '-'} |"
                )
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Health check for CCTV, PBX and access devices.")
    parser.add_argument("--devices", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=Path("reports"))
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args(argv)

    rows = read_hosts(args.devices)
    if not rows:
        print("No devices found in the CSV.", file=sys.stderr)
        return 2
    results = run_audit(rows, args.timeout)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"device_health_{datetime.now():%Y%m%d_%H%M%S}.md"
    path.write_text(build_report(results), encoding="utf-8")
    print(f"Checked {len(results)} devices -> {path}")
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
