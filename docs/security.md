# Security Notes

## Application-Owned Controls

- OTPs are generated with `secrets.choice`.
- OTPs are never stored in plaintext.
- Hashing uses PBKDF2-HMAC-SHA256 with per-code salt and application pepper.
- Verification uses constant-time comparison.
- Expiry, attempt counting, resend limits, and rate limiting are all enforced by the backend.
- Audit logs preserve event outcomes for investigation and tuning.

## Required Production Hardening

- Replace the default `OTP_OTP_PEPPER`.
- Add schema migrations and operational backup strategy.
- Put the API behind TLS and a trusted proxy.
- Add cleanup for old challenges and logs.
- Emit logs to a centralized sink and redact sensitive fields.
- Consider provider failover if SMS delivery is business-critical.
