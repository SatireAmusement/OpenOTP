# Deploy OpenOTP

This guide is the fastest production-oriented path for a single-host OpenOTP deployment.

## Requirements

- A Linux host with Docker and Docker Compose.
- A DNS name pointed at the host.
- TCP ports `80` and `443` open to the internet.
- Twilio credentials and an SMS-capable sender number.

## Generate Configuration

From the repository root:

```bash
./scripts/init-env.sh
```

The script writes `.env.production`, generates secrets, and prints the API key your client applications must use.

Review the generated file before first boot:

```bash
nano .env.production
```

At minimum, confirm:

```env
OPENOTP_DOMAIN=otp.example.com
OTP_PUBLIC_BASE_URL=https://otp.example.com
OTP_ALLOWED_COUNTRIES=US,CA
OTP_TWILIO_ACCOUNT_SID=...
OTP_TWILIO_AUTH_TOKEN=...
OTP_TWILIO_FROM_NUMBER=+15557654321
```

## Start

```bash
docker compose -f deploy/compose/docker-compose.prod.yml --env-file .env.production up -d --build
```

Caddy will request and renew TLS certificates automatically for `OPENOTP_DOMAIN`.

## Check Health

```bash
curl https://otp.example.com/health
curl https://otp.example.com/ready
```

`/health` confirms the API process is alive. `/ready` verifies database connectivity and Redis when Redis rate limiting is enabled.

## Send a Test OTP

```bash
curl -X POST https://otp.example.com/v1/otp/send \
  -H "Content-Type: application/json" \
  -H "X-OpenOTP-API-Key: $OTP_API_KEY" \
  -d '{"phone_number":"+14155552671","purpose":"login"}'
```

## Metrics

If `OTP_METRICS_BEARER_TOKEN` is set:

```bash
curl https://otp.example.com/metrics \
  -H "Authorization: Bearer $OTP_METRICS_BEARER_TOKEN"
```

Keep this endpoint private. It is meant for Prometheus or similar monitoring systems.

## Backups

Back up the Postgres volume regularly. A simple logical backup from the host:

```bash
docker exec openotp-postgres pg_dump -U openotp openotp > openotp-$(date +%F).sql
```

Restore into a stopped or fresh deployment:

```bash
cat openotp-YYYY-MM-DD.sql | docker exec -i openotp-postgres psql -U openotp openotp
```

## Upgrade

```bash
git pull
docker compose -f deploy/compose/docker-compose.prod.yml --env-file .env.production up -d --build
```

The API container runs Alembic migrations on startup.

## Stop

```bash
docker compose -f deploy/compose/docker-compose.prod.yml --env-file .env.production down
```

Do not use `-v` unless you intentionally want to delete the database and Redis volumes.
