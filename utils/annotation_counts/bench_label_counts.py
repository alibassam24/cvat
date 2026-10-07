# SPDX-License-Identifier: MIT

"""
Time GET /api/test/tasks/{id}/label-counts the way Objectives MO-1 describes:
5 runs, each 5 warm-up requests followed by 50 timed ones, sent one after another
over a single keep-alive connection. Prints every run and a summary line.

By default it logs in once and sends the session cookie, like the web UI does.
--basic-auth sends the password with every request instead, which makes Django
hash it each time (PBKDF2, a few hundred ms on its own).
"""

import argparse
import base64
import http.client
import json
import statistics
import time
from http.cookies import SimpleCookie


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))]


def session_headers(conn, user: str, password: str) -> dict:
    conn.request(
        "POST",
        "/api/auth/login",
        body=json.dumps({"username": user, "password": password}),
        headers={"Content-Type": "application/json"},
    )
    response = conn.getresponse()
    response.read()
    if response.status != 200:
        raise RuntimeError(f"login failed with HTTP {response.status}")

    cookies = SimpleCookie()
    for header in response.headers.get_all("Set-Cookie"):
        cookies.load(header)
    return {"Cookie": "; ".join(f"{name}={morsel.value}" for name, morsel in cookies.items())}


def basic_auth_headers(user: str, password: str) -> dict:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def timed_requests(conn, path: str, headers: dict, count: int) -> list[float]:
    timings_ms = []
    for _ in range(count):
        start = time.perf_counter()
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        response.read()
        timings_ms.append((time.perf_counter() - start) * 1000)
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP {response.status} for {path}")
    return timings_ms


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("task_id", type=int)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", required=True)
    parser.add_argument("--basic-auth", action="store_true", help="send the password every time")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--requests", type=int, default=50)
    args = parser.parse_args()

    path = f"/api/test/tasks/{args.task_id}/label-counts"
    conn = http.client.HTTPConnection(args.host, args.port, timeout=30)
    try:
        if args.basic_auth:
            headers = basic_auth_headers(args.user, args.password)
        else:
            headers = session_headers(conn, args.user, args.password)

        auth = "basic auth" if args.basic_auth else "session cookie"
        print(
            f"GET {path}  {auth}  runs={args.runs} warmup={args.warmup}"
            f" requests={args.requests}"
        )
        run_medians = []
        for run in range(1, args.runs + 1):
            timed_requests(conn, path, headers, args.warmup)
            timings = timed_requests(conn, path, headers, args.requests)
            median = statistics.median(timings)
            run_medians.append(median)
            print(
                f"run {run}: median {median:.1f} ms  p95 {percentile(timings, 0.95):.1f} ms"
                f"  min {min(timings):.1f} ms  max {max(timings):.1f} ms"
            )
    finally:
        conn.close()

    print(
        f"median of run medians: {statistics.median(run_medians):.1f} ms"
        f"  spread: {min(run_medians):.1f}-{max(run_medians):.1f} ms"
    )


if __name__ == "__main__":
    main()
