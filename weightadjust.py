#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Callable, Iterable, List, Optional, Tuple
import argparse
import math
import sys

from fontTools.ttLib import TTFont  # type: ignore
from common.fontweights import load_config, standard_weights


def is_ttf(path: Path) -> bool:
    """Return True if path has a .ttf suffix (case-insensitive).

    Does not check existence; suitable for suffix checks in pure logic.
    """
    return path.suffix.lower() == ".ttf"


def discover_ttf(inputs: Iterable[Path]) -> list[Path]:
    """Discover .ttf files from provided files and directories.

    - Nonexistent paths are ignored.
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
            # nonexistent or special; ignore
            continue
    return sorted(found)


def parse_weight(value: str) -> float:
    """Parse a weight string to float, validating positivity and finiteness."""
    try:
        w = float(value)
    except Exception as e:  # noqa: BLE001 - return argparse-friendly error upstream
        raise argparse.ArgumentTypeError(f"invalid weight '{value}'") from e
    if not math.isfinite(w) or w < 0:
        raise argparse.ArgumentTypeError(f"invalid weight '{value}'")
    return w


def read_wght_range(ttf_path: Path) -> tuple[float, float] | None:
    """Read the wght axis min/max from a variable TTF.

    Returns (min, max) if the font has an fvar table with a wght axis,
    otherwise returns None.
    """
    font = TTFont(ttf_path)
    try:
        fvar = getattr(font, "fvar", None)
        if not fvar:
            return None
        for axis in getattr(fvar, "axes", []) or []:
            if getattr(axis, "tag", "") == "wght":
                return float(axis.minValue), float(axis.maxValue)
        return None
    finally:
        try:
            font.close()  # type: ignore[attr-defined]
        except Exception:
            pass


def _weight_for_filename(weight: float) -> str:
    """Format weight for filenames without unnecessary trailing .0."""
    if float(weight).is_integer():
        return str(int(weight))
    return str(weight)



def parse_weight_offset(value: str) -> float:
    """Parse a weight offset string to float.

    Accepts forms like "+10", "-10", "10", "-12.5"; rejects NaN/inf.
    """
    try:
        w = float(value)
    except Exception as e:  # noqa: BLE001
        raise argparse.ArgumentTypeError(f"invalid weight offset '{value}'") from e
    if not math.isfinite(w):
        raise argparse.ArgumentTypeError(f"invalid weight offset '{value}'")
    return w


def compose_weight_basename(font: Path, weight_name: str, base: int, resolved: float, offset: float) -> str:
    """Return output basename (without extension) for a font/weight.

    - If offset is zero: <stem>-<WeightName>
    - Else: <stem>-<WeightName>-<ResolvedWeight>
    """
    stem = font.stem
    if offset == 0:
        return f"{stem}-{weight_name}"
    return f"{stem}-{weight_name}-{_weight_for_filename(resolved)}"


def _rewrite_internal_names(ttf_path: Path, *, weight_name: str, resolved_weight: float, offset: float) -> None:
    """Rewrite internal name records to include weight name and resolved weight when offset != 0.

    - Subfamily (nameID=2): set to `<WeightName>` or `<WeightName>-<Resolved>` when offset != 0.
    - Full name (nameID=4): `<Family> <Subfamily>`.
    - PostScript name (nameID=6): `<Family>-<Subfamily>` with spaces removed.

    If the name table is missing or encoding issues arise, this function raises; callers may choose to ignore.
    """
    font = TTFont(ttf_path)
    try:
        name_tbl = font["name"]
        # Determine family name: prefer existing nameID 1; fall back to file stem
        family = None
        for rec in name_tbl.names:
            if rec.nameID == 1:
                try:
                    family = rec.toUnicode()
                    if family:
                        break
                except Exception:
                    continue
        if not family:
            family = ttf_path.stem

        subfamily = weight_name if offset == 0 else f"{weight_name}-{_weight_for_filename(resolved_weight)}"
        full_name = f"{family} {subfamily}".strip()
        ps_name = f"{family.replace(' ', '')}-{subfamily.replace(' ', '')}"

        # Set Windows (3,1,0x409) and Mac (1,0,0) names
        name_tbl.setName(family, 1, 3, 1, 0x409)
        name_tbl.setName(subfamily, 2, 3, 1, 0x409)
        name_tbl.setName(full_name, 4, 3, 1, 0x409)
        name_tbl.setName(ps_name, 6, 3, 1, 0x409)

        name_tbl.setName(family, 1, 1, 0, 0)
        name_tbl.setName(subfamily, 2, 1, 0, 0)
        name_tbl.setName(full_name, 4, 1, 0, 0)
        name_tbl.setName(ps_name, 6, 1, 0, 0)

        font.save(ttf_path)
    finally:
        try:
            font.close()
        except Exception:
            pass


def build_mutator_argv(font: Path, weight: float, out_path: Path, *, py_exe: str = sys.executable) -> list[str]:
    """Build argv to invoke FontTools varLib.mutator for a font/weight/output."""
    return [
        py_exe,
        "-m",
        "fontTools.varLib.mutator",
        str(font),
        f"wght={weight}",
        "-o",
        str(out_path),
    ]


def run_mutator(argv: list[str]) -> CompletedProcess:
    """Execute the provided argv and return the CompletedProcess."""
    return run(argv, capture_output=True, text=True)


def adjust_font_weight(
    font: Path,
    weight: float,
    out_dir: Path,
    *,
    runner: Callable[[list[str]], CompletedProcess] = run_mutator,
    out_basename: str | None = None,
) -> Path:
    """Adjust the weight of one variable TTF and write into out_dir.

    Returns the output path on success; raises RuntimeError on error.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = read_wght_range(font)
    if rng is not None:
        mn, mx = rng
        if not (mn <= weight <= mx):
            raise RuntimeError(
                f"weight {weight} outside supported range [{mn}, {mx}] for '{font.name}'"
            )

    if out_basename:
        out_name = f"{out_basename}.ttf"
    else:
        out_name = f"{font.stem}-{_weight_for_filename(weight)}.ttf"
    out_path = out_dir / out_name

    argv = build_mutator_argv(font, weight, out_path)
    proc = runner(argv)
    if proc.returncode != 0:
        msg = proc.stderr or proc.stdout or "mutator failed"
        raise RuntimeError(f"mutator failed for {font.name} (rc={proc.returncode}): {msg}")
    return out_path


def process_font_all_weights(
    font: Path,
    out_dir: Path,
    offset: float,
    *,
    runner: Callable[[list[str]], CompletedProcess] = run_mutator,
) -> list[Path]:
    """Generate outputs for each standard weight for one font.

    Skips weights that are outside the font's supported wght range (if known).
    Returns the list of created output paths.
    """
    created: list[Path] = []
    rng = read_wght_range(font)
    # Load weights config (required)
    cfg = load_config()
    for base, name in standard_weights(cfg):
        target = float(base) + float(offset)
        if rng is not None:
            mn, mx = rng
            # Clamp to supported range to ensure we always produce 9 outputs
            if target < mn:
                target = mn
            elif target > mx:
                target = mx
        basename = compose_weight_basename(font, name, base, target, offset)
        try:
            p = adjust_font_weight(font, target, out_dir, runner=runner, out_basename=basename)
            # Attempt to update internal names; non-fatal if it fails (e.g., in tests)
            try:
                _rewrite_internal_names(p, weight_name=name, resolved_weight=target, offset=offset)
            except Exception as ie:  # noqa: BLE001
                print(f"WARN {font.name} {name}: could not rewrite internal names: {ie}", file=sys.stderr)
            created.append(p)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {font.name} {name}: {e}", file=sys.stderr)
    return created


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="weightadjust",
        description="Adjust the weight axis of variable TTF fonts using FontTools.",
    )
    p.add_argument(
        "paths",
        nargs="+",
        help="Font files or directories to search for .ttf files",
    )
    p.add_argument(
        "-w",
        "--weight-offset",
        dest="weight_offset",
        type=parse_weight_offset,
        default=0.0,
        help="Numeric offset applied to each standard weight (e.g., +10, -10). Default: 0",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path.cwd(),
        help="Output directory (default: CWD)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    inputs = [Path(p) for p in args.paths]
    fonts = discover_ttf(inputs)
    if not fonts:
        print("No .ttf files found under provided paths.", file=sys.stderr)
        return 1

    out_dir: Path = Path(args.output)
    total_created = 0
    total_failed_fonts = 0
    for f in fonts:
        created = process_font_all_weights(f, out_dir, float(args.weight_offset))
        if created:
            total_created += len(created)
            print(f"OK  {f.name}: {len(created)} outputs")
        else:
            total_failed_fonts += 1
            print(f"FAIL {f.name}: no outputs created", file=sys.stderr)

    print(f"Done. Outputs: {total_created}, Fonts with no outputs: {total_failed_fonts}")
    return 0 if total_failed_fonts == 0 else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
