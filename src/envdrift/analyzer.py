"""Compare env files with code usage and produce findings."""

from __future__ import annotations

import math
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .parser import parse_env_file
from .scanner import Location, scan_directory

EXAMPLE_NAMES = (
    ".env.example", ".env.sample", ".env.template", ".env.dist", "example.env",
)
LOCAL_NAME = ".env"

ERROR = "error"
WARNING = "warning"

# Well-known secret prefixes / shapes.
SECRET_PATTERNS = [
    re.compile(r"^AKIA[0-9A-Z]{16}$"),                 # AWS access key id
    re.compile(r"^gh[pousr]_[A-Za-z0-9]{36,}$"),       # GitHub tokens
    re.compile(r"^sk_(live|test)_[A-Za-z0-9]{16,}$"),  # Stripe
    re.compile(r"^sk-[A-Za-z0-9_\-]{20,}$"),           # OpenAI-style keys
    re.compile(r"^xox[abprs]-[A-Za-z0-9\-]{10,}$"),    # Slack
    re.compile(r"^AIza[0-9A-Za-z_\-]{35}$"),           # Google API key
    re.compile(r"^eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+$"),  # JWT
    re.compile(r"^-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


@dataclass
class Finding:
    code: str
    severity: str
    variable: Optional[str]
    message: str
    locations: List[Location] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "variable": self.variable,
            "message": self.message,
            "locations": [
                {"file": loc.file, "line": loc.line} for loc in self.locations
            ],
        }


@dataclass
class Report:
    root: Path
    example_file: Optional[str]
    env_file: Optional[str]
    findings: List[Finding]
    used_count: int

    @property
    def errors(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == ERROR]

    @property
    def warnings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == WARNING]

    def to_dict(self) -> dict:
        return {
            "root": str(self.root),
            "example_file": self.example_file,
            "env_file": self.env_file,
            "variables_used_in_code": self.used_count,
            "summary": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
            },
            "findings": [f.to_dict() for f in self.findings],
        }


def find_example_file(root: Path, explicit: Optional[str] = None) -> Optional[Path]:
    if explicit:
        path = (root / explicit) if not Path(explicit).is_absolute() else Path(explicit)
        return path if path.is_file() else None
    for name in EXAMPLE_NAMES:
        path = root / name
        if path.is_file():
            return path
    return None


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts: Dict[str, int] = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    total = len(value)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


PLACEHOLDER_HINTS = (
    "changeme", "change_me", "your", "example", "placeholder", "xxx", "todo",
    "<", "replace", "secret_here", "dummy", "test", "localhost", "foo", "bar",
)


def looks_like_secret(value: str) -> bool:
    """Heuristic: does this value look like a real credential?"""
    if not value or len(value) < 16:
        return False
    lowered = value.lower()
    if any(hint in lowered for hint in PLACEHOLDER_HINTS):
        # A placeholder-ish value can still be a real key with a known shape.
        return any(p.match(value) for p in SECRET_PATTERNS)
    if any(p.match(value) for p in SECRET_PATTERNS):
        return True
    if value.startswith(("http://", "https://", "/")) or " " in value:
        return False
    return len(value) >= 24 and shannon_entropy(value) >= 4.0


def _git(root: Path, *args: str) -> Optional[subprocess.CompletedProcess]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _in_git_repo(root: Path) -> bool:
    result = _git(root, "rev-parse", "--is-inside-work-tree")
    return bool(result and result.returncode == 0 and result.stdout.strip() == "true")


def analyze(
    root: Path,
    example: Optional[str] = None,
    env: Optional[str] = None,
    ignore: Iterable[str] = (),
    use_git: bool = True,
) -> Report:
    root = Path(root).resolve()
    ignored = set(ignore)
    used = scan_directory(root, ignore=ignored)

    example_path = find_example_file(root, example)
    env_path = root / (env or LOCAL_NAME)
    if not env_path.is_file():
        env_path = None  # type: ignore[assignment]

    findings: List[Finding] = []

    documented: Dict[str, str] = {}
    if example_path:
        documented = {
            k: v for k, v in parse_env_file(example_path).items() if k not in ignored
        }
    else:
        findings.append(Finding(
            "no-example", WARNING, None,
            "No .env.example found. Create one so new contributors know "
            "which variables they need (run `envdrift fix`).",
        ))

    local: Dict[str, str] = {}
    if env_path:
        local = {k: v for k, v in parse_env_file(env_path).items() if k not in ignored}

    if example_path:
        for var in sorted(set(used) - set(documented)):
            findings.append(Finding(
                "undocumented", ERROR, var,
                f"{var} is used in code but missing from {example_path.name}",
                used[var],
            ))
        for var in sorted(set(documented) - set(used)):
            findings.append(Finding(
                "stale", WARNING, var,
                f"{var} is in {example_path.name} but never used in code",
            ))
        for var, value in sorted(documented.items()):
            if looks_like_secret(value):
                findings.append(Finding(
                    "secret-in-example", ERROR, var,
                    f"{var} in {example_path.name} looks like a real secret; "
                    "use a placeholder instead",
                ))

    if env_path and example_path:
        for var in sorted(set(documented) - set(local)):
            findings.append(Finding(
                "missing-local", WARNING, var,
                f"{var} is documented in {example_path.name} but not set in {env_path.name}",
            ))
        for var in sorted(set(local) - set(documented)):
            findings.append(Finding(
                "extra-local", WARNING, var,
                f"{var} is set in {env_path.name} but not documented in {example_path.name}",
            ))

    if use_git and _in_git_repo(root):
        tracked = _git(root, "ls-files", "--error-unmatch", LOCAL_NAME)
        if tracked and tracked.returncode == 0:
            findings.append(Finding(
                "env-tracked", ERROR, None,
                ".env is tracked by git. Remove it with "
                "`git rm --cached .env` and rotate any exposed secrets.",
            ))
        elif env_path:
            ignored_by_git = _git(root, "check-ignore", "-q", LOCAL_NAME)
            if ignored_by_git is not None and ignored_by_git.returncode == 1:
                findings.append(Finding(
                    "env-not-ignored", WARNING, None,
                    ".env exists but is not in .gitignore; add it before you commit.",
                ))

    return Report(
        root=root,
        example_file=example_path.name if example_path else None,
        env_file=env_path.name if env_path else None,
        findings=findings,
        used_count=len(used),
    )


def fix_example(root: Path, report: Report, used: Optional[Dict[str, List[Location]]] = None) -> List[str]:
    """Append undocumented variables to the example file. Returns added names."""
    root = Path(root).resolve()
    added = [f for f in report.findings if f.code == "undocumented" and f.variable]
    target = root / (report.example_file or ".env.example")
    if not added:
        return []
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    lines = [] if existing.endswith("\n") or not existing else [""]
    if existing and not existing.endswith("\n\n"):
        lines.append("")
    lines.append("# Added by envdrift - please document these variables")
    for f in added:
        first = f.locations[0] if f.locations else None
        if first:
            lines.append(f"# used in {first.file}:{first.line}")
        lines.append(f"{f.variable}=")
    target.write_text(existing + "\n".join(lines) + "\n", encoding="utf-8")
    return [f.variable for f in added if f.variable]
