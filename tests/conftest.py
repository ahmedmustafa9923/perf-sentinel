"""Shared fixtures for perf tests."""
import subprocess
import time
import httpx
import pytest


BOOKSTORE_URL = "http://127.0.0.1:8001"


@pytest.fixture(scope="session")
def bookstore():
    """Start BookStore in a subprocess for the test session, tear down after."""
    proc = subprocess.Popen(
        ["uvicorn", "bookstore.main:app", "--port", "8001", "--log-level", "warning"],
    )
    for _ in range(30):
        try:
            r = httpx.get(f"{BOOKSTORE_URL}/health", timeout=0.5)
            if r.status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        proc.terminate()
        raise RuntimeError("BookStore did not start in time")
    yield BOOKSTORE_URL
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def client(bookstore):
    with httpx.Client(base_url=bookstore, timeout=5.0) as c:
        yield c