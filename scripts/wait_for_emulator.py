#!/usr/bin/env python3
"""
Polls the Firestore emulator until it is ready, then exits 0.
Exits 1 if the emulator does not respond within the timeout.

Usage: python scripts/wait_for_emulator.py [--host HOST] [--timeout SECONDS]
"""
import argparse
import sys
import time
import urllib.request
import urllib.error


def wait_for_emulator(host: str = "localhost:8080", timeout: int = 60) -> bool:
    url = f"http://{host}/"
    deadline = time.time() + timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        try:
            urllib.request.urlopen(url, timeout=2)
            print(f"Firestore emulator is ready at {host} (attempt {attempt})")
            return True
        except Exception:
            remaining = int(deadline - time.time())
            print(f"Waiting for emulator at {host}... ({remaining}s remaining)", flush=True)
            time.sleep(2)

    print(f"ERROR: Firestore emulator at {host} did not respond within {timeout}s")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost:8080")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    if not wait_for_emulator(args.host, args.timeout):
        sys.exit(1)
