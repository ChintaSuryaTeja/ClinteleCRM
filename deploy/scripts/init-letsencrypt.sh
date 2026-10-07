#!/bin/sh
# Real server only, once: gets the first free Let's Encrypt certificate.
# (Afterwards the certbot service renews it automatically.)
#
# Needs: DNS for $DOMAIN pointing at this server, ports 80 and 443 open, and
# DOMAIN + LETSENCRYPT_EMAIL set in .env.production.
#
# The chicken-and-egg problem it solves: Nginx won't start without a
# certificate, but Let's Encrypt checks the domain through Nginx. So:
#   1. make a throwaway self-signed certificate,
#   2. start Nginx with it,
#   3. ask Let's Encrypt for the real one (it checks port 80),
#   4. reload Nginx to use the real one.
#
#   cd deploy && sh scripts/init-letsencrypt.sh
set -eu

set -a
# shellcheck source=/dev/null # the settings file only exists on the server
. ./.env.production
set +a
: "${DOMAIN:?Set DOMAIN in .env.production}"
: "${LETSENCRYPT_EMAIL:?Set LETSENCRYPT_EMAIL in .env.production}"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.production"

echo "1. Temporary certificate"
DOMAIN="$DOMAIN" sh scripts/local-certificate.sh

echo "2. Starting the app and Nginx"
$COMPOSE up -d --no-build

echo "3. Requesting the real certificate"
# Remove the temporary one so certbot can write the real one in its place.
$COMPOSE run --rm --entrypoint sh certbot -c "rm -rf /etc/letsencrypt/live/$DOMAIN"
$COMPOSE run --rm --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot \
  -d "$DOMAIN" --email "$LETSENCRYPT_EMAIL" \
  --agree-tos --no-eff-email --non-interactive

echo "4. Reloading Nginx and starting automatic renewal"
$COMPOSE exec nginx nginx -s reload
$COMPOSE --profile letsencrypt up -d certbot
echo "Done: https://$DOMAIN"
