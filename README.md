# envdrift

[![CI](https://github.com/SunoriOff/envdrift/actions/workflows/ci.yml/badge.svg)](https://github.com/SunoriOff/envdrift/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/envdrift.svg)](https://pypi.org/project/envdrift/)
[![Python](https://img.shields.io/pypi/pyversions/envdrift.svg)](https://pypi.org/project/envdrift/)
[![License: WTFPL](https://img.shields.io/badge/license-WTFPL-brightgreen.svg)](LICENSE)
![Dependencies: 0](https://img.shields.io/badge/dependencies-0-brightgreen)

**Stop shipping broken `.env.example` files.**

`envdrift` compares three things that always fall out of sync: your `.env`, your `.env.example`, and the environment variables your code *actually* reads. It runs in milliseconds, has zero dependencies, and works with Python, JavaScript/TypeScript, Go, Ruby, PHP, Rust, Java/Kotlin and docker-compose.

```text
$ envdrift check

envdrift 0.1.0  /home/me/my-app
example: .env.example   env: .env   variables used in code: 6

✖ error   PORT is used in code but missing from .env.example
            at server.js:1
✖ error   REDIS_URL is used in code but missing from .env.example
            at server.js:2
✖ error   STRIPE_API_KEY is used in code but missing from .env.example
            at app.py:5
⚠ warning SENTRY_DSN is in .env.example but never used in code
✖ error   SECRET_KEY in .env.example looks like a real secret; use a placeholder instead

4 error(s), 1 warning(s)
Tip: run `envdrift fix` to add undocumented variables to your example file.
```

## Why?

Every new teammate hits the same wall: `git clone`, `cp .env.example .env`, run the app, and it crashes because someone added `REDIS_URL` six months ago and never documented it. Or worse, a real API key was pasted into `.env.example` and pushed to a public repo.

`envdrift` catches both, locally and in CI.

## Install

```bash
pip install envdrift
# or, without installing:
pipx run envdrift
```

Requires Python 3.9+. No runtime dependencies.

## Usage

```bash
envdrift                      # check the current directory
envdrift check path/to/app    # check another directory
envdrift fix                  # append undocumented variables to .env.example
envdrift --format json        # machine-readable output
envdrift --strict             # exit 1 on warnings too (great for CI)
envdrift --ignore LOG_LEVEL --ignore TZ
envdrift --example .env.sample --env .env.local
```

Exit codes: `0` clean, `1` problems found, `2` bad usage.

## What it detects

| Check | Severity | Meaning |
|---|---|---|
| `undocumented` | error | Used in code, missing from `.env.example` |
| `secret-in-example` | error | A value in `.env.example` looks like a real credential (AWS, GitHub, Stripe, OpenAI-style keys, Slack, Google, JWT, private keys, high-entropy strings) |
| `env-tracked` | error | `.env` is committed to git |
| `stale` | warning | Documented in `.env.example` but never used in code |
| `missing-local` | warning | In `.env.example` but not set in your `.env` |
| `extra-local` | warning | Set in `.env` but not documented |
| `env-not-ignored` | warning | `.env` exists but isn't in `.gitignore` |
| `no-example` | warning | No `.env.example` / `.env.sample` / `.env.template` found |

### Supported code patterns

| Language | Patterns |
|---|---|
| Python | `os.environ["X"]`, `os.environ.get("X")`, `os.getenv("X")` |
| JS / TS | `process.env.X`, `process.env["X"]`, `import.meta.env.X`, `Deno.env.get("X")` |
| Go | `os.Getenv("X")`, `os.LookupEnv("X")` |
| Ruby | `ENV["X"]`, `ENV.fetch("X")` |
| PHP / Laravel | `getenv('X')`, `$_ENV['X']`, `env('X')` |
| Rust | `env::var("X")` |
| Java / Kotlin | `System.getenv("X")` |
| docker-compose | `${X}`, `${X:-default}` |

Only `UPPER_SNAKE_CASE` names are considered. `node_modules`, `.venv`, `dist`, `build` and other vendor directories are skipped, as are OS variables like `PATH` and `HOME`.

## Use it in CI

### GitHub Actions

```yaml
name: env-check
on: [push, pull_request]
jobs:
  envdrift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install envdrift
      - run: envdrift check --strict
```

### pre-commit

```yaml
repos:
  - repo: https://github.com/SunoriOff/envdrift
    rev: v0.1.0
    hooks:
      - id: envdrift
```

## Development

```bash
git clone https://github.com/SunoriOff/envdrift
cd envdrift
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add support for a new language, it's usually a one-line regex.

## Roadmap

- [ ] `.env.schema` file with types and required/optional flags
- [ ] Config file (`pyproject.toml` / `.envdrift.toml`)
- [ ] SARIF output for GitHub code scanning
- [ ] More languages (Elixir, Swift, Dart, C#)
- [ ] Monorepo mode (one example file per package)

## License

[WTFPL](LICENSE): do what the fuck you want to.
