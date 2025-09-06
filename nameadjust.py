#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple
import argparse
import re
import shutil
import sys

from fontTools.ttLib import TTFont  # type: ignore


def is_ttf(path: Path) -> bool:
    """Return True if path has a .ttf suffix (case-insensitive)."""
    return Path(path).suffix.lower() == ".ttf"


def discover_ttf(inputs: Iterable[Path]) -> list[Path]:
    """Discover .ttf files from provided files and directories.

    - Nonexistent inputs are ignored.
    - Directories are traversed recursively.
    - Returns a sorted, de-duplicated list of resolved paths.
    """
    found: set[Path] = set()
    for raw in inputs:
        p = Path(raw)
        if p.is_file():
            if is_ttf(p):
                found.add(p.resolve())
        elif p.is_dir():
            for child in p.rglob("*"):
                if child.is_file() and is_ttf(child):
                    found.add(child.resolve())
        else:
            continue
    return sorted(found)


_SPLIT_RE = re.compile(r"[_\-]+")
_VERSION_TOKEN_RE = re.compile(r"^(?:v)?\d+(?:[._]\d+)*$")


def _is_camel_like(token: str) -> bool:
    return bool(re.search(r"[a-z][A-Z]", token))


def _is_version_token(token: str) -> bool:
    """Heuristic: token looks like a version (e.g., 0902, 1.0, v1, v1.2.3)."""
    return bool(_VERSION_TOKEN_RE.match(token))


def humanize_stem(stem: str) -> str:
    """Convert a filename stem into a Humanized Title Case string.

    Rules:
    - Split on '_' and '-' and collapse repeats.
    - Drop standalone 'VF' (case-insensitive).
    - Preserve CamelCase tokens; Title Case purely lower/upper tokens.
    - Remove version-like tokens (e.g., 0902, 1.0, v1, v1.2.3).
    - Preserve other alnum tokens (including CamelCase and mixed tokens like H2).
    - Join with single spaces.
    """
    tokens = [t for t in _SPLIT_RE.split(stem) if t]
    out: list[str] = []
    for tok in tokens:
        # Drop trailing 'VF' suffix (e.g., PragmataProMonoVF -> PragmataProMono)
        if tok.lower().endswith("vf") and len(tok) > 2:
            tok = tok[:-2]
        if not tok:
            continue
        if tok.lower() == "vf":
            continue
        # Drop version tokens entirely
        if _is_version_token(tok):
            continue
        if _is_camel_like(tok):
            out.append(tok)
            continue
        # Title Case otherwise
        out.append(tok.lower().title())
    return " ".join(out).strip()


# Recognized style phrases
_BASE_STYLES = [
    "Thin",
    "Extra Light",
    "Light",
    "Regular",
    "Medium",
    "Semi Bold",
    "Bold",
    "Extra Bold",
    "Black",
]
_STYLE_SET = set(_BASE_STYLES)
# Add italic combinations
for base in _BASE_STYLES:
    if base != "Italic":
        _STYLE_SET.add(f"{base} Italic")
_STYLE_SET.add("Italic")


def split_family_subfamily(humanized: str) -> tuple[str, str]:
    """Split a Humanized string into (Family, Subfamily).

    Heuristic: find the rightmost recognized style phrase (length 3, then 2, then 1 tokens);
    treat it as Subfamily and remove it from the token list. The remainder becomes Family.
    If no style phrase is found, Subfamily = 'Regular' and Family = the entire Humanized string.
    """
    toks = [t for t in humanized.split(" ") if t]
    if not toks:
        return "", "Regular"

    found: tuple[int, int] | None = None  # (start, end) inclusive
    n = len(toks)
    # search right-to-left, prefer longer phrases
    for i in range(n - 1, -1, -1):
        for size in (3, 2, 1):
            start = i - size + 1
            if start < 0:
                continue
            phrase = " ".join(toks[start : i + 1])
            if phrase in _STYLE_SET:
                found = (start, i)
                break
        if found:
            break

    if found is None:
        return humanized, "Regular"

    s, e = found
    subfamily = " ".join(toks[s : e + 1])
    family_tokens = toks[:s] + toks[e + 1 :]
    family = " ".join(family_tokens).strip() or humanized
    return family, subfamily


_PS_ALLOWED = re.compile(r"[^A-Za-z0-9-]")


def ps_name(family: str, subfamily: str) -> str:
    """Compose a PostScript name: <Family>-<Subfamily> with spaces removed and filtered chars."""
    fam = family.replace(" ", "")
    sub = subfamily.replace(" ", "")
    fam = _PS_ALLOWED.sub("", fam)
    sub = _PS_ALLOWED.sub("", sub)
    return f"{fam}-{sub}" if sub else fam


def make_clean_stem(family: str, subfamily: str) -> str:
    """Return cleaned filename stem: <Family>-<Subfamily> with spaces → underscores.

    Always retains the hyphen between Family and Subfamily; if Subfamily is empty,
    returns just the Family part.
    """
    fam = family.replace(" ", "_")
    sub = subfamily.replace(" ", "_")
    return f"{fam}-{sub}" if sub else fam


def _infer_weight_and_italic_from_subfamily(subfamily: str) -> tuple[int, bool]:
    """Infer usWeightClass (100-900) and italic flag from subfamily phrase.

    - Strictly treat 'Bold' for bold; do not infer bold from 'Medium' etc.
    - Italic true when 'Italic' appears in the phrase.
    """
    is_italic = "italic" in subfamily.lower()
    # Weight map aligned with collection tool
    weight_map = {
        "thin": 100,
        "hairline": 100,
        "extra light": 200,
        "extralight": 200,
        "ultra light": 200,
        "ultralight": 200,
        "light": 300,
        "regular": 400,
        "book": 400,
        "roman": 400,
        "medium": 500,
        "semi bold": 600,
        "semibold": 600,
        "demi bold": 600,
        "demibold": 600,
        "bold": 700,
        "extra bold": 800,
        "extrabold": 800,
        "ultra bold": 800,
        "ultrabold": 800,
        "black": 900,
        "heavy": 900,
    }
    s = " ".join(subfamily.lower().split())
    for k in sorted(weight_map.keys(), key=len, reverse=True):
        if k in s:
            return weight_map[k], is_italic
    return 400, is_italic


def rewrite_name_table(ttf_in: Path, *, out_path: Path | None, family: str, subfamily: str) -> Path:
    """Rewrite name table IDs 16/17/1/2/4/6 for Windows and Mac; update style flags.

    Returns the written path (in place when out_path is None).
    """
    font = TTFont(ttf_in)
    try:
        name_tbl = font["name"]
        full = f"{family} {subfamily}".strip()
        ps = ps_name(family, subfamily)
        weight, italic = _infer_weight_and_italic_from_subfamily(subfamily or "Regular")

        # Windows (3,1,0x409)
        name_tbl.setName(family, 16, 3, 1, 0x409)
        name_tbl.setName(subfamily, 17, 3, 1, 0x409)
        name_tbl.setName(family, 1, 3, 1, 0x409)
        name_tbl.setName(subfamily, 2, 3, 1, 0x409)
        name_tbl.setName(full, 4, 3, 1, 0x409)
        name_tbl.setName(ps, 6, 3, 1, 0x409)

        # Mac (1,0,0)
        name_tbl.setName(family, 16, 1, 0, 0)
        name_tbl.setName(subfamily, 17, 1, 0, 0)
        name_tbl.setName(family, 1, 1, 0, 0)
        name_tbl.setName(subfamily, 2, 1, 0, 0)
        name_tbl.setName(full, 4, 1, 0, 0)
        name_tbl.setName(ps, 6, 1, 0, 0)

        # Update OS/2 and head flags when available
        try:
            os2 = font["OS/2"]
            os2.usWeightClass = int(weight)
            # fsSelection bits: 0=ITALIC, 5=BOLD, 6=REGULAR
            fs = getattr(os2, "fsSelection", 0)
            def _set_bit(val: int, bit: int, on: bool) -> int:
                return (val | (1 << bit)) if on else (val & ~(1 << bit))

            is_bold_style = " bold" in (" " + subfamily.lower()) and "extra bold" not in subfamily.lower()
            is_regular_upright = (subfamily.lower() == "regular") and not italic
            fs = _set_bit(fs, 0, italic)
            fs = _set_bit(fs, 5, is_bold_style)
            fs = _set_bit(fs, 6, is_regular_upright)
            os2.fsSelection = fs
        except Exception:
            pass

        try:
            head = font["head"]
            mac = getattr(head, "macStyle", 0)
            # macStyle bits: 0=Bold, 1=Italic
            def _set_bit(val: int, bit: int, on: bool) -> int:
                return (val | (1 << bit)) if on else (val & ~(1 << bit))

            is_bold_style = " bold" in (" " + subfamily.lower()) and "extra bold" not in subfamily.lower()
            mac = _set_bit(mac, 0, is_bold_style)
            mac = _set_bit(mac, 1, italic)
            head.macStyle = mac
        except Exception:
            pass

        target = Path(out_path) if out_path is not None else Path(ttf_in)
        font.save(target)
        return target
    finally:
        try:
            font.close()
        except Exception:
            pass


def process_font(path: Path, out_dir: Path | None) -> Path:
    """Process one .ttf: compute names from filename and rewrite the name table.

    Returns the written path (either in place or the copied path under out_dir).
    """
    path = Path(path)
    human = humanize_stem(path.stem)
    family, subfamily = split_family_subfamily(human)

    # Determine cleaned filename
    clean_stem = make_clean_stem(family, subfamily)
    suffix = path.suffix

    if out_dir is None:
        # In-place, but rename to cleaned filename if needed
        target = path
        new_path = path.with_name(f"{clean_stem}{suffix}")
        if new_path != path:
            # Rename first so rewrite writes to the final location
            path = path.rename(new_path)
            target = new_path
        return rewrite_name_table(target, out_path=target, family=family, subfamily=subfamily)
    else:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{clean_stem}{suffix}"
        return rewrite_name_table(path, out_path=out_path, family=family, subfamily=subfamily)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nameadjust",
        description="Update internal font names from a humanized filename.",
    )
    p.add_argument("paths", nargs="+", help="Font files or directories to search for .ttf files")
    p.add_argument("-o", "--output", type=Path, default=None, help="Output directory (default: in-place update)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    inputs = [Path(p) for p in args.paths]
    fonts = discover_ttf(inputs)
    if not fonts:
        print("No .ttf files found under provided paths.", file=sys.stderr)
        return 1

    failures = 0
    for f in fonts:
        try:
            out = process_font(f, args.output)
            print(f"OK  {f.name} -> {out}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"FAIL {f.name}: {e}", file=sys.stderr)

    return 0 if failures == 0 else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
