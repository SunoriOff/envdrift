"""Command-line interface for envdrift."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .analyzer import ERROR, WARNING, Report, analyze, fix_example


class Style:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def red(self, t: str) -> str: return self._wrap("31", t)
    def yellow(self, t: str) -> str: return self._wrap("33", t)
    def green(self, t: str) -> str: return self._wrap("32", t)
    def dim(self, t: str) -> str: return self._wrap("2", t)
    def bold(self, t: str) -> str: return self._wrap("1", t)


def render_text(report: Report, style: Style) -> str:
    out: List[str] = []
    out.append(style.bold(f"envdrift {__version__}") + style.dim(f"  {report.root}"))
    out.append(style.dim(
        f"example: {report.example_file or '-'}   "
        f"env: {report.env_file or '-'}   "
        f"variables used in code: {report.used_count}"
    ))
    out.append("")
    if not report.findings:
        out.append(style.green("✔ No drift detected. Your env files match your code."))
        return "\n".join(out)

    for finding in report.findings:
        if finding.severity == ERROR:
            tag = style.red("✖ error  ")
        else:
            tag = style.yellow("⚠ warning")
        out.append(f"{tag} {finding.message}")
        for loc in finding.locations[:3]:
            out.append(style.dim(f"            at {loc.file}:{loc.line}"))
        if len(finding.locations) > 3:
            out.append(style.dim(f"            … and {len(finding.locations) - 3} more"))
    out.append("")
    summary = f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)"
    out.append(style.red(summary) if report.errors else style.yellow(summary))
    if any(f.code == "undocumented" for f in report.findings):
        out.append(style.dim("Tip: run `envdrift fix` to add undocumented variables to your example file."))
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envdrift",
        description="Detect drift between your .env, .env.example and the "
                    "environment variables your code actually uses.",
    )
    parser.add_argument("--version", action="version", version=f"envdrift {__version__}")
    sub = parser.add_subparsers(dest="command")

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("path", nargs="?", default=".", help="project directory (default: .)")
        p.add_argument("--example", help="example file name (default: auto-detect .env.example, .env.sample, ...)")
        p.add_argument("--env", help="local env file name (default: .env)")
        p.add_argument("--ignore", action="append", default=[], metavar="VAR",
                       help="variable to ignore (repeatable)")
        p.add_argument("--no-git", action="store_true", help="skip git checks")

    check = sub.add_parser("check", help="analyze a project (default command)")
    common(check)
    check.add_argument("--format", choices=["text", "json"], default="text")
    check.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    check.add_argument("--no-color", action="store_true")

    fix = sub.add_parser("fix", help="append undocumented variables to the example file")
    common(fix)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in {"check", "fix", "-h", "--help", "--version"}:
        argv = ["check", *argv]
    args = build_parser().parse_args(argv)

    root = Path(args.path)
    if not root.is_dir():
        print(f"envdrift: not a directory: {root}", file=sys.stderr)
        return 2

    report = analyze(
        root,
        example=args.example,
        env=args.env,
        ignore=args.ignore,
        use_git=not args.no_git,
    )

    if args.command == "fix":
        added = fix_example(root, report)
        if added:
            print(f"Added {len(added)} variable(s) to {report.example_file or '.env.example'}: "
                  + ", ".join(added))
        else:
            print("Nothing to fix.")
        return 0

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        color = sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ
        print(render_text(report, Style(color)))

    if report.errors:
        return 1
    if args.strict and report.warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
