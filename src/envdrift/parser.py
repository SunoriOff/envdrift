"""Minimal, dependency-free parser for dotenv-style files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_env_text(text: str) -> Dict[str, str]:
    """Parse the content of a dotenv file into a dict.

    Supports comments, ``export`` prefixes, single/double quotes and inline
    comments on unquoted values. Later definitions override earlier ones.
    """
    values: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not KEY_RE.match(key):
            continue
        if len(value) >= 2 and value[0] in "\"'" and value.endswith(value[0]):
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        values[key] = value
    return values


def parse_env_file(path: Path) -> Dict[str, str]:
    return parse_env_text(Path(path).read_text(encoding="utf-8", errors="replace"))
