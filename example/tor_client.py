"""
tor_client.py
~~~~~~~~~~~~~
Minimal helper for making HTTP requests through a Tor SOCKS5 proxy
and rotating the exit IP via stem's NEWNYM signal.

Requirements:
    pip install httpx[socks] stem

Docker setup (see docker-compose.yml):
    docker compose up -d
    # wait ~30s for Tor to bootstrap, then run this script
"""

import logging
import os
import time

import httpx
from stem import Signal
from stem.control import Controller

# ---------------------------------------------------------------------------
# Config — override via environment variables in production
# ---------------------------------------------------------------------------
TOR_SOCKS_HOST = os.getenv("TOR_SOCKS_HOST", "127.0.0.1")
TOR_SOCKS_PORT = int(os.getenv("TOR_SOCKS_PORT", "9150"))
TOR_CONTROL_HOST = os.getenv("TOR_CONTROL_HOST", "127.0.0.1")
TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", "9151"))
TOR_CONTROL_PASSWORD = os.getenv("TOR_CONTROL_PASSWORD", "changeme")

# socks5h = DNS resolved inside Tor (no local DNS leak)
SOCKS_URL = f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Circuit rotation
# ---------------------------------------------------------------------------


def new_circuit() -> None:
    """
    Ask Tor for a fresh circuit (new exit IP).

    Tor enforces a cooldown (get_newnym_wait()) between NEWNYM signals —
    typically 10 seconds. Calling this more often than that is a no-op on
    the network side; the sleep here ensures we actually get a new circuit.
    """
    with Controller.from_port(address=TOR_CONTROL_HOST, port=TOR_CONTROL_PORT) as ctrl:  # type: ignore
        ctrl.authenticate(password=TOR_CONTROL_PASSWORD)
        wait = ctrl.get_newnym_wait()
        if wait > 0:
            log.info("Tor cooldown: waiting %.1fs before requesting new circuit", wait)
            time.sleep(wait)
        ctrl.signal(Signal.NEWNYM)  # type: ignore
        log.info("New Tor circuit requested.")


# ---------------------------------------------------------------------------
# HTTP client factory
# ---------------------------------------------------------------------------


def tor_client(timeout: int = 30) -> httpx.Client:
    """Return an httpx.Client pre-configured to route through Tor."""
    return httpx.Client(proxy=SOCKS_URL, timeout=timeout)


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def get_exit_ip(client: httpx.Client) -> str:
    """Return the current Tor exit IP (via httpbin)."""
    resp = client.get("https://httpbin.org/ip")
    resp.raise_for_status()
    return resp.json()["origin"]


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def main() -> None:
    urls = [
        "https://httpbin.org/ip",
        "https://httpbin.org/ip",
        "https://httpbin.org/ip",
    ]

    for i, url in enumerate(urls, start=1):
        with tor_client() as client:
            ip = get_exit_ip(client)
            log.info("[%d] Exit IP: %s", i, ip)

            resp = client.get(url)
            log.info("[%d] %s → %d", i, url, resp.status_code)

        # Rotate before the next request (skip rotation after the last one)
        if i < len(urls):
            new_circuit()


if __name__ == "__main__":
    main()
