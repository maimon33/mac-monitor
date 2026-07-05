import unittest
from io import StringIO
from unittest.mock import patch

from mac_monitor.cli import emit
from mac_monitor.monitor import DiskStats, ProcessStats, build_network_stats, is_physical_interface_name
from mac_monitor.render import human_bytes, render_top_columns


class MonitorTests(unittest.TestCase):
    def test_network_rates_are_deltas_per_second(self):
        rows = build_network_stats({"en0": (300, 900)}, {"en0": (100, 300)}, 2.0)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].rx_rate, 100.0)
        self.assertEqual(rows[0].tx_rate, 300.0)

    def test_negative_network_delta_clamps_to_zero(self):
        rows = build_network_stats({"en0": (50, 50)}, {"en0": (100, 100)}, 1.0)

        self.assertEqual(rows[0].rx_rate, 0.0)
        self.assertEqual(rows[0].tx_rate, 0.0)

    def test_human_bytes(self):
        self.assertEqual(human_bytes(1024), "  1.0 KB")

    def test_physical_interface_names_are_en_devices(self):
        self.assertTrue(is_physical_interface_name("en0"))
        self.assertTrue(is_physical_interface_name("en12"))
        self.assertFalse(is_physical_interface_name("utun0"))
        self.assertFalse(is_physical_interface_name("bridge0"))
        self.assertFalse(is_physical_interface_name("awdl0"))

    def test_emit_does_not_append_frame_newline(self):
        rows = build_network_stats({"en0": (300, 900)}, None, 0.0)
        snapshot = type(
            "SnapshotStub",
            (),
            {
                "timestamp": 0,
                "network": rows,
                "disks": [],
                "processes": [],
                "cpu": type("CpuStub", (), {"percent": 1.0, "load_1m": 1.0, "load_5m": 1.0, "load_15m": 1.0, "cores": 1})(),
                "memory": type("MemoryStub", (), {"percent": 1.0, "used_bytes": 1, "total_bytes": 10})(),
            },
        )()
        config = type(
            "ConfigStub",
            (),
            {
                "warn_cpu_percent": 85.0,
                "warn_memory_percent": 85.0,
                "warn_disk_percent": 90.0,
                "view": "all",
                "top_count": 5,
            },
        )()
        output = StringIO()

        with patch("sys.stdout", output):
            emit(snapshot, config, as_json=False)

        self.assertFalse(output.getvalue().endswith("\n"))

    def test_top_columns_rank_each_resource_independently(self):
        snapshot = type(
            "SnapshotStub",
            (),
            {
                "processes": [
                    ProcessStats(1, 90.0, 1.0, 100, "/bin/cpu-heavy"),
                    ProcessStats(2, 5.0, 40.0, 4000, "/bin/ram-heavy"),
                ],
                "disks": [
                    DiskStats("/", "root", 100, 20, 80, 20.0),
                    DiskStats("/data", "data", 100, 90, 10, 90.0),
                ],
                "network": build_network_stats({"en0": (300, 900), "utun0": (900, 100)}, {"en0": (100, 300), "utun0": (100, 0)}, 1.0),
            },
        )()

        lines = render_top_columns(snapshot, count=2, warn_disk=90.0)
        output = "\n".join(lines)

        self.assertIn("1. cpu-heavy 0.9 c", output)
        self.assertIn("1. ram-heavy 3.9", output)
        self.assertIn("1. /data 90.0 B 90%", output)
        self.assertIn("1. utun0 900.0 B/s", output)


if __name__ == "__main__":
    unittest.main()
