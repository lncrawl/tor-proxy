# tor-proxy

[![Docker](https://github.com/lncrawl/tor-proxy/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/lncrawl/tor-proxy/actions/workflows/docker-publish.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/sdipu/tor-proxy)](https://hub.docker.com/r/sdipu/tor-proxy)
[![Image Size](https://img.shields.io/docker/image-size/sdipu/tor-proxy/latest)](https://hub.docker.com/r/sdipu/tor-proxy)

A minimal, up-to-date Tor Docker image built on **Alpine**.  
Exposes a SOCKS5 proxy (port **9150**) and a control port (port **9151**) so Python's
`stem` library can rotate circuits programmatically.

## Why a custom image?

| Image                            | Tor version | Control port      | Last updated |
| -------------------------------- | ----------- | ----------------- | ------------ |
| `dperson/torproxy`               | old         | manual torrc only | ~5 years ago |
| `barneybuffet/tor`               | old         | yes (buggy hash)  | ~4 years ago |
| `peterdavehello/tor-socks-proxy` | recent      | ❌ no             | active       |

This image:

- Installs Tor directly from Alpine's community repo — always the latest available version.
- Hashes `CONTROL_PASSWORD` **at runtime** so no stale hash is ever baked in.
- Supports multi-arch builds (`linux/amd64`, `linux/arm64`).
- Rebuilds automatically every week to pick up Tor/Alpine updates.

---

## Project layout

```
tor-proxy/
├── .github/
│   └── workflows/
│       └── docker-publish.yml  # build + push to Docker Hub & GHCR
├── docker/
│   ├── Dockerfile              # Alpine + tor + su-exec
│   └── entrypoint.sh           # hashes password at runtime, writes torrc
├── example/
│   └── tor_client.py           # httpx + stem circuit-rotation example
├── .env.example                # template for local .env
├── compose.yml
├── LICENSE
└── README.md
```

---

## Quick start

### Pull from Docker Hub

```bash
docker compose pull
docker compose up -d
```

### Or build locally

```bash
docker compose up -d --build
```

### Verify the proxy works (takes ~30 s for Tor to bootstrap)

```bash
docker compose logs -f

# once you see "Bootstrapped 100%":
curl --socks5-hostname 127.0.0.1:9150 https://httpbin.org/ip
```

---

## Configuration

All settings are environment variables. Copy `.env.example` to `.env` and edit:

| Variable           | Default                   | Description                             |
| ------------------ | ------------------------- | --------------------------------------- |
| `CONTROL_PASSWORD` | `changeme`                | Plain-text password — hashed at startup |
| `SOCKS_HOST`       | `0.0.0.0`                 | SOCKS5 bind address inside container    |
| `CONTROL_HOST`     | `0.0.0.0`                 | Control port bind address               |
| `SOCKS_POLICY`     | RFC1918 ranges + loopback | Comma-separated `accept IP/CIDR` rules  |

The hashed password is generated each time the container starts via:

```sh
tor --hash-password "${CONTROL_PASSWORD}"
```

This avoids the `Bad HashedControlPassword: wrong length or bad encoding` error
that plagues older images that bake a stale hash into the config.

---

## Python usage

Install dependencies:

```bash
pip install "httpx[socks]" stem
```

Set env vars if not using defaults:

```bash
export TOR_CONTROL_PASSWORD=changeme
```

Run:

```bash
python example/tor_client.py
```

Expected output:

```
2026-06-08 12:00:01 INFO [1] Exit IP: 185.220.101.5
2026-06-08 12:00:01 INFO [1] https://httpbin.org/ip → 200
2026-06-08 12:00:11 INFO New Tor circuit requested.
2026-06-08 12:00:11 INFO [2] Exit IP: 178.175.128.50   ← different IP
...
```

---

## How circuit rotation works

```
your script
    │
    ├─ HTTP request ──► SOCKS5 port 9150 ──► Tor network ──► exit node ──► target
    │
    └─ stem NEWNYM  ──► Control port 9151 ──► Tor picks a new 3-hop circuit
```

`stem` sends `SIGNAL NEWNYM` to the control port. Tor enforces a ~10 s cooldown
between rotations. The `get_newnym_wait()` call in `tor_client.py` respects this
automatically so you always get a genuinely new exit node.

---

## Ports

| Port | Protocol | Purpose                         |
| ---- | -------- | ------------------------------- |
| 9150 | TCP      | SOCKS5 proxy (connect your app) |
| 9151 | TCP      | Control port (stem / NEWNYM)    |

Both ports are bound to `127.0.0.1` on the host by default (see `compose.yml`).

---

## Publishing a new image manually

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag sdipu/tor-proxy:latest \
  --push \
  ./docker
```

CI (`.github/workflows/docker-publish.yml`) does this automatically on every push
to `main` and on `v*` tags.

---

## Rebuilding when Tor updates

The weekly scheduled CI build handles this automatically. To rebuild manually:

```bash
docker compose build --no-cache
docker compose up -d
```

---

## Security notes

- The control port is bound only to `127.0.0.1` on the host (see `compose.yml`).
  **Never expose port 9151 publicly.**
- Store `CONTROL_PASSWORD` in a `.env` file (excluded from version control) or use
  Docker secrets in production.
- The SOCKS proxy accepts only RFC1918 addresses by default. Adjust `SOCKS_POLICY`
  if your app container is on a different subnet.
- The image runs Tor as the `tor` user (created by the Alpine package) — not root.
