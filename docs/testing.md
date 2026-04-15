# Testing

Run:

```bash
.venv/bin/pytest -q
```

What is covered:

- send then verify happy path
- resend cooldown rejection
- invalid-code rejection
- invalid phone-number rejection
- delivery-status webhook update
- cleanup retention behavior
- metrics endpoint exposure

Recommended next tests:

- expiry handling
- verify-attempt exhaustion
- hourly send limit
- resend ceiling exhaustion
- SMS provider failure behavior
- concurrent verification attempts
- Twilio provider integration tests with HTTP mocking

Current note:

- automated tests use SQLite fixtures for speed and isolation, while the default application configuration targets Postgres
