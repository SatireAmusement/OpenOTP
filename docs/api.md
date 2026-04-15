# API

## `POST /v1/otp/send`

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
- Returns `400` for a wrong code.
- Returns `404` if no challenge exists.
- Returns `410` if the challenge expired.
- Returns `423` if the challenge is blocked or already exhausted.
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

Examples:

- request counters and latency
- OTP send and verify outcome counters
- SMS webhook outcome counters
- cleanup job counters
