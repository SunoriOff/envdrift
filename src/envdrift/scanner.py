"""Scan source files for environment variable usage (multi-language)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List

KEY = r"[A-Z][A-Z0-9_]*"

# Each pattern captures the variable name in group 1.
CODE_PATTERNS = [
    # Python: os.environ["X"], os.environ.get("X"), environ["X"]
    re.compile(rf"""\benviron(?:\.get)?\s*[\[(]\s*['"]({KEY})['"]"""),
    # Python / PHP: os.getenv("X"), getenv('X')
    re.compile(rf"""\bgetenv\s*\(\s*['"]({KEY})['"]"""),
    # JS / TS: process.env.X, process.env["X"], import.meta.env.X, Deno.env.get("X")
    re.compile(rf"""\bprocess\.env\.({KEY})\b"""),
    re.compile(rf"""\bprocess\.env\[\s*['"]({KEY})['"]\s*\]"""),
    re.compile(rf"""\bimport\.meta\.env\.({KEY})\b"""),
    re.compile(rf"""\bDeno\.env\.get\(\s*['"]({KEY})['"]"""),
    # Go: os.Getenv("X"), os.LookupEnv("X")
    re.compile(rf"""\b(?:Getenv|LookupEnv)\s*\(\s*"({KEY})"\s*\)"""),
    # Ruby: ENV["X"], ENV.fetch("X")
    re.compile(rf"""\bENV\s*(?:\[|\.fetch\()\s*['"]({KEY})['"]"""),
    # PHP superglobals
    re.compile(rf"""\$_(?:ENV|SERVER)\s*\[\s*['"]({KEY})['"]\s*\]"""),
    # Laravel: env('X')
    re.compile(rf"""(?<![\w.])env\s*\(\s*['"]({KEY})['"]"""),
    # Rust: env::var("X")
    re.compile(rf"""\benv::var(?:_os)?\s*\(\s*"({KEY})"\s*\)"""),
    # Java / Kotlin: System.getenv("X")
    re.compile(rf"""\bSystem\.getenv\s*\(\s*"({KEY})"\s*\)"""),
]

# ${VAR} / ${VAR:-default} interpolation, only meaningful in compose files.
COMPOSE_PATTERN = re.compile(rf"""\$\{{({KEY})(?::?[-?+][^}}]*)?\}}""")

CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rb", ".php",
    ".rs", ".java", ".kt", ".kts", ".cs", ".vue", ".svelte", ".astro",
}

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist",
    "build", "target", ".tox", ".mypy_cache", ".pytest_cache", ".next",
    ".nuxt", "vendor", ".idea", ".vscode", "coverage", ".gradle",
}

# Variables set by the OS / shell / CI that are never worth documenting.
BUILTIN_IGNORES = {
    "PATH", "HOME", "USER", "USERNAME", "PWD", "SHELL", "LANG", "TERM",
    "TMPDIR", "TEMP", "TMP", "HOSTNAME", "CI", "PYTHONPATH", "LOGNAME",
    "APPDATA", "LOCALAPPDATA", "USERPROFILE", "XDG_CONFIG_HOME",
    "XDG_DATA_HOME", "XDG_CACHE_HOME", "NO_COLOR", "FORCE_COLOR",
}

MAX_FILE_SIZE = 1_000_000  # bytes


@dataclass(frozen=True)
class Location:
    file: str
    line: int


def _is_compose(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith((".yml", ".yaml")) and (
        name.startswith("docker-compose") or name.startswith("compose")
    )


def iter_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in CODE_EXTENSIONS or _is_compose(path):
            try:
                if path.stat().st_size <= MAX_FILE_SIZE:
                    yield path
            except OSError:
                continue


def scan_text(text: str, compose: bool = False) -> Iterable[tuple]:
    """Yield ``(variable, line_number)`` for every usage found in *text*."""
    patterns = [COMPOSE_PATTERN] if compose else CODE_PATTERNS
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in patterns:
            for match in pattern.finditer(line):
                yield match.group(1), lineno


def scan_directory(
    root: Path, ignore: Iterable[str] = ()
) -> Dict[str, List[Location]]:
    """Return ``{variable: [Location, ...]}`` for the whole tree under *root*."""
    root = Path(root)
    ignored = BUILTIN_IGNORES | set(ignore)
    found: Dict[str, List[Location]] = {}
    for path in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        for var, lineno in scan_text(text, compose=_is_compose(path)):
            if var in ignored:
                continue
            locs = found.setdefault(var, [])
            loc = Location(rel, lineno)
            if loc not in locs:
                locs.append(loc)
    return found
