# Changelog

## 0.1.0

Initial public MVP release of OpenOTP.

Highlights:

- application-owned SMS OTP generation, hashing, expiry, verification, resend, and audit logging
- Postgres-first persistence with Alembic migrations
- Redis-backed rate limiting with database fallback
- strict phone validation and E.164 normalization with `phonenumbers`
- Twilio-compatible delivery status webhooks
- retention cleanup CLI
- SMS provider failover chain
- Prometheus-style metrics endpoint
