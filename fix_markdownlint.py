#!/usr/bin/env python3
"""
refactored_fix_markdownlint.py
Refactor minimal: pure transforms, argparse, logging, typing.
Adds --check to exit non-zero if changes would be made.
"""
from __future__ import annotations
import re
import logging
import argparse
from pathlib import Path
from typing import List, Sequence

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)(\s+#+)?\s*$")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])\s+")
CONT_RE = re.compile(r"^ {1,3}\S")
BARE_URL_RE = re.compile(r'(?<![<(\["\'=])https?://[^\s<>`]+')
PUNCT = ".,;:!?"

logger = logging.getLogger(__name__)


def fence_mask(lines: Sequence[str]) -> List[bool]:
    """Return True for lines inside fenced code blocks (``` or ~~~)."""
    mask: List[bool] = []
    opener: str | None = None
    for ln in lines:
        m = FENCE_RE.match(ln)
        if opener is None:
            if m:
                opener = m.group(1)[0]
                mask.append(True)
            else:
                mask.append(False)
        else:
            mask.append(True)
            if m and m.group(1)[0] == opener:
                opener = None
    return mask


def fix_md026_line(line: str) -> str:
    """Remove trailing punctuation from Markdown headings (MD026)."""
    m = HEADING_RE.match(line)
    if not m:
        return line
    text = m.group(2).rstrip()
    if text and text[-1] in PUNCT:
        cleaned = text.rstrip(PUNCT).rstrip()
        if cleaned:
            return f"{m.group(1)} {cleaned}"
    return line


def _wrap_url_match(m: re.Match[str]) -> str:
    """Helper to wrap bare URL, preserving trailing punctuation."""
    url = m.group(0)
    trail = ""
    while url and url[-1] in PUNCT:
        trail = url[-1] + trail
        url = url[:-1]
    return f"<{url}>{trail}"


def fix_md034_line(line: str) -> str:
    """Wrap bare URLs in angle brackets, skipping inline code."""
    parts = re.split(r"(`[^`]+`)", line)
    for i in range(0, len(parts), 2):
        parts[i] = BARE_URL_RE.sub(_wrap_url_match, parts[i])
    return "".join(parts)


def _is_empty_line_in_list(
    lines: Sequence[str], i: int, n: int, mask: Sequence[bool]
) -> bool:
    """Return True if line i is an empty line inside a list continuation."""
    line = lines[i]
    if line.strip() != "" or mask[i]:
        return False
    if not (0 < i and i + 1 < n):
        return False
    if mask[i - 1] or mask[i + 1]:
        return False
    prev_is_list = bool(LIST_ITEM_RE.match(lines[i - 1]) or CONT_RE.match(lines[i - 1]))
    next_is_cont = bool(CONT_RE.match(lines[i + 1]))
    return prev_is_list and next_is_cont


def tighten_lists(lines: Sequence[str], mask: Sequence[bool]) -> List[str]:
    """Remove empty lines between a list item and its indented continuation."""
    out: List[str] = []
    n = len(lines)
    for i, ln in enumerate(lines):
        if _is_empty_line_in_list(lines, i, n, mask):
            continue
        out.append(ln)
    return out


def fix_md032_lines(lines: Sequence[str], mask: Sequence[bool]) -> List[str]:
    """
    Ensure blank lines around list blocks without breaking item continuations (MD032).
    """
    out: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if mask[i] or not LIST_ITEM_RE.match(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        j = i
        while (
            j < n
            and not mask[j]
            and (LIST_ITEM_RE.match(lines[j]) or CONT_RE.match(lines[j]))
        ):
            j += 1
        if out and out[-1].strip():
            out.append("")
        out.extend(lines[i:j])
        if j < n and lines[j].strip():
            out.append("")
        i = j
    return out


def apply_fixes(lines: Sequence[str]) -> List[str]:
    """Apply all fixes to a list of lines and return the modified list."""
    mask0 = fence_mask(lines)
    lines2 = tighten_lists(lines, mask0)
    mask = fence_mask(lines2)
    result: List[str] = []
    for ln, m in zip(lines2, mask):
        if m:
            result.append(ln)
        else:
            ln2 = fix_md026_line(ln)
            ln2 = fix_md034_line(ln2)
            result.append(ln2)
    result = fix_md032_lines(result, mask)
    return result


def process_file(path: Path, inplace: bool = True, dry_run: bool = False) -> bool:
    """Process a markdown file. Return True if file would be/was changed."""
    text = path.read_text(encoding="utf-8")
    ends_nl = text.endswith("\n")
    lines = text.splitlines()
    new_lines = apply_fixes(lines)

    if new_lines == lines:
        logger.debug("Unchanged %s", path)
        return False

    if dry_run:
        logger.info("Would modify %s", path)
        return True

    if inplace:
        content = "\n".join(new_lines) + ("\n" if ends_nl else "")
        path.write_text(content, encoding="utf-8")
        logger.info("Modified %s", path)

    return True


def collect_targets(
    paths: Sequence[str],
    exclude: Sequence[str] = (".git", "node_modules"),
) -> List[Path]:
    """Collect files and directories to process, excluding some folders."""
    targets: List[Path] = []
    for a in paths:
        p = Path(a)
        if p.is_dir():
            for q in sorted(p.rglob("*.md")):
                if not any(x in q.parts for x in exclude):
                    targets.append(q)
        elif p.is_file():
            targets.append(p)
    return targets


def create_arg_parser() -> argparse.ArgumentParser:
    """Create and return an ArgumentParser (testable)."""
    p = argparse.ArgumentParser(description="Fix some markdownlint rules")
    p.add_argument(
        "paths",
        nargs="+",
        help="files or directories",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="perform a dry run (no writes)",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any file would be changed (CI-friendly)",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="verbose logging",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    """Command line entry point."""
    parser = create_arg_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s"
    )
    targets = collect_targets(args.paths)
    if not targets:
        logger.info("No files found")
        return 2
    modified = 0
    for t in targets:
        changed = process_file(
            t, inplace=(not args.dry_run and not args.check), dry_run=args.dry_run
        )
        if changed:
            modified += 1
        status = (
            "would change"
            if args.check and changed
            else ("changed" if changed else "unchanged")
        )
        logger.info("[%s] %s", status, t)
    if args.check:
        return 1 if modified > 0 else 0
    logger.info("%d file(s) modified on %d scanned.", modified, len(targets))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
