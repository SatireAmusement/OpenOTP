# Operations

## Run Locally

```bash
cp .env.example .env
docker compose up --build
```

Stop the stack with:

```bash
docker compose down
```

Scrape metrics locally at:

```text
http://127.0.0.1:8000/metrics
```

If you want the app on the host but Postgres in Docker:

```bash
docker compose up -d postgres
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

Run cleanup manually:

```bash
make cleanup
```

## Environment Variables

All settings use the `OTP_` prefix.

```env
OTP_DATABASE_URL=postgresql+psycopg://openotp:openotp@localhost:5432/openotp
OTP_PUBLIC_BASE_URL=
OTP_REDIS_URL=
OTP_RATE_LIMIT_BACKEND=database
OTP_RATE_LIMIT_KEY_PREFIX=openotp:ratelimit
OTP_PHONE_DEFAULT_REGION=US
OTP_CHALLENGE_RETENTION_DAYS=30
OTP_AUDIT_LOG_RETENTION_DAYS=90
OTP_SMS_PROVIDER=console
OTP_SMS_FAILOVER_PROVIDERS=
OTP_OTP_PEPPER=replace-me
OTP_OTP_TTL_SECONDS=300
OTP_SEND_MAX_PER_WINDOW=5
OTP_SEND_WINDOW_SECONDS=3600
OTP_VERIFY_MAX_PER_WINDOW=10
OTP_VERIFY_WINDOW_SECONDS=900
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_RESEND_MAX_PER_CHALLENGE=3
```

Twilio:

```env
OTP_SMS_PROVIDER=twilio
OTP_TWILIO_ACCOUNT_SID=...
OTP_TWILIO_AUTH_TOKEN=...
OTP_TWILIO_FROM_NUMBER=+15557654321
```

## Operational Behavior

- The API container waits for Postgres and runs Alembic before starting the server.
- The containerized stack enables Redis-backed rate limiting by default.
- The console provider logs SMS contents for local development only.
- Rate limiting is enforced per phone number and, when available, per IP address.
- Resends reuse the active challenge and rotate the underlying OTP code.
- `docker-compose.yml` provisions the API, Postgres, and Redis so the default container path matches the intended production architecture more closely.
- Delivery receipt webhooks require `OTP_PUBLIC_BASE_URL` to point at a publicly reachable URL for this service.
- Cleanup is an explicit maintenance job that expires stale pending challenges and prunes old challenges and audit logs by retention window.
- SMS failover is configured as a provider chain: primary `OTP_SMS_PROVIDER`, then comma-separated `OTP_SMS_FAILOVER_PROVIDERS`.

## Production Notes

- Do not use the console provider outside local development.
- Rotate the OTP pepper through a proper secrets manager.
- Put the service behind TLS and a trusted reverse proxy.
