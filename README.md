# OpenOTP

OpenOTP is a self-hosted SMS OTP backend for teams that want to own OTP generation, storage, expiry, verification, rate limiting, audit logs, and SMS provider choice.

It treats Twilio or any other SMS vendor as a delivery pipe, not as the owner of your verification state.

## Why Use It

- Application-owned OTP lifecycle.
- OTPs are stored only as salted, peppered PBKDF2-HMAC-SHA256 hashes.
- Expiry, resend cooldowns, max attempts, and rate limits are enforced by the service.
- Redis-backed rate limiting for container deployments, with a database fallback.
- Twilio SMS delivery with provider abstraction and failover support.
- Delivery status webhooks with provider signature validation.
- Audit logs, cleanup jobs, health checks, readiness checks, and Prometheus metrics.
- Docker Compose paths for local development and single-host production.

## Status

OpenOTP is a production-minded MVP and reference implementation. It is suitable for demos, internal tools, architecture review, and as a starting point for a real service.

Before high-volume or high-risk production use, add your organization’s abuse controls, alerting, backup policy, and deployment review process.

## Quick Start

Run the full local stack:

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://127.0.0.1:8000/docs
```

The default local stack uses:

- API on `127.0.0.1:8000`
- Postgres on `127.0.0.1:5432`
- Redis on `127.0.0.1:6379`
- console SMS provider for local development

Stop it:

```bash
docker compose down
```

## Production Deploy

Generate a production environment file:

```bash
./scripts/init-env.sh
```

Review `.env.production`, especially:

```env
OPENOTP_DOMAIN=otp.example.com
OTP_PUBLIC_BASE_URL=https://otp.example.com
OTP_ALLOWED_COUNTRIES=US,CA
OTP_TWILIO_ACCOUNT_SID=...
OTP_TWILIO_AUTH_TOKEN=...
OTP_TWILIO_FROM_NUMBER=+15557654321
```

Start the production stack:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

The production stack includes Caddy for HTTPS, API, Postgres, and Redis. See [docs/deploy.md](docs/deploy.md) for backups, health checks, upgrades, and metrics.

## API

If `OTP_API_KEY` is set, include it on OTP API requests:

```text
X-OpenOTP-API-Key: <your-api-key>
```

### Send OTP

```bash
curl -X POST http://127.0.0.1:8000/v1/otp/send \
  -H "Content-Type: application/json" \
  -H "X-OpenOTP-API-Key: $OTP_API_KEY" \
  -d '{"phone_number":"+14155552671","purpose":"login"}'
```

Response:

```json
{
  "success": true,
  "message": "OTP sent successfully.",
  "challenge_id": "uuid",
  "expires_at": "2026-04-21T20:00:00"
}
```

### Verify OTP

```bash
curl -X POST http://127.0.0.1:8000/v1/otp/verify \
  -H "Content-Type: application/json" \
  -H "X-OpenOTP-API-Key: $OTP_API_KEY" \
  -d '{"phone_number":"+14155552671","purpose":"login","code":"123456"}'
```

Response:

```json
{
  "success": true,
  "message": "OTP verified successfully.",
  "challenge_id": "uuid",
  "expires_at": null
}
```

Invalid, missing, expired, blocked, and already-used OTP challenges all return a uniform verification failure.

## Configuration

All application settings use the `OTP_` prefix.

Important settings:

| Variable | Purpose |
| --- | --- |
| `OTP_APP_ENV` | Use `production` to enable production startup checks. |
| `OTP_API_KEY` | Optional in development, required in production. |
| `OTP_OTP_PEPPER` | Secret pepper used when hashing OTPs. Required to be changed in production. |
| `OTP_SMS_PROVIDER` | `console` for local development, `twilio` for real SMS. |
| `OTP_PUBLIC_BASE_URL` | Public HTTPS base URL used for SMS status callbacks. |
| `OTP_REDIS_URL` | Enables Redis-backed rate limiting when configured. |
| `OTP_RATE_LIMIT_BACKEND` | `redis` or `database`. |
| `OTP_ALLOWED_COUNTRIES` | Optional comma-separated ISO country allow-list, such as `US,CA,GB`. |
| `OTP_TRUSTED_PROXY_IPS` | Comma-separated trusted proxy IPs or CIDRs for forwarded headers. |
| `OTP_METRICS_BEARER_TOKEN` | Protects `/metrics` with bearer auth when set. |

Production startup rejects unsafe defaults, including the default OTP pepper, console SMS provider, missing API key, non-HTTPS public URL, and unauthenticated metrics when metrics are enabled.

## Security Model

OpenOTP follows these core rules:

- Generate OTPs with Python `secrets`.
- Never store OTPs in plaintext.
- Hash OTPs with per-code salt and application pepper.
- Compare OTP hashes with constant-time comparison.
- Enforce expiration, attempt limits, resend limits, and rate limits server-side.
- Do not leak precise OTP challenge state in public verification responses.
- Trust forwarded headers only from configured proxy IPs or CIDRs.
- Keep metrics private or bearer-protected.

SMS OTP is useful, but it is not phishing-resistant. For high-assurance authentication, pair OpenOTP with stronger factors and account-risk controls.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/otp/send` | Create or resend an OTP challenge. |
| `POST` | `/v1/otp/verify` | Verify an OTP code. |
| `POST` | `/v1/webhooks/sms/{provider}/status` | Receive provider delivery status callbacks. |
| `GET` | `/health` | Process liveness. |
| `GET` | `/ready` | Database and Redis readiness. |
| `GET` | `/metrics` | Prometheus metrics. |

## Development

Install locally:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Run tests:

```bash
.venv/bin/pytest -q
```

Run security checks:

```bash
.venv/bin/pip install bandit pip-audit
.venv/bin/bandit -r app -ll
.venv/bin/pip-audit
```

Run with a local Postgres container:

```bash
docker compose up -d postgres redis
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

## Project Layout

```text
app/
  api/            HTTP routes and dependencies
  core/           settings and logging
  db/             SQLAlchemy engine and session setup
  models/         OTP challenge and audit log models
  observability/  metrics and middleware
  schemas/        request and response models
  services/       OTP logic, rate limiting, SMS, cleanup, webhooks
  utils/          phone normalization helpers
alembic/          database migrations
docker/           container entrypoint and Caddy config
docs/             architecture, API, deployment, operations, security
tests/            pytest coverage
```

## Documentation

- [Deployment](docs/deploy.md)
- [API](docs/api.md)
- [Architecture](docs/architecture.md)
- [Security](docs/security.md)
- [Operations](docs/operations.md)
- [Testing](docs/testing.md)

## Contributing

Issues and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md) before contributing.

## License

MIT. See [LICENSE](LICENSE).
