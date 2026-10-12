"""Backup verification: is the newest backup recent enough and not suspiciously small?

Usage:
    python -m itops.backup_verify --jobs sample-data/backup_jobs.example.csv [--notify telegram|email]

Input CSV columns: name, path, pattern, max_age_hours, min_size_mb
Exit code: 0 all OK, 1 any WARN (e.g. unusually small), 2 any FAIL (missing/old).
Alerts are sent only for WARN/FAIL results.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from . import notify


@dataclass
class BackupResult:
    name: str
    path: str
    status: str  # OK | WARN | FAIL
    message: str
    newest_file: Optional[str] = None
    age_hours: Optional[float] = None
    size_mb: Optional[float] = None


def evaluate_backup(
    name: str,
    path: str,
    pattern: str = "*",
    max_age_hours: float = 26.0,
    min_size_mb: float = 1.0,
    now: Optional[float] = None,
) -> BackupResult:
    now = time.time() if now is None else now
    folder = Path(path)
    if not folder.is_dir():
        return BackupResult(name, path, "FAIL", "backup folder not found")

    files = [f for f in folder.glob(pattern) if f.is_file()]
    if not files:
        return BackupResult(name, path, "FAIL", f"no files match '{pattern}'")

    newest = max(files, key=lambda f: f.stat().st_mtime)
    age_hours = round((now - newest.stat().st_mtime) / 3600, 1)
    size_mb = round(newest.stat().st_size / (1024 * 1024), 2)

    if age_hours > max_age_hours:
        return BackupResult(
            name, path, "FAIL",
            f"newest backup is {age_hours}h old (limit {max_age_hours}h)",
            newest.name, age_hours, size_mb,
        )
    if size_mb < min_size_mb:
        return BackupResult(
            name, path, "WARN",
            f"newest backup is only {size_mb} MB (expected at least {min_size_mb} MB)",
            newest.name, age_hours, size_mb,
        )
    return BackupResult(name, path, "OK", "backup is recent and sized as expected",
                        newest.name, age_hours, size_mb)


def read_jobs(csv_path: Path) -> List[dict]:
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        return [
            {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            for row in csv.DictReader(fh)
        ]


def run_jobs(jobs: List[dict]) -> List[BackupResult]:
    results = []
    for job in jobs:
        results.append(
            evaluate_backup(
                job.get("name", job.get("path", "?")),
                job["path"],
                job.get("pattern") or "*",
                float(job.get("max_age_hours") or 26),
                float(job.get("min_size_mb") or 1),
            )
        )
    return results


def summarize(results: List[BackupResult]) -> str:
    lines = []
    for r in results:
        detail = f" [{r.newest_file}]" if r.newest_file else ""
        lines.append(f"{r.status:<4} {r.name}: {r.message}{detail}")
    return "\n".join(lines)


def exit_code(results: List[BackupResult]) -> int:
    statuses = {r.status for r in results}
    return 2 if "FAIL" in statuses else 1 if "WARN" in statuses else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify backup freshness and size.")
    parser.add_argument("--jobs", required=True, type=Path)
    parser.add_argument("--notify", choices=["telegram", "email"], help="alert on WARN/FAIL")
    args = parser.parse_args(argv)

    results = run_jobs(read_jobs(args.jobs))
    report = summarize(results)
    print(report)

    problems = [r for r in results if r.status != "OK"]
    if problems and args.notify:
        text = "Backup check needs attention:\n" + summarize(problems)
        sent = (
            notify.send_telegram(text)
            if args.notify == "telegram"
            else notify.send_email("Backup check needs attention", text)
        )
        if not sent:
            print(f"(alert via {args.notify} not sent: missing settings or network error)",
                  file=sys.stderr)
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
