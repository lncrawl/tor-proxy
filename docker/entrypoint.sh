#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# Generate a hashed control password at startup so the plain-text password
# is never baked into the image. tor --hash-password outputs a line like:
#   16:ABCDEF...
# ---------------------------------------------------------------------------
HASHED_PW=$(tor --hash-password "${CONTROL_PASSWORD}" | tail -1)

# ---------------------------------------------------------------------------
# Build /etc/tor/torrc from environment variables.
# We write it fresh each startup so settings survive image rebuilds.
# ---------------------------------------------------------------------------
cat > /etc/tor/torrc <<EOF
# === SOCKS5 proxy ===
SocksPort ${SOCKS_HOST}:9150

# Accept policy: allow only the listed CIDRs, reject everything else.
$(echo "${SOCKS_POLICY}" | tr ',' '\n' | sed 's/^ */SocksPolicy /')

# === Control port (used by stem for NEWNYM / circuit rotation) ===
ControlPort ${CONTROL_HOST}:9151
HashedControlPassword ${HASHED_PW}

# === Data & logging ===
DataDirectory /var/lib/tor
Log notice stderr
EOF

echo "[tor-proxy] torrc written. Starting Tor..."
echo "[tor-proxy] SOCKS5  -> ${SOCKS_HOST}:9150"
echo "[tor-proxy] Control -> ${CONTROL_HOST}:9151 (password auth)"

# Run as the 'tor' user created by the apk package.
exec su-exec tor tor -f /etc/tor/torrc "$@"
