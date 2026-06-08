FROM alpine:latest

LABEL maintainer="dipu.sudipta@gmail.com" \
    description="Minimal Tor SOCKS5 proxy with control port for circuit rotation" \
    org.opencontainers.image.source="https://github.com/lncrawl/tor-proxy"

# Tor is in the community repo
RUN apk add --no-cache tor su-exec

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# tor user is created by the apk package; data dir is /var/lib/tor
# We write a custom torrc at runtime (see entrypoint.sh)

EXPOSE 9150 9151

# CONTROL_PASSWORD: plain-text password; hashed at container start
# SOCKS_HOST:       bind address for SOCKS port (default 0.0.0.0)
# SOCKS_POLICY:     comma-separated IPs/CIDRs allowed to use the proxy
ENV CONTROL_PASSWORD="changeme" \
    SOCKS_HOST="0.0.0.0" \
    CONTROL_HOST="0.0.0.0" \
    SOCKS_POLICY="accept 127.0.0.1,accept 10.0.0.0/8,accept 172.16.0.0/12,accept 192.168.0.0/16"

ENTRYPOINT ["/entrypoint.sh"]
