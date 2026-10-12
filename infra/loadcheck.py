"""A small load check for the API. Standard library only.

    python infra/loadcheck.py --base http://localhost:8000 --email you@example.test --password ...

It measures response times for the probes (no sign-in) and, if credentials are given,
for the main signed-in reads. It stays under the API's own rate limits on purpose: the
point is to notice a slow endpoint, not to stress the rate limiter. Use a throwaway
account. Nothing is written to the account.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def timed(opener: urllib.request.OpenerDirector, url: str) -> tuple[float, int]:
    started = time.perf_counter()
    try:
        with opener.open(url, timeout=15) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    return (time.perf_counter() - started) * 1000, status


def run(opener: urllib.request.OpenerDirector, url: str, total: int, workers: int) -> dict[str, object]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda _: timed(opener, url), range(total)))
    times = sorted(ms for ms, _ in results)
    statuses = sorted({status for _, status in results})
    return {
        "requests": total,
        "statuses": statuses,
        "p50_ms": round(statistics.median(times), 1),
        "p95_ms": round(times[int(len(times) * 0.95) - 1], 1),
        "max_ms": round(times[-1], 1),
    }


def sign_in(base: str, email: str, password: str) -> urllib.request.OpenerDirector:
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    with opener.open(f"{base}/api/v1/auth/csrf", timeout=15) as response:
        token = json.load(response)["csrf_token"]
    request = urllib.request.Request(  # noqa: S310 - the base URL is the operator's own API
        f"{base}/api/v1/auth/login",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json", "X-CSRFToken": token},
        method="POST",
    )
    opener.open(request, timeout=15).read()
    return opener


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--email")
    parser.add_argument("--password")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    anonymous = urllib.request.build_opener()
    report = {
        "GET /api/v1/health": run(anonymous, f"{args.base}/api/v1/health", 300, args.workers),
        "GET /api/v1/ready": run(anonymous, f"{args.base}/api/v1/ready", 300, args.workers),
    }
    if args.email and args.password:
        signed_in = sign_in(args.base, args.email, args.password)
        for path in ("check-ins", "patterns?days=90", "exercises", "sharing/consent"):
            report[f"GET /api/v1/{path}"] = run(
                signed_in, f"{args.base}/api/v1/{path}", 40, args.workers
            )
    for name, result in report.items():
        print(f"{name:34} {result}")


if __name__ == "__main__":
    main()
