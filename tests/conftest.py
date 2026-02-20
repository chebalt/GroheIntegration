"""
Shared pytest fixtures for the Grohe NEO integration test suite.

Infrastructure assumptions:
  - Firestore emulator: localhost:8080  (started via `make infra-up`)
  - Data-loader: grohe-neo-data-loader/  (run via subprocess using its .venv)
  - CSV fixtures:  integration/fixtures/csv/
"""

import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import pytest
from google.cloud import firestore

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT       = Path(__file__).parent.parent.parent          # NEO/
INTEGRATION_DIR = Path(__file__).parent.parent                 # NEO/integration/
DATA_LOADER_DIR = REPO_ROOT / "grohe-neo-data-loader"
FIXTURES_CSV    = INTEGRATION_DIR / "fixtures" / "csv"

# Python executable inside the data-loader's virtualenv
if platform.system() == "Windows":
    DATA_LOADER_PYTHON = DATA_LOADER_DIR / ".venv" / "Scripts" / "python.exe"
else:
    DATA_LOADER_PYTHON = DATA_LOADER_DIR / ".venv" / "bin" / "python"

# Fallback to system Python if the venv doesn't exist yet
if not DATA_LOADER_PYTHON.exists():
    DATA_LOADER_PYTHON = Path(sys.executable)

# ── Emulator config ───────────────────────────────────────────────────────────

EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
PROJECT_ID    = "demo-project"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_emulator_up(host: str = EMULATOR_HOST, timeout: float = 2.0) -> bool:
    """Return True if the Firestore emulator is reachable."""
    import urllib.request, urllib.error
    try:
        urllib.request.urlopen(f"http://{host}/", timeout=timeout)
        return True
    except Exception:
        return False


def _clear_emulator(client: firestore.Client) -> None:
    """Delete every document in every known collection (for test isolation)."""
    collections = [
        "PLProductContent", "PLCategory", "PLFeatureContent",
        "PLVariant", "ProductIndexData", "CategoryRouting",
        "cacheEntries", "cacheRegions",
    ]
    for name in collections:
        for doc in client.collection(name).stream():
            doc.reference.delete()


# ── Session-scoped fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def emulator_available() -> bool:
    return _is_emulator_up()


@pytest.fixture(scope="session")
def firestore_client(emulator_available):
    """Firestore client connected to the local emulator."""
    if not emulator_available:
        pytest.skip("Firestore emulator not running — start it with: make infra-up")

    os.environ["FIRESTORE_EMULATOR_HOST"] = EMULATOR_HOST
    os.environ["GCLOUD_PROJECT"]          = PROJECT_ID

    return firestore.Client(project=PROJECT_ID)


@pytest.fixture(scope="session")
def pipeline_result(firestore_client):
    """
    Run the ETL pipeline once for the entire test session.

    Clears the emulator before running so tests always start from a known state.
    Returns the CompletedProcess from the data-loader subprocess.
    """
    _clear_emulator(firestore_client)

    env = {
        **os.environ,
        "FIRESTORE_EMULATOR_HOST": EMULATOR_HOST,
        "GCLOUD_PROJECT":          PROJECT_ID,
    }

    proc = subprocess.run(
        [
            str(DATA_LOADER_PYTHON), "main.py",
            "--input-dir",    str(FIXTURES_CSV),
            "--to-firestore",
            "--firestore-emulator",
            "--log-level",    "WARNING",
        ],
        cwd=DATA_LOADER_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )

    return proc


# ── Function-scoped fixture for tests that need a clean emulator ──────────────

@pytest.fixture
def clean_firestore(firestore_client):
    """Yields a clean Firestore client; clears all collections after each test."""
    yield firestore_client
    _clear_emulator(firestore_client)
