# OpenOTP

OpenOTP is a production-minded SMS OTP backend where the application owns OTP generation, hashing, expiry, verification, rate limiting, resend policy, logging, and vendor abstraction. The SMS provider is treated strictly as a delivery channel.

This repository is intentionally positioned as a strong MVP and reference implementation, not a drop-in finished auth platform. The current build is suitable for local development, demos, technical interviews, architecture review, and as a starting point for a real service.

## Status

- public MVP with tests, docs, Docker, migrations, failover, cleanup, and metrics
- good reference implementation for teams that want application-owned OTP behavior
- not a finished auth platform; production rollout still needs abuse controls and deployment rigor

## Why OpenOTP

- Application-owned OTP lifecycle rather than vendor-managed verification state
- OTP codes are generated in-app and stored only as salted, peppered hashes
- Expiry, verify-attempt limits, resend policy, and rate limiting are enforced locally
- SMS delivery is abstracted behind a provider interface
- Audit logs capture accepted, rejected, and blocked events
- The codebase is small enough to understand quickly and structured enough to evolve

## Stack

- FastAPI
- SQLAlchemy
- Postgres as the default deployment target
- Redis-backed rate limiting in the containerized development stack
- SQLite only in tests and quick local experimentation
- Twilio provider example plus a local console provider
- Pytest

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open the API docs at `http://127.0.0.1:8000/docs`.

## Repository Features

- CI workflow for automated test runs on pushes and pull requests
- GitHub issue templates for bugs and feature requests
- Pull request template for consistent review context
- Security policy and contributor-facing repo docs
- Dockerized local development path with automatic migrations
- Prometheus-style metrics endpoint and service instrumentation

## Current Capabilities

- application-owned OTP generation, hashing, expiry, verification, resend policy, and audit logging
- Postgres-first schema management with Alembic
- Redis-backed rate limiting with database fallback
- strict phone normalization with `phonenumbers`
- provider-specific delivery webhooks
- provider failover chain for send attempts
- retention cleanup command for challenges and audit logs
- `/metrics` endpoint for Prometheus-style scraping

## API Surface

- `POST /v1/otp/send`
- `POST /v1/otp/verify`
- `GET /health`
- `GET /metrics`

Example send request:

```json
{
  "phone_number": "+14155552671",
  "purpose": "login"
}
```

## Project Layout

```text
app/
  api/        HTTP routes and dependency wiring
  core/       settings and logging
  db/         engine and session setup
  models/     OTP challenge and audit log models
  schemas/    request and response schemas
  services/   OTP logic and SMS provider implementations
  utils/      small helpers
docs/         architecture, API, security, ops, testing
tests/        automated coverage for the MVP flow
```

## MVP Caveats

OpenOTP is GitHub-ready, but still an MVP. Before using it in a serious production environment, you should address at least these gaps:

- expand the migration workflow with deployment/review discipline and rollback procedures
- move hot rate-limit state to Redis if you need multi-instance scaling
- expand tests for expiry, lockout, resend ceilings, provider errors, and concurrency
- add abuse controls such as CAPTCHA hooks, app scoping, and stronger anti-enumeration behavior

## Running Tests

```bash
.venv/bin/pytest -q
```

Or, with the included helper:

```bash
make test
```

Run cleanup manually with:

```bash
make cleanup
```

## Local Development

The simplest path is fully containerized:

```bash
cp .env.example .env
docker compose up --build
```

The API container waits for Postgres, runs `alembic upgrade head`, and then starts Uvicorn. The compose stack uses [.env.postgres.example](./.env.postgres.example) for the database container and [.env.example](./.env.example) for the application container.
In the containerized path, Redis is enabled as the rate-limit backend through [.env.docker.example](./.env.docker.example).
If you want Twilio delivery callbacks to work, set `OTP_PUBLIC_BASE_URL` to the externally reachable base URL for this service.
Provider failover is configured with `OTP_SMS_PROVIDER` as the primary sender and `OTP_SMS_FAILOVER_PROVIDERS` as a comma-separated fallback chain.

If you prefer running the app directly on your machine:

```bash
docker compose up -d postgres
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

## Docs

Start with [docs/README.md](./docs/README.md).

## Community Files

- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [SECURITY.md](./SECURITY.md)
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- [CHANGELOG.md](./CHANGELOG.md)

## Roadmap

- optional tracing/export integration beyond local metrics

## License

MIT. See [LICENSE](./LICENSE).
