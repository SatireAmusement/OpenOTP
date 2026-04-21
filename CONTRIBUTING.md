# Contributing

## Scope

OpenOTP is currently an MVP. Contributions that improve correctness, security posture, tests, documentation, and operational clarity are the best fit.

## Local Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp examples/env/.env.example .env
```

Container-first setup:

```bash
cp examples/env/.env.example .env
docker compose -f deploy/compose/docker-compose.yml up --build
```

## Before Opening a PR

- keep changes focused
- add or update tests when behavior changes
- update docs when configuration, API behavior, or architecture changes
- avoid committing secrets, `.env`, or local databases
- use the pull request template and include verification notes

## Good First Areas

- Postgres support and migrations
- stronger phone number parsing
- Redis-backed rate limiting
- provider error handling improvements
- expanded test coverage
