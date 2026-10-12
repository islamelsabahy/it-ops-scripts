import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from itops import backup_verify, device_health, netcheck, network_audit  # noqa: E402


class ParsePortsTests(unittest.TestCase):
    def test_mixed_separators(self):
        self.assertEqual(netcheck.parse_ports("80;443|8080 22"), [80, 443, 8080, 22])

    def test_empty(self):
        self.assertEqual(netcheck.parse_ports(""), [])
        self.assertEqual(netcheck.parse_ports(None), [])

    def test_out_of_range(self):
        with self.assertRaises(ValueError):
            netcheck.parse_ports("70000")


class AuditHostTests(unittest.TestCase):
    row = {"name": "srv", "ip": "192.0.2.5", "role": "server", "ports": "80;443"}

    def test_up(self):
        with mock.patch.object(netcheck, "ping_host", return_value=True), \
             mock.patch.object(netcheck, "tcp_check", return_value=(True, 1.0)):
            self.assertEqual(network_audit.audit_host(self.row)["status"], "UP")

    def test_degraded(self):
        answers = iter([(True, 1.0), (False, None)])
        with mock.patch.object(netcheck, "ping_host", return_value=True), \
             mock.patch.object(netcheck, "tcp_check", side_effect=lambda *a, **k: next(answers)):
            result = network_audit.audit_host(self.row)
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["closed_ports"], [443])

    def test_down(self):
        with mock.patch.object(netcheck, "ping_host", return_value=False), \
             mock.patch.object(netcheck, "tcp_check", return_value=(False, None)):
            self.assertEqual(network_audit.audit_host(self.row)["status"], "DOWN")

    def test_exit_codes(self):
        self.assertEqual(network_audit.exit_code([{"status": "UP"}]), 0)
        self.assertEqual(network_audit.exit_code([{"status": "UP"}, {"status": "DEGRADED"}]), 1)
        self.assertEqual(network_audit.exit_code([{"status": "DEGRADED"}, {"status": "DOWN"}]), 2)


class DeviceReportTests(unittest.TestCase):
    def test_report_lists_only_problems(self):
        results = [
            {"name": "nvr-1", "type": "nvr", "site": "HQ", "ip": "198.51.100.10",
             "status": "UP", "closed_ports": []},
            {"name": "cam-1", "type": "camera", "site": "HQ", "ip": "198.51.100.11",
             "status": "DOWN", "closed_ports": [554]},
        ]
        report = device_health.build_report(results)
        self.assertIn("cam-1", report)
        self.assertNotIn("| nvr-1 |", report)
        self.assertIn("HQ (1/2 healthy)", report)


class BackupTests(unittest.TestCase):
    def _make(self, folder, name, size_bytes, age_hours):
        path = Path(folder) / name
        path.write_bytes(b"x" * size_bytes)
        ts = time.time() - age_hours * 3600
        os.utime(path, (ts, ts))

    def test_ok(self):
        with tempfile.TemporaryDirectory() as d:
            self._make(d, "a.dump", 2 * 1024 * 1024, 3)
            r = backup_verify.evaluate_backup("t", d, "*.dump", 26, 1)
            self.assertEqual(r.status, "OK")

    def test_old_backup_fails(self):
        with tempfile.TemporaryDirectory() as d:
            self._make(d, "a.dump", 2 * 1024 * 1024, 40)
            self.assertEqual(backup_verify.evaluate_backup("t", d, "*.dump", 26, 1).status, "FAIL")

    def test_small_backup_warns(self):
        with tempfile.TemporaryDirectory() as d:
            self._make(d, "a.dump", 1024, 2)
            self.assertEqual(backup_verify.evaluate_backup("t", d, "*.dump", 26, 1).status, "WARN")

    def test_missing_folder_and_no_match(self):
        self.assertEqual(backup_verify.evaluate_backup("t", "/no/such/dir").status, "FAIL")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(backup_verify.evaluate_backup("t", d, "*.dump").status, "FAIL")

    def test_newest_file_wins(self):
        with tempfile.TemporaryDirectory() as d:
            self._make(d, "old.dump", 2 * 1024 * 1024, 100)
            self._make(d, "new.dump", 2 * 1024 * 1024, 1)
            r = backup_verify.evaluate_backup("t", d, "*.dump", 26, 1)
            self.assertEqual((r.status, r.newest_file), ("OK", "new.dump"))


if __name__ == "__main__":
    unittest.main()
