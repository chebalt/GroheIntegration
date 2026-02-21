#!/usr/bin/env python3
"""
Polls a service endpoint until it is ready, then exits 0.
Exits 1 if the service does not respond within the timeout.

Usage: python scripts/wait_for_emulator.py [--host HOST] [--path PATH] [--timeout SECONDS]
"""
import argparse
import sys
import time
import urllib.request
import urllib.error


def wait_for_emulator(host: str = "localhost:8080", timeout: int = 60, path: str = "/") -> bool:
    url = f"http://{host}{path}"
    deadline = time.time() + timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        try:
            urllib.request.urlopen(url, timeout=2)
            print(f"Service is ready at {host}{path} (attempt {attempt})")
            return True
        except urllib.error.HTTPError as e:
            if e.code < 500:
                # 4xx means the service is up but the path returned an error — still counts as ready
                print(f"Service is ready at {host}{path} (status {e.code}, attempt {attempt})")
                return True
            remaining = int(deadline - time.time())
            print(f"Waiting for service at {host}{path}... (status {e.code}, {remaining}s remaining)", flush=True)
            time.sleep(2)
        except Exception:
            remaining = int(deadline - time.time())
            print(f"Waiting for service at {host}{path}... ({remaining}s remaining)", flush=True)
            time.sleep(2)

    print(f"ERROR: Service at {host}{path} did not respond within {timeout}s")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost:8080")
    parser.add_argument("--path", default="/")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    if not wait_for_emulator(args.host, args.timeout, args.path):
        sys.exit(1)
