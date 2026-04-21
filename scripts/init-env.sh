#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$root_dir/.env.production"

if [[ -f "$env_file" ]]; then
  echo ".env.production already exists. Move it aside before generating a new one." >&2
  exit 1
fi

secret() {
  python3 - "$1" <<'PY'
import secrets
import sys

print(secrets.token_urlsafe(int(sys.argv[1])))
PY
}

read -r -p "Public domain for OpenOTP [otp.example.com]: " domain
domain="${domain:-otp.example.com}"

read -r -p "Allowed phone countries, comma-separated ISO codes [US,CA]: " allowed_countries
allowed_countries="${allowed_countries:-US,CA}"

read -r -p "Twilio Account SID [leave blank to fill later]: " twilio_sid
read -r -s -p "Twilio Auth Token [leave blank to fill later]: " twilio_token
echo
read -r -p "Twilio From Number, E.164 [leave blank to fill later]: " twilio_from

postgres_password="$(secret 36)"
api_key="$(secret 32)"
metrics_token="$(secret 32)"
otp_pepper="$(secret 48)"

cat > "$env_file" <<EOF
OPENOTP_DOMAIN=$domain

POSTGRES_DB=openotp
POSTGRES_USER=openotp
POSTGRES_PASSWORD=$postgres_password

OTP_APP_ENV=production
OTP_DATABASE_URL=postgresql+psycopg://openotp:$postgres_password@postgres:5432/openotp
OTP_LOG_LEVEL=INFO
OTP_PUBLIC_BASE_URL=https://$domain
OTP_API_KEY=$api_key
OTP_REDIS_URL=redis://redis:6379/0
OTP_RATE_LIMIT_BACKEND=redis
OTP_RATE_LIMIT_KEY_PREFIX=openotp:ratelimit
OTP_TRUSTED_PROXY_IPS=172.16.0.0/12
OTP_METRICS_ENABLED=true
OTP_METRICS_BEARER_TOKEN=$metrics_token
OTP_PHONE_DEFAULT_REGION=US
OTP_ALLOWED_COUNTRIES=$allowed_countries
OTP_CHALLENGE_RETENTION_DAYS=30
OTP_AUDIT_LOG_RETENTION_DAYS=90

OTP_OTP_LENGTH=6
OTP_OTP_TTL_SECONDS=300
OTP_OTP_MAX_VERIFY_ATTEMPTS=5
OTP_OTP_HASH_ITERATIONS=120000
OTP_OTP_PEPPER=$otp_pepper

OTP_SEND_MAX_PER_WINDOW=5
OTP_SEND_WINDOW_SECONDS=3600
OTP_VERIFY_MAX_PER_WINDOW=10
OTP_VERIFY_WINDOW_SECONDS=900
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_RESEND_MAX_PER_CHALLENGE=3

OTP_SMS_PROVIDER=twilio
OTP_SMS_FAILOVER_PROVIDERS=
OTP_SMS_SENDER_ID=ExampleApp

OTP_TWILIO_ACCOUNT_SID=$twilio_sid
OTP_TWILIO_AUTH_TOKEN=$twilio_token
OTP_TWILIO_FROM_NUMBER=$twilio_from
EOF

chmod 600 "$env_file"

cat <<EOF
Wrote $env_file

Next steps:
1. Review Twilio settings in .env.production.
2. Point DNS for $domain at this host.
3. Run: docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

Save this API key for clients:
$api_key
EOF
