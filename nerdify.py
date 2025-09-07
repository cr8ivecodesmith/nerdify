#!/usr/bin/env python3

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
import io
from pathlib import Path
from subprocess import CompletedProcess
import zipfile

FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}


def is_font_file(path: Path) -> bool:
    """Return True if the given path looks like a supported font file.

    This checks the filename extension only; callers decide existence.
    """
    try:
        suffix = path.suffix.lower()
    except Exception:
        return False
    return suffix in FONT_EXTENSIONS


def discover_fonts(inputs: Iterable[Path]) -> list[Path]:
    """Discover font files from a mix of file and directory inputs.

    - Non-existent inputs are ignored.
    - Directories are searched recursively.
    - Returns a sorted list of unique absolute paths for determinism.
    """
    found: set[Path] = set()
    for raw in inputs:
        p = Path(raw)
        if not p.exists():
            continue
        if p.is_file():
            if is_font_file(p):
                found.add(p.resolve())
        elif p.is_dir():
            for sub in p.rglob("*"):
                if sub.is_file() and is_font_file(sub):
                    found.add(sub.resolve())
    return sorted(found)


def check_fontforge_available(*, run: Callable[[Sequence[str]], CompletedProcess]) -> None:
    """Ensure `fontforge` is available by checking its version.

    Raises RuntimeError with actionable guidance when not available.
    """
    try:
        result = run(["fontforge", "-version"])
    except Exception as exc:  # pragma: no cover - exercised via return code path
        raise RuntimeError(
            "fontforge not found. Install via `requirements.sh` or your package manager."
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            "fontforge not found. Install via `requirements.sh` or your package manager."
        )


def download_fontpatcher_zip(
    dest_zip: Path, opener: Callable[[str], io.BufferedReader] | None = None
) -> None:
    """Download the FontPatcher.zip archive to `dest_zip`.

    Attempts to use `requests` if available, otherwise falls back to urllib.
    """
    url = "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FontPatcher.zip"
    dest_zip.parent.mkdir(parents=True, exist_ok=True)

    if opener is not None:
        with opener(url) as r, open(dest_zip, "wb") as f:
            f.write(r.read())
        return

    try:
        import requests  # type: ignore

        with requests.get(url, timeout=30, stream=True) as resp:  # type: ignore[attr-defined]
            resp.raise_for_status()
            with open(dest_zip, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
        return
    except Exception:
        # Fallback to stdlib
        import urllib.request

        with urllib.request.urlopen(url, timeout=30) as r:  # type: ignore[attr-defined]
            data = r.read()
        with open(dest_zip, "wb") as f:
            f.write(data)


def extract_zip(zip_path: Path, target_dir: Path) -> None:
    """Extract `zip_path` into `target_dir` safely."""
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        # Basic zip slip protection
        for member in zf.infolist():
            extracted_path = (target_dir / member.filename).resolve()
            if (
                target_dir.resolve() not in extracted_path.parents
                and extracted_path != target_dir.resolve()
            ):
                raise RuntimeError(f"Unsafe path in archive: {member.filename}")
        zf.extractall(target_dir)


def ensure_font_patcher(*, patcher_dir: Path | None, cache_dir: Path) -> Path:
    """Return path to the `font-patcher` executable.

    Order of resolution:
    1) Explicit `patcher_dir` if provided.
    2) Local `./FontPatcher/font-patcher` in current working directory.
    3) Download FontPatcher.zip into `cache_dir` and extract to `./FontPatcher`.
    """
    if patcher_dir is not None:
        candidate = patcher_dir / "font-patcher"
        if candidate.exists():
            return candidate
        raise RuntimeError(f"Invalid --fontpatcher-dir; missing: {candidate}")

    local_dir = Path.cwd() / "FontPatcher"
    local_patcher = local_dir / "font-patcher"
    if local_patcher.exists():
        return local_patcher

    # Download to cache and extract into ./FontPatcher
    dest_zip = cache_dir / "FontPatcher.zip"
    download_fontpatcher_zip(dest_zip)
    extract_zip(dest_zip, local_dir)
    if not local_patcher.exists():
        raise RuntimeError("FontPatcher download/extract did not produce font-patcher executable")
    return local_patcher


def build_patch_command(fontforge_bin: str, patcher: Path, font: Path) -> list[str]:
    """Build the fontforge invocation command for a single font.

    No output directory is passed; outputs are collected and moved explicitly.
    """
    return [fontforge_bin, "-script", str(patcher), str(font)]


def patch_font(cmd: Sequence[str], *, run: Callable[[Sequence[str]], CompletedProcess]) -> None:
    """Execute patch command; raise RuntimeError on failure including stderr."""
    result = run(list(cmd))
    if result.returncode != 0:
        stderr = getattr(result, "stderr", "") or ""
        raise RuntimeError(f"Patching failed (return code {result.returncode}). {stderr}")


def _snapshot_files(d: Path) -> set[Path]:
    return {p.resolve() for p in d.glob("**/*") if p.is_file()}


def patch_one_font(
    font: Path,
    patcher: Path,
    out_dir: Path,
    *,
    run_in_cwd: Callable[[Sequence[str], Path], CompletedProcess],
) -> list[Path]:
    """Patch a single font by running the patcher in a temp dir, then move outputs.

    Returns the list of destination file Paths moved into `out_dir`.
    Raises RuntimeError if the patcher returns a non-zero exit code.
    """
    import shutil
    import tempfile

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = build_patch_command("fontforge", patcher, font)

    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        before = _snapshot_files(workdir)
        result = run_in_cwd(cmd, workdir)
        if result.returncode != 0:
            stderr = getattr(result, "stderr", "") or ""
            raise RuntimeError(f"Patching failed (return code {result.returncode}). {stderr}")
        after = _snapshot_files(workdir)
        new_files = sorted(after - before)
        moved: list[Path] = []
        for src in new_files:
            # Rename patched font outputs to "<stem>-NerdFont.<ext>" for clarity
            if is_font_file(src):
                dest_name = f"{font.stem}-NerdFont{src.suffix.lower()}"
                dest = out_dir / dest_name
            else:
                dest = out_dir / src.name
            shutil.move(str(src), dest)
            moved.append(dest)
        return moved


def main(
    argv: Sequence[str] | None = None,
) -> int:  # pragma: no cover - CLI wiring, tested indirectly
    import argparse
    import subprocess

    parser = argparse.ArgumentParser(description="Patch fonts with Nerd Fonts glyphs")
    parser.add_argument("paths", nargs="+", help="Font files or directories to process")
    parser.add_argument("-o", "--output", dest="output", default=".", help="Output directory")
    parser.add_argument(
        "--fontpatcher-dir",
        dest="fontpatcher_dir",
        default=None,
        help="Existing FontPatcher directory",
    )
    parser.add_argument(
        "--cache-dir",
        dest="cache_dir",
        default=str(Path.cwd() / "FontPatcher"),
        help="Directory for downloads",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    def _run(a: Sequence[str]) -> CompletedProcess:
        return subprocess.run(a, capture_output=True, text=True)

    check_fontforge_available(run=_run)

    patcher = ensure_font_patcher(
        patcher_dir=Path(args.fontpatcher_dir) if args.fontpatcher_dir else None,
        cache_dir=Path(args.cache_dir),
    )

    fonts = discover_fonts([Path(p) for p in args.paths])
    if not fonts:
        print("No fonts found to patch.")
        return 1

    failures = 0
    for font in fonts:
        try:

            def run_in_cwd(argv: Sequence[str], cwd: Path) -> CompletedProcess:
                import subprocess

                return subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True)

            patch_one_font(font, patcher, out_dir, run_in_cwd=run_in_cwd)
            print(f"OK: {font.name}")
        except Exception as exc:
            failures += 1
            print(f"FAIL: {font.name}: {exc}")

    return 0 if failures == 0 else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
