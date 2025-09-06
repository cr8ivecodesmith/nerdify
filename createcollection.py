#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Literal, Sequence


SUPPORTED_EXTS = {".ttf", ".otf"}
ITALIC_TOKENS: set[str] = {"italic", "oblique"}


def is_ttf(path: Path) -> bool:
    """Return True if path has .ttf extension (case-insensitive)."""
    return path.suffix.lower() == ".ttf"


def is_otf(path: Path) -> bool:
    """Return True if path has .otf extension (case-insensitive)."""
    return path.suffix.lower() == ".otf"


def discover_fonts(inputs: Iterable[Path]) -> list[Path]:
    """Discover supported font files (.ttf, .otf) from files/dirs recursively.

    Returns a sorted list of resolved Paths.
    """
    files: list[Path] = []
    for p in inputs:
        if not isinstance(p, Path):
            p = Path(p)  # type: ignore[assignment]
        if not p.exists():
            print(f"Warning: path not found: {p}")
            continue
        if p.is_dir():
            for cand in p.rglob("*"):
                if cand.is_file() and cand.suffix.lower() in SUPPORTED_EXTS:
                    files.append(cand)
        elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            files.append(p)
    # Deduplicate by resolved path and sort by name deterministically
    resolved = sorted({f.resolve() for f in files}, key=lambda x: x.name)
    return list(resolved)


def sniff_sfnt_type(path: Path) -> Literal["ttf", "otf"]:
    """Sniff sfnt type by header bytes.

    - OTTO => CFF/OpenType (otf)
    - 00010000 or 'true' => TrueType (ttf)
    """
    with path.open("rb") as fh:
        head = fh.read(4)
    if head == b"OTTO":
        return "otf"
    if head in (b"\x00\x01\x00\x00", b"true"):
        return "ttf"
    raise ValueError(f"Unrecognized sfnt header for {path}")


def infer_collection_type(paths: Sequence[Path], forced: str | None) -> Literal["ttc", "otc"]:
    """Infer collection container type from inputs or honor a forced type.

    Raises ValueError on mixed inputs or mismatch with forced type.
    """
    if not paths:
        raise ValueError("No input fonts to infer type from")
    kinds = {sniff_sfnt_type(p) for p in paths}
    if forced:
        forced = forced.lower()
        if forced not in {"ttc", "otc"}:
            raise ValueError("--type must be 'ttc' or 'otc'")
        need = "ttf" if forced == "ttc" else "otf"
        if kinds != {need}:
            raise ValueError(f"Forced type {forced} conflicts with input types {kinds}")
        return forced  # type: ignore[return-value]
    if kinds == {"ttf"}:
        return "ttc"
    if kinds == {"otf"}:
        return "otc"
    raise ValueError("Mixed TTF/OTF inputs; specify --type or filter inputs")


def _import_fonttools_tt():
    try:
        from fontTools.ttLib import TTFont
        from fontTools.ttLib.ttCollection import TTCollection
    except Exception as e:  # pragma: no cover - exercised via call sites
        raise RuntimeError("fonttools not installed; see requirements.txt") from e
    return TTFont, TTCollection


def read_family_and_subfamily(path: Path) -> tuple[str | None, str | None]:
    """Read Typographic Family/Subfamily (IDs 16/17) with Legacy (1/2) fallback.

    Returns (family, subfamily) or (None, None) if not found.
    """
    TTFont, _ = _import_fonttools_tt()
    family: str | None = None
    subfam: str | None = None
    font = TTFont(str(path), lazy=True)
    try:
        name = font["name"]
        # Prefer Windows then Mac
        def _get(nid: int) -> str | None:
            for rec in name.names:
                if rec.nameID == nid and (rec.platformID, rec.platEncID) in ((3, 1), (1, 0)):
                    try:
                        return str(rec.toUnicode()).strip()
                    except Exception:
                        continue
            return None

        family = _get(16) or _get(1)
        subfam = _get(17) or _get(2)
    finally:
        try:
            font.close()
        except Exception:
            pass
    return family, subfam


_VERSION_TOKEN_RE = re.compile(r"^(?:v)?\d+(?:[._]\d+)*$")


def tokenize_stem(stem: str) -> list[str]:
    """Tokenize a filename stem on '-' and '_', to lowercase alphanumeric tokens."""
    raw = re.split(r"[-_]+", stem)
    toks = [t.strip().lower() for t in raw if t.strip()]
    return toks


def _strip_nonfamily_tokens(tokens: list[str]) -> list[str]:
    """Strip only obvious non-family tokens for basename inference.

    Removes: italic markers, VF markers, and version-like tokens. Does not
    attempt to strip weight/style words.
    """
    result: list[str] = []
    for t in tokens:
        if t in ITALIC_TOKENS or t in {"vf", "variable", "var"} or _VERSION_TOKEN_RE.match(t):
            continue
        result.append(t)
    return result


def common_token_prefix(list_of_tokens: Sequence[list[str]]) -> list[str]:
    """Longest common prefix across multiple token lists."""
    if not list_of_tokens:
        return []
    min_len = min(len(t) for t in list_of_tokens)
    out: list[str] = []
    for idx in range(min_len):
        col = {t[idx] for t in list_of_tokens}
        if len(col) == 1:
            out.append(next(iter(col)))
        else:
            break
    return out


def sanitize_filename(name: str) -> str:
    """Make a filesystem-safe filename stem.

    - Replace spaces with underscores.
    - Retain existing dashes.
    - Allow only A–Z, a–z, 0–9, dash, underscore, dot.
    - Collapse repeated underscores and dashes; trim leading/trailing separators.
    """
    name = name.replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9._-]", "", name)
    name = re.sub(r"_+", "_", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-._")


def derive_collection_basename(fonts: Sequence[Path]) -> str:
    """Derive a collection base filename from a consensus Typographic Family.

    If there is no single non-empty shared family, fall back to the parent directory
    name of the first font, or its stem if parent is empty.
    """
    try:
        families: list[str] = []
        for p in fonts:
            fam, _ = read_family_and_subfamily(p)
            if fam:
                families.append(" ".join(fam.split()))  # normalize spaces
        unique = {f for f in families if f}
        if len(unique) == 1:
            return next(iter(unique))
    except RuntimeError:
        # fonttools missing or unreadable name table; fall through to fallback
        pass
    # Light filename heuristic: use common token prefix with only non-family
    # tokens removed (italic/vf/version), preserving original case from first file
    token_lists = [_strip_nonfamily_tokens(tokenize_stem(p.stem)) for p in fonts]
    prefix = common_token_prefix(token_lists)
    if prefix:
        base_tokens: list[str] = []
        first_tokens = re.split(r"[-_]+", fonts[0].stem)
        fi = 0
        for tok in prefix:
            while fi < len(first_tokens) and first_tokens[fi].strip().lower() != tok:
                fi += 1
            if fi < len(first_tokens):
                base_tokens.append(first_tokens[fi].strip())
                fi += 1
            else:
                base_tokens.append(tok)
        return sanitize_filename(" ".join(base_tokens))
    parent = fonts[0].parent.name or fonts[0].stem
    return sanitize_filename(parent)


def read_weight_and_italic(path: Path) -> tuple[int | None, bool]:
    """Read OS/2 weight and italic flag from a font.

    Returns (weight or None, is_italic). Weight is OS/2.usWeightClass if present.
    Italic is detected via OS/2.fsSelection bit 0, with head.macStyle bit 1 fallback.
    """
    TTFont, _ = _import_fonttools_tt()
    font = TTFont(str(path), lazy=True)
    try:
        weight = None
        italic = False
        if "OS/2" in font:
            os2 = font["OS/2"]
            try:
                weight = int(getattr(os2, "usWeightClass", None)) if getattr(os2, "usWeightClass", None) is not None else None
            except Exception:
                weight = None
            try:
                fs = int(getattr(os2, "fsSelection", 0))
                italic = bool(fs & 0x01) or italic
            except Exception:
                pass
        if not italic and "head" in font:
            try:
                head = font["head"]
                ms = int(getattr(head, "macStyle", 0))
                italic = bool(ms & 0x02) or italic
            except Exception:
                pass
        return weight, italic
    finally:
        try:
            font.close()
        except Exception:
            pass


def sort_fonts(fonts: Sequence[Path]) -> list[Path]:
    """Sort fonts by OS/2 weight (asc) then Roman before Italic; tiebreaker by name."""
    keyed: list[tuple[int, int, str, Path]] = []
    for p in fonts:
        w, it = read_weight_and_italic(p)
        weight_key = w if w is not None else 1000
        keyed.append((weight_key, 1 if it else 0, p.name.lower(), p))
    keyed.sort(key=lambda t: (t[0], t[1], t[2]))
    return [k[-1] for k in keyed]


def write_collection(fonts: Sequence[Path], out_path: Path, kind: Literal["ttc", "otc"]) -> None:
    """Write a TTC/OTC collection composed of the given font paths."""
    # Validate consistency with kind
    need = "ttf" if kind == "ttc" else "otf"
    for p in fonts:
        sf = sniff_sfnt_type(p)
        if sf != need:
            raise ValueError(f"Input {p} is {sf}, not compatible with {kind}")
    TTFont, TTCollection = _import_fonttools_tt()
    ttfonts = []
    try:
        for p in fonts:
            ttfonts.append(TTFont(str(p), lazy=True, recalcTimestamp=False))
        # Initialize empty collection and assign fonts
        coll = TTCollection()
        coll.fonts = ttfonts
        out_path.parent.mkdir(parents=True, exist_ok=True)
        coll.save(str(out_path))
    finally:
        for f in ttfonts:
            try:
                f.close()
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create a TTC/OTC from fonts")
    p.add_argument("paths", nargs="+", help="Font files or directories")
    p.add_argument("-o", "--output", default=".", help="Output directory")
    p.add_argument("--type", choices=["ttc", "otc"], help="Force output type")
    p.add_argument("--name", help="Override collection filename (no extension)")
    p.add_argument("--dry-run", action="store_true", help="Print plan; do not write files")
    p.add_argument("-q", "--quiet", action="store_true", help="Reduce logging")
    p.add_argument("-v", "--verbose", action="store_true", help="Increase logging")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inputs = [Path(s) for s in args.paths]
    fonts = discover_fonts(inputs)
    if not fonts:
        print("No supported fonts found (.ttf/.otf).", file=sys.stderr)
        return 1
    try:
        kind = infer_collection_type(fonts, args.type)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    base = args.name or derive_collection_basename(fonts)
    out_dir = Path(args.output)
    ext = ".ttc" if kind == "ttc" else ".otc"
    out_path = out_dir / f"{sanitize_filename(base)}{ext}"
    ordered = sort_fonts(fonts)
    if args.dry_run:
        print(f"Would create collection: name={out_path.name} type={kind} count={len(ordered)}")
        for p in ordered:
            print(f"  include: {p.name}")
        return 0
    try:
        write_collection(ordered, out_path, kind)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"Wrote {out_path} ({len(ordered)} fonts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
