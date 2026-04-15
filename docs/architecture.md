# OpenOTP Architecture

## Goals

- The application owns the full OTP lifecycle.
- The SMS vendor only delivers the already-generated message.
- Policy enforcement is local and auditable.

## Components

- `app/api/routes/otp.py`: HTTP entrypoints for send and verify.
- `app/services/otp_service.py`: OTP lifecycle, hashing, expiry, resend, verification, and audit logic.
- `app/models/otp.py`: persistent challenge and audit log models.
- `app/services/sms/`: SMS provider interface plus `console` and `twilio` implementations.
- `app/db/session.py`: database initialization and session management.

## Flow

1. Client calls `POST /v1/otp/send`.
2. Server normalizes the phone number and checks rate limits based on audit logs.
3. Server creates or reuses a pending challenge, generates a new OTP, hashes it with PBKDF2-HMAC-SHA256 plus salt and pepper, and stores only the hash.
4. Server sends the rendered SMS text through the configured provider.
5. Server records an audit event.
6. Client calls `POST /v1/otp/verify`.
7. Server loads the latest challenge, enforces expiry and max-attempt rules, constant-time compares the submitted code hash, updates status, and records another audit event.

## MVP Persistence

- `otp_challenges` stores the active state of each OTP challenge.
- `audit_logs` stores send and verify events, including blocks and rejections, so rate limiting stays inside the application boundary.
- Alembic manages schema evolution rather than startup table creation.

## Rate Limiting

- OpenOTP now supports a dedicated rate limiter abstraction.
- The database fallback keeps local development and simple deployments working without Redis.
- The containerized stack enables Redis-backed counters for better multi-instance behavior.

## Cleanup And Retention

- A cleanup service marks stale pending challenges as expired.
- Old verified, expired, and blocked challenges are deleted after the configured challenge retention window.
- Old audit logs are deleted after a separate audit-log retention window.
- Cleanup runs as an explicit CLI job so it can be scheduled by cron, systemd timers, or a worker container.

## Provider Failover

- OpenOTP now supports a primary SMS provider plus an ordered fallback chain.
- The OTP challenge stores the provider that actually accepted the send, not just the configured primary.
- Webhook handling resolves providers by concrete provider name so callback validation still works after failover.

## Observability

- OpenOTP exposes a Prometheus-style `/metrics` endpoint.
- HTTP requests are instrumented with counters and latency histograms.
- OTP sends, OTP verifies, SMS webhook outcomes, and cleanup runs emit service-level counters.

## Production Extensions

- Add Redis for distributed counters if traffic warrants it.
- Add background jobs for alerting.
- Add signature-based webhooks if the SMS vendor supports delivery receipts.
