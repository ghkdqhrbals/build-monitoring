import os
import tempfile
import time
import unittest

import build_monitor


class TestBuildMonitor(unittest.TestCase):
    def test_start_writes_env_vars(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as env_file:
            env_path = env_file.name

        try:
            os.environ["GITHUB_ENV"] = env_path
            rc = build_monitor.cmd_start("my-project")
            self.assertEqual(rc, 0)

            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("BUILD_START_TIME=", content)
            self.assertIn("BUILD_START_TIME_MS=", content)
            self.assertIn("PROJECT_NAME=my-project", content)
        finally:
            try:
                os.unlink(env_path)
            except OSError:
                pass

    def test_end_emits_build_time_ms_and_skipped_health(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as out_file:
            out_path = out_file.name

        try:
            os.environ["GITHUB_OUTPUT"] = out_path
            # Simulate start time 250ms ago
            start_ms = int(time.time() * 1000) - 250
            os.environ["BUILD_START_TIME_MS"] = str(start_ms)
            os.environ["PROJECT_NAME"] = "proj"

            rc = build_monitor.cmd_end(
                project_name="proj",
                job_status="success",
                webhook_url="",
                health_check_url="",
                health_wait_seconds=0.0,
            )
            self.assertEqual(rc, 0)

            with open(out_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()

            kv = dict(line.split("=", 1) for line in lines if "=" in line)
            self.assertIn("build_time_ms", kv)
            self.assertIn("build_status", kv)
            self.assertEqual(kv.get("health_status"), "skipped")
            self.assertEqual(kv.get("health_http_status"), "skipped")
            self.assertEqual(kv.get("health_latency_ms"), "skipped")

            # sanity: build_time_ms should be non-negative int
            self.assertGreaterEqual(int(kv["build_time_ms"]), 0)
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
