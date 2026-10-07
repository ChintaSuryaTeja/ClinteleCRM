#!/bin/sh
# For testing production on your own computer: makes a self-signed HTTPS
# certificate for $DOMAIN (default localhost) in the letsencrypt volume, where
# Nginx expects the real one. Browsers will warn that it isn't trusted; that's
# expected. On the real server use init-letsencrypt.sh instead.
#
#   cd deploy && sh scripts/local-certificate.sh
set -eu

DOMAIN="${DOMAIN:-localhost}"
docker run --rm -v clientele_letsencrypt:/etc/letsencrypt alpine:3.22 sh -c "
  apk add --no-cache openssl >/dev/null &&
  mkdir -p /etc/letsencrypt/live/$DOMAIN &&
  openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
    -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
    -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
    -subj '/CN=$DOMAIN' -addext 'subjectAltName=DNS:$DOMAIN' 2>/dev/null
"
echo "Self-signed certificate for $DOMAIN created."
