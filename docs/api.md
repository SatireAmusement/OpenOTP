# API

## `POST /v1/otp/send`

If `OTP_API_KEY` is configured, include:

```text
X-OpenOTP-API-Key: <key>
```

Request:

```json
{
  "phone_number": "+14155552671",
  "purpose": "login"
}
```

Response:

```json
{
  "success": true,
  "message": "OTP sent successfully.",
  "challenge_id": "uuid",
  "expires_at": "2026-04-15T08:00:00Z"
}
```

Behavior:

- Returns `202` on success.
- Returns `429` if the send rate limit or resend cooldown/policy is violated.

## `POST /v1/otp/verify`

If `OTP_API_KEY` is configured, include:

```text
X-OpenOTP-API-Key: <key>
```

Request:

```json
{
  "phone_number": "+14155552671",
  "purpose": "login",
  "code": "123456"
}
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

Behavior:

- Returns `200` on success.
- Returns `400` for invalid, missing, expired, blocked, or already-used OTP challenges.
- Returns `429` if verify attempts exceed the configured rate window.

## `POST /v1/webhooks/sms/{provider}/status`

Purpose:

- Accepts provider delivery status callbacks.
- Validates the provider signature.
- Updates the matching OTP challenge delivery status by provider message id.

Current implementation:

- Twilio-compatible status callbacks are supported through the configured SMS provider abstraction.

## `GET /metrics`

Purpose:

- Exposes Prometheus-style application metrics.
- If `OTP_METRICS_BEARER_TOKEN` is set, callers must provide `Authorization: Bearer <token>`.

Examples:

- request counters and latency
- OTP send and verify outcome counters
- SMS webhook outcome counters
- cleanup job counters
