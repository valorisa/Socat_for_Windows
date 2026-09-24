#!/usr/bin/env python3
"""Corrige MD026, MD032, MD034 (non auto-fixables par --fix).
Usage: python3 <ce_script.py> <fichier.md|dossier> [...]"""
from __future__ import annotations

import re
import sys
from pathlib import Path

FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
HEADING_RE = re.compile(r'^(#{1,6})\s+(.*?)(\s+#+)?\s*$')
LIST_ITEM_RE = re.compile(r'^\s*(?:[-*+]|\d{1,9}[.)])\s+')
CONT_RE = re.compile(r'^ {1,3}\S')
BARE_URL_RE = re.compile(r'(?<![<(\["\'=])https?://[^\s<>`]+')
PUNCT = '.,;:!?'
EXCLUDE = {'.git', 'node_modules'}


def fence_mask(lines: list[str]) -> list[bool]:
    """True pour chaque ligne située dans un bloc de code fence."""
    mask, opener = [], None
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


def fix_md026(line: str) -> str:
    """Ponctuation finale d'un titre : '# Titre.' -> '# Titre'"""
    m = HEADING_RE.match(line)
    if not m:
        return line
    text = m.group(2).rstrip()
    if text and text[-1] in PUNCT:
        cleaned = text.rstrip(PUNCT).rstrip()
        if cleaned:
            return m.group(1) + ' ' + cleaned
    return line


def wrap_url(m: re.Match) -> str:
    """Wrap bare URL with angle brackets."""
    url, trail = m.group(0), ''
    while url and url[-1] in PUNCT:
        trail = url[-1] + trail
        url = url[:-1]
    return '<' + url + '>' + trail


def fix_md034(line: str) -> str:
    """URL nue -> <URL>, sans toucher aux liens [x](url), <url>, ni au code inline."""
    parts = re.split(r'(`[^`]+`)', line)
    for i in range(0, len(parts), 2):
        parts[i] = BARE_URL_RE.sub(wrap_url, parts[i])
    return ''.join(parts)


def _is_empty_line_in_list(lines: list[str], i: int, n: int, mask: list[bool]) -> bool:
    """Vrai si la ligne i est une ligne vide isolée entre une puce et sa continuation."""
    line = lines[i]
    if line.strip() != '' or mask[i]:
        return False
    if not (0 < i and i + 1 < n):
        return False
    if mask[i - 1] or mask[i + 1]:
        return False
    prev_is_list = LIST_ITEM_RE.match(lines[i - 1]) or CONT_RE.match(lines[i - 1])
    next_is_cont = CONT_RE.match(lines[i + 1])
    return bool(prev_is_list and next_is_cont)


def tighten_lists(lines: list[str], mask: list[bool]) -> list[str]:
    """Supprime les lignes vides entre une puce et sa continuation indentée."""
    n = len(lines)
    return [ln for i, ln in enumerate(lines) if not _is_empty_line_in_list(lines, i, n, mask)]


def fix_md032(lines: list[str], mask: list[bool]) -> list[str]:
    """Insère les lignes vides manquantes autour de chaque bloc de liste,
    sans jamais couper une puce de sa continuation indentée."""
    out, i, n = [], 0, len(lines)
    while i < n:
        if mask[i] or not LIST_ITEM_RE.match(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        j = i
        while (j < n and not mask[j] and
               (LIST_ITEM_RE.match(lines[j]) or CONT_RE.match(lines[j]))):
            j += 1
        if out and out[-1].strip():
            out.append('')
        out.extend(lines[i:j])
        if j < n and lines[j].strip():
            out.append('')
        i = j
    return out


def process(path: Path) -> bool:
    """Applique les correctifs à un fichier markdown.

    Lève OSError ou UnicodeDecodeError si le fichier ne peut pas être lu ou
    écrit ; l'appelant décide comment rapporter l'erreur au fichier suivant.
    """
    original_lines = path.read_text(encoding='utf-8').split('\n')
    initial_mask = fence_mask(original_lines)
    lines = tighten_lists(original_lines, initial_mask)
    mask = fence_mask(lines)
    lines = [ln if in_fence else fix_md034(fix_md026(ln))
             for ln, in_fence in zip(lines, mask)]
    final_lines = fix_md032(lines, mask)
    if final_lines != original_lines:
        path.write_text('\n'.join(final_lines), encoding='utf-8')
        return True
    return False


def collect_targets(args: list[str]) -> list[Path]:
    """Résout les arguments (fichiers ou dossiers) en liste de fichiers .md."""
    targets: list[Path] = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            targets += sorted(q for q in p.rglob('*.md')
                               if not any(x in EXCLUDE for x in q.parts))
        elif p.is_file():
            targets.append(p)
        else:
            print(f'[introuvable] {p}', file=sys.stderr)
    return targets


def main() -> int:
    """Point d'entrée principal. Retourne un code de sortie non nul en cas d'erreur."""
    targets = collect_targets(sys.argv[1:])
    fixed = errors = 0
    for t in targets:
        try:
            changed = process(t)
        except (OSError, UnicodeDecodeError) as exc:
            print(f'[erreur] {t}: {exc}', file=sys.stderr)
            errors += 1
            continue
        status = 'corrigé' if changed else 'inchangé'
        if changed:
            fixed += 1
        print(f'[{status}] {t}')
    print(f'\n{fixed} fichier(s) modifié(s) sur {len(targets)} analysé(s).')
    if errors:
        print(f'{errors} fichier(s) en erreur.', file=sys.stderr)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
