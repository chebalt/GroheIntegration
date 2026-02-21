#!/usr/bin/env python3
"""
Seeds the Firestore `configuration` collection with the document needed by
FirebaseConfigurationService at startup of NavigationApi and ProductsApi.

Must be run BEFORE starting the phase4 containers (navigation-api, products-api),
because both services read the configuration collection synchronously at startup.

The document contains:
  - project_id      — used by FirestoreDbResolver to build per-locale Firestore connections
  - database_de_de  — maps locale "de-DE" to Firestore database "(default)"
  - fallback_locale — fallback when requested locale has no database_* entry

Usage:
    python scripts/seed_config.py [--host HOST]
"""
import argparse
import os
import sys


def seed_config(host: str = "localhost:8080") -> None:
    os.environ["FIRESTORE_EMULATOR_HOST"] = host
    os.environ.setdefault("GCLOUD_PROJECT", "demo-project")

    from google.cloud import firestore

    client = firestore.Client(project="demo-project")

    config_doc = {
        "project_id": "demo-project",
        "database_de_de": "(default)",
        "fallback_locale": "de_de",
    }

    client.collection("configuration").document("config").set(config_doc)
    print(f"Seeded configuration/config in emulator at {host}")
    print(f"  project_id    = demo-project")
    print(f"  database_de_de = (default)")
    print(f"  fallback_locale = de_de")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed Firestore configuration collection for Phase 4 services."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080"),
        help="Firestore emulator host:port (default: localhost:8080)",
    )
    args = parser.parse_args()

    try:
        seed_config(args.host)
    except Exception as e:
        print(f"ERROR: Failed to seed configuration: {e}", file=sys.stderr)
        sys.exit(1)
