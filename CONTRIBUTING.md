# Contributing to envdrift

Thanks for helping! The project is small on purpose: zero runtime dependencies, fast, easy to read.

## Setup

```bash
git clone https://github.com/SunoriOff/envdrift
cd envdrift
pip install -e ".[dev]"
pytest
```

## Adding support for a new language

Most contributions are one regex.

1. Open `src/envdrift/scanner.py`.
2. Add a pattern to `CODE_PATTERNS`. Capture the variable name in group 1 (use the `KEY` fragment).
3. If the file extension isn't covered, add it to `CODE_EXTENSIONS`.
4. Add a test in `tests/test_scanner.py`.

## Adding a secret pattern

Add a compiled regex to `SECRET_PATTERNS` in `src/envdrift/analyzer.py` and a test in `tests/test_analyzer.py`. Please prefer patterns with a distinctive prefix to avoid false positives.

## Pull requests

- Keep PRs focused, one change each.
- Add or update tests; CI must pass on Python 3.9 to 3.13.
- Don't add runtime dependencies.

## Reporting false positives / negatives

Open an issue with a minimal code snippet and the output you expected. Those reports are very valuable.
