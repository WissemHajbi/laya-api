#!/usr/bin/env python3
"""Dependency-free HTTP load test for the local Laya API."""

import argparse
import concurrent.futures
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    rank = (len(ordered) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/predict")
    parser.add_argument("--payload", default="examples/request.json")
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()

    body = Path(args.payload).read_bytes()

    def send(_: int) -> tuple[float, int, str | None]:
        request = urllib.request.Request(
            args.url,
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                response.read()
                return time.perf_counter() - started, response.status, None
        except urllib.error.HTTPError as exc:
            return time.perf_counter() - started, exc.code, str(exc)
        except Exception as exc:
            return time.perf_counter() - started, 0, str(exc)

    wall_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(send, range(args.requests)))
    wall = time.perf_counter() - wall_started

    successful = [duration for duration, status, error in results if status == 200 and error is None]
    failures = [
        {"status": status, "error": error}
        for _, status, error in results
        if status != 200 or error is not None
    ]

    output = {
        "requests": args.requests,
        "concurrency": args.concurrency,
        "successful": len(successful),
        "failed": len(failures),
        "wall_seconds": round(wall, 4),
        "throughput_requests_per_second": round(len(successful) / wall, 3),
        "latency_ms": {
            "min": round(min(successful) * 1000, 2) if successful else None,
            "mean": round(statistics.mean(successful) * 1000, 2) if successful else None,
            "p50": round(percentile(successful, 0.50) * 1000, 2) if successful else None,
            "p95": round(percentile(successful, 0.95) * 1000, 2) if successful else None,
            "p99": round(percentile(successful, 0.99) * 1000, 2) if successful else None,
            "max": round(max(successful) * 1000, 2) if successful else None,
        },
        "errors": failures[:5],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
