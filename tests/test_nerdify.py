from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
import builtins
import types
import pytest
import sys

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_is_font_file_true_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Lazy import to avoid hard import error before implementation exists
    import importlib

    nerdify = importlib.import_module("nerdify")

    assert nerdify.is_font_file(Path("A.ttf"))
    assert nerdify.is_font_file(Path("B.OTF"))
    assert nerdify.is_font_file(Path("C.TtC"))
    assert not nerdify.is_font_file(Path("not-a-font.woff"))
    assert not nerdify.is_font_file(tmp_path)  # directory


def test_discover_fonts_mixed(tmp_path: Path):
    import importlib

    nerdify = importlib.import_module("nerdify")

    # Create a nested directory with fonts and non-fonts
    d1 = tmp_path / "a" / "b"; d1.mkdir(parents=True)
    f1 = tmp_path / "root.ttf"; f1.write_bytes(b"\0")
    f2 = d1 / "sub.otf"; f2.write_bytes(b"\0")
    nf = d1 / "readme.txt"; nf.write_text("hi")
    # Duplicate path in input
    inputs = [f1, tmp_path, Path("/nonexistent/nowhere")]  # nonexistent ignored

    result = nerdify.discover_fonts([Path(p) for p in inputs])
    assert isinstance(result, list)
    # Deterministic: sorted unique absolute paths
    expected = sorted({f1.resolve(), f2.resolve()})
    assert result == expected


def test_build_patch_command_no_outputdir(tmp_path: Path):
    import importlib

    nerdify = importlib.import_module("nerdify")

    fontforge_bin = "fontforge"
    patcher = tmp_path / "FontPatcher" / "font-patcher"
    font = tmp_path / "X.ttf"
    cmd = nerdify.build_patch_command(fontforge_bin, patcher, font)
    # Expected shape
    assert cmd[:2] == ["fontforge", "-script"]
    assert str(patcher) in cmd
    assert str(font) in cmd
    # No implicit outputdir; we move files after
    assert "--outputdir" not in cmd


def test_patch_one_font_moves_outputs(tmp_path: Path):
    import importlib

    nerdify = importlib.import_module("nerdify")

    patcher = tmp_path / "FontPatcher" / "font-patcher"
    patcher.parent.mkdir(parents=True, exist_ok=True)
    patcher.write_text("#!/bin/sh\n")

    font = tmp_path / "A.ttf"
    font.write_bytes(b"\0")

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def runner(argv: list[str], cwd: Path):
        # Simulate the patcher creating a file in the working directory
        created = cwd / "A Nerd Font.ttf"
        created.write_text("ok")
        return CompletedProcess(argv, 0, stdout="done", stderr="")

    moved = nerdify.patch_one_font(font, patcher, out_dir, run_in_cwd=runner)
    assert len(moved) == 1
    assert moved[0] == out_dir / "A-NerdFont.ttf"
    assert moved[0].exists()


def test_check_fontforge_available_ok(monkeypatch: pytest.MonkeyPatch):
    import importlib

    nerdify = importlib.import_module("nerdify")

    def ok_run(argv: list[str]):
        return CompletedProcess(argv, 0, stdout="", stderr="")

    # Should not raise
    nerdify.check_fontforge_available(run=ok_run)


def test_check_fontforge_available_fail(monkeypatch: pytest.MonkeyPatch):
    import importlib
    nerdify = importlib.import_module("nerdify")

    def bad_run(argv: list[str]):
        return CompletedProcess(argv, 127, stdout="", stderr="not found")

    with pytest.raises(RuntimeError):
        nerdify.check_fontforge_available(run=bad_run)


def test_ensure_font_patcher_uses_provided_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import importlib

    nerdify = importlib.import_module("nerdify")

    provided = tmp_path / "FP"
    provided.mkdir()
    patcher = provided / "font-patcher"
    patcher.write_text("#!/bin/sh\n")

    result = nerdify.ensure_font_patcher(patcher_dir=provided, cache_dir=tmp_path)
    assert result == patcher


def test_ensure_font_patcher_downloads_if_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import importlib

    nerdify = importlib.import_module("nerdify")

    # Work in an isolated CWD because implementation extracts into ./FontPatcher
    monkeypatch.chdir(tmp_path)

    # Monkeypatch download/extract to avoid network and actually create the file
    created_zip = tmp_path / "FontPatcher.zip"

    def fake_download(dest_zip: Path, opener=None):
        dest_zip.write_bytes(b"PK\x03\x04fake")

    def fake_extract(zip_path: Path, target_dir: Path):
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "font-patcher").write_text("#!/bin/sh\n")

    monkeypatch.setattr(nerdify, "download_fontpatcher_zip", fake_download)
    monkeypatch.setattr(nerdify, "extract_zip", fake_extract)

    result = nerdify.ensure_font_patcher(patcher_dir=None, cache_dir=tmp_path)
    assert result == (tmp_path / "FontPatcher" / "font-patcher")


def test_patch_font_success_and_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import importlib

    nerdify = importlib.import_module("nerdify")

    ok_cmd = ["fontforge", "-script", str(tmp_path / "font-patcher"), str(tmp_path / "F.ttf")]
    fail_cmd = ["fontforge", "-script", str(tmp_path / "font-patcher"), str(tmp_path / "G.ttf")]

    def runner(argv: list[str]):
        if argv == ok_cmd:
            return CompletedProcess(argv, 0, stdout="done", stderr="")
        return CompletedProcess(argv, 1, stdout="", stderr="boom")

    # Success path should not raise
    nerdify.patch_font(ok_cmd, run=runner)

    # Failure path should raise with stderr included
    with pytest.raises(RuntimeError) as ei:
        nerdify.patch_font(fail_cmd, run=runner)
    msg = str(ei.value)
    assert "boom" in msg or "return code" in msg
