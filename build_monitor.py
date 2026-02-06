#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


def _append_env_file(path: str, key: str, value: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def _append_output_file(path: str, key: str, value: str) -> None:
    # GitHub Actions outputs: https://docs.github.com/actions/using-workflows/workflow-commands-for-github-actions#setting-an-output-parameter
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _now_epoch_seconds() -> int:
    return int(time.time())


@dataclass
class HealthResult:
    status: str  # ok|fail|skipped
    http_status: str  # e.g. 200, 503, 000, skipped
    latency_ms: str  # numeric string, unknown, skipped


def _health_check(url: str, timeout_seconds: float = 10.0) -> HealthResult:
    if not url:
        return HealthResult(status="skipped", http_status="skipped", latency_ms="skipped")

    start = time.monotonic()
    code: Optional[int] = None

    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            code = getattr(resp, "status", None)
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        code = 0

    elapsed_ms = int((time.monotonic() - start) * 1000)

    if code == 200:
        status = "ok"
    else:
        status = "fail"

    http_status = str(code).zfill(3) if code is not None else "000"
    if http_status == "000":
        status = "fail"

    return HealthResult(status=status, http_status=http_status, latency_ms=str(elapsed_ms))


def _health_check_wait_for_200(
    url: str,
    *,
    timeout_seconds: float = 10.0,
    wait_seconds: float = 0.0,
    interval_seconds: float = 1.0,
) -> HealthResult:
    """Health-check URL and optionally wait until it returns HTTP 200.

    - If url is empty => skipped
    - If wait_seconds <= 0 => single check
    - Otherwise, keep checking until HTTP 200 or deadline reached
    """

    if not url:
        return HealthResult(status="skipped", http_status="skipped", latency_ms="skipped")

    try:
        wait_seconds = float(wait_seconds)
    except Exception:
        wait_seconds = 0.0

    try:
        interval_seconds = float(interval_seconds)
    except Exception:
        interval_seconds = 1.0

    if wait_seconds <= 0:
        return _health_check(url, timeout_seconds=timeout_seconds)

    deadline = time.monotonic() + max(0.0, wait_seconds)
    interval = max(0.1, interval_seconds)

    last_result = HealthResult(status="fail", http_status="000", latency_ms="0")
    while True:
        last_result = _health_check(url, timeout_seconds=timeout_seconds)
        if last_result.http_status == "200":
            return HealthResult(status="ok", http_status="200", latency_ms=last_result.latency_ms)

        now = time.monotonic()
        if now >= deadline:
            return last_result

        remaining = deadline - now
        time.sleep(min(interval, max(0.0, remaining)))


def _post_webhook(webhook_url: str, payload: dict) -> None:
    if not webhook_url:
        return

    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            # Consume response so connection closes cleanly
            resp.read()
    except Exception as e:
        # Webhook delivery must not fail the job.
        print(f"Build Monitor: webhook POST failed: {e}", file=sys.stderr)


def cmd_start(project_name: str) -> int:
    github_env = _env("GITHUB_ENV")
    if not github_env:
        print("Build Monitor: GITHUB_ENV not set; are you running outside GitHub Actions?", file=sys.stderr)
        return 1

    start_s = _now_epoch_seconds()
    start_ms = int(time.time() * 1000)
    _append_env_file(github_env, "BUILD_START_TIME", str(start_s))
    _append_env_file(github_env, "BUILD_START_TIME_MS", str(start_ms))
    _append_env_file(github_env, "PROJECT_NAME", project_name or "unknown")
    print(f"Build monitoring started for {project_name or 'unknown'}")
    return 0


def cmd_end(
    project_name: str,
    job_status: str,
    webhook_url: str,
    health_check_url: str,
    health_wait_seconds: float,
) -> int:
    github_output = _env("GITHUB_OUTPUT")
    if not github_output:
        print("Build Monitor: GITHUB_OUTPUT not set; are you running outside GitHub Actions?", file=sys.stderr)
        return 1

    end_ms = int(time.time() * 1000)
    start_ms_str = _env("BUILD_START_TIME_MS", "")
    if start_ms_str.strip():
        try:
            start_ms = int(start_ms_str)
        except ValueError:
            start_ms = end_ms
    else:
        # Back-compat: older start step stored seconds
        start_s_str = _env("BUILD_START_TIME", "")
        try:
            start_s = int(start_s_str) if start_s_str else int(end_ms / 1000)
        except ValueError:
            start_s = int(end_ms / 1000)
        start_ms = start_s * 1000

    build_time_ms = max(0, end_ms - start_ms)

    status = (job_status or "unknown").strip() or "unknown"

    effective_project = (_env("PROJECT_NAME") or project_name or "unknown").strip() or "unknown"

    # Retry health check every 1 second while waiting for HTTP 200.
    health = _health_check_wait_for_200(
        health_check_url,
        wait_seconds=health_wait_seconds,
        interval_seconds=1.0,
    )

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    payload = {
        "project": effective_project,
        "build_time_ms": build_time_ms,
        "status": status,
        "health_status": health.status,
        "health_http_status": health.http_status,
        "health_latency_ms": health.latency_ms,
        "timestamp": timestamp,
        "repository": _env("GITHUB_REPOSITORY"),
        "workflow": _env("GITHUB_WORKFLOW"),
        "run_id": _env("GITHUB_RUN_ID"),
        "run_number": _env("GITHUB_RUN_NUMBER"),
        "job": _env("GITHUB_JOB"),
        "sha": _env("GITHUB_SHA"),
    }

    _post_webhook(webhook_url, payload)

    print(f"Build completed in {build_time_ms} milliseconds with status: {status}")

    _append_output_file(github_output, "build_time_ms", str(build_time_ms))
    _append_output_file(github_output, "build_status", status)
    _append_output_file(github_output, "health_status", health.status)
    _append_output_file(github_output, "health_http_status", health.http_status)
    _append_output_file(github_output, "health_latency_ms", health.latency_ms)

    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="build_monitor")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Record build start time")
    p_start.add_argument("--project-name", default="unknown")

    p_end = sub.add_parser("end", help="Compute build duration and emit outputs")
    p_end.add_argument("--project-name", default="unknown")
    p_end.add_argument("--job-status", default="unknown")
    p_end.add_argument("--webhook-url", default="")
    p_end.add_argument("--health-check-url", default="")
    p_end.add_argument(
        "--health-wait-seconds",
        type=float,
        default=0.0,
        help="Wait up to N seconds for health-check URL to return HTTP 200 (0 = no wait)",
    )

    args = parser.parse_args(argv)

    if args.command == "start":
        return cmd_start(project_name=args.project_name)

    if args.command == "end":
        return cmd_end(
            project_name=args.project_name,
            job_status=args.job_status,
            webhook_url=args.webhook_url,
            health_check_url=args.health_check_url,
            health_wait_seconds=args.health_wait_seconds,
        )

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
