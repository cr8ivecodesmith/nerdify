from __future__ import annotations

import importlib
from pathlib import Path
from subprocess import CompletedProcess
import sys

import pytest

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _import_module():
    return importlib.import_module("weightadjust")


def test_is_ttf_true_false(tmp_path: Path):
    wa = _import_module()

    assert wa.is_ttf(Path("A.ttf"))
    assert wa.is_ttf(Path("B.TTF"))
    assert not wa.is_ttf(Path("X.otf"))
    assert not wa.is_ttf(Path("X.woff"))
    assert not wa.is_ttf(tmp_path)  # directory


def test_discover_ttf_mixed(tmp_path: Path):
    wa = _import_module()

    d1 = tmp_path / "a" / "b"
    d1.mkdir(parents=True)
    f1 = tmp_path / "root.ttf"
    f1.write_bytes(b"\0")
    f2 = d1 / "sub.TtF"
    f2.write_bytes(b"\0")
    nf = d1 / "readme.txt"
    nf.write_text("hi")

    inputs = [f1, tmp_path, Path("/nope/missing")]  # nonexistent ignored
    result = wa.discover_ttf([Path(p) for p in inputs])
    expected = sorted({f1.resolve(), f2.resolve()})
    assert result == expected


def test_parse_weight_valid_invalid():
    wa = _import_module()

    assert wa.parse_weight("400") == 400.0
    assert wa.parse_weight("425.5") == pytest.approx(425.5)

    for bad in ["-1", "abc", "nan", "inf", "-inf", ""]:
        with pytest.raises(Exception):
            wa.parse_weight(bad)


def test_build_mutator_argv(tmp_path: Path):
    wa = _import_module()

    font = tmp_path / "Font.ttf"
    out = tmp_path / "out" / "Font-400.ttf"
    argv = wa.build_mutator_argv(font, 400.0, out, py_exe="/usr/bin/python3")

    assert argv[:3] == ["/usr/bin/python3", "-m", "fontTools.varLib.mutator"]
    assert str(font) in argv
    assert "wght=400.0" in argv
    # Ensure output flag and path are present and ordered
    oi = argv.index("-o")
    assert argv[oi + 1] == str(out)


def test_read_wght_range_found_and_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    wa = _import_module()

    class Axis:
        def __init__(self, tag: str, minimum: float, maximum: float):
            self.tag = tag
            self.minValue = minimum
            self.maxValue = maximum

    class FVar:
        def __init__(self, axes):
            self.axes = axes

    class FakeTTFont:
        def __init__(self, path):
            self.path = path
            # Switch behavior based on filename
            if "has" in path.name:
                self.fvar = FVar([Axis("wght", 200.0, 900.0), Axis("wdth", 75.0, 125.0)])
            elif "nofvar" in path.name:
                self.fvar = None
            else:
                self.fvar = FVar([Axis("wdth", 80.0, 120.0)])

        def close(self):
            return None

    monkeypatch.setattr(wa, "TTFont", FakeTTFont)

    has = tmp_path / "has.ttf"
    has.write_bytes(b"\0")
    missing_axis = tmp_path / "missing.ttf"
    missing_axis.write_bytes(b"\0")
    nofvar = tmp_path / "nofvar.ttf"
    nofvar.write_bytes(b"\0")

    assert wa.read_wght_range(has) == (200.0, 900.0)
    assert wa.read_wght_range(missing_axis) is None
    assert wa.read_wght_range(nofvar) is None


def test_adjust_font_weight_success_and_out_of_range(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    wa = _import_module()

    font = tmp_path / "F.ttf"
    font.write_bytes(b"\0")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    # Mock range to include 400, and exclude 1000
    monkeypatch.setattr(wa, "read_wght_range", lambda p: (200.0, 900.0))

    created_paths: list[Path] = []

    def runner(argv: list[str]) -> CompletedProcess:
        # create the output file indicated after -o
        try:
            oi = argv.index("-o")
            out_path = Path(argv[oi + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"ok")
            created_paths.append(out_path)
            return CompletedProcess(argv, 0, stdout="ok", stderr="")
        except Exception as e:  # pragma: no cover - test should not hit
            return CompletedProcess(argv, 1, stdout="", stderr=str(e))

    # Success path
    dst = wa.adjust_font_weight(font, 400.0, out_dir, runner=runner)
    assert dst == out_dir / f"{font.stem}-400.ttf"
    assert dst.exists()

    # Out-of-range should raise
    with pytest.raises(RuntimeError):
        wa.adjust_font_weight(font, 1000.0, out_dir, runner=runner)


def test_parse_weight_offset_valid_invalid():
    wa = _import_module()

    assert wa.parse_weight_offset("+10") == 10.0
    assert wa.parse_weight_offset("-12.5") == pytest.approx(-12.5)
    assert wa.parse_weight_offset("0") == 0.0

    for bad in ["nan", "inf", "-inf", "abc", ""]:
        with pytest.raises(Exception):
            wa.parse_weight_offset(bad)


def test_compose_weight_basename_formatting(tmp_path: Path):
    wa = _import_module()
    font = tmp_path / "Cool.ttf"
    font.write_bytes(b"\0")

    # No offset: no numeric suffix
    assert wa.compose_weight_basename(font, "Regular", 400, 400.0, 0.0) == "Cool-Regular"

    # With offset: numeric suffix; drop trailing .0
    assert wa.compose_weight_basename(font, "Regular", 400, 410.0, 10.0) == "Cool-Regular-410"
    # Fractional preserves decimal
    assert wa.compose_weight_basename(font, "Bold", 700, 712.5, 12.5) == "Cool-Bold-712.5"


def test_process_font_all_weights_creates_expected_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    wa = _import_module()

    font = tmp_path / "F.ttf"
    font.write_bytes(b"\0")
    out_dir = tmp_path / "out"

    # Provide a temporary fontweights.toml as required by the tool
    cfg = tmp_path / "fontweights.toml"
    cfg.write_text(
        """
        [weights]
        Thin = 100
        "Extra-Light" = 200
        Light = 300
        Regular = 400
        Medium = 500
        "Semi-Bold" = 600
        Bold = 700
        "Extra-Bold" = 800
        Black = 900
        """,
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    # Range covers all standard weights
    monkeypatch.setattr(wa, "read_wght_range", lambda p: (100.0, 900.0))

    created_paths: list[Path] = []

    def runner(argv: list[str]) -> CompletedProcess:
        try:
            oi = argv.index("-o")
            out_path = Path(argv[oi + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"ok")
            created_paths.append(out_path)
            return CompletedProcess(argv, 0, stdout="ok", stderr="")
        except Exception as e:  # pragma: no cover
            return CompletedProcess(argv, 1, stdout="", stderr=str(e))

    # No offset: expect 9 outputs with names lacking numeric suffix
    results = wa.process_font_all_weights(font, out_dir, 0.0, runner=runner)
    assert len(results) == 9
    assert (out_dir / "F-Regular.ttf").exists()
    assert (out_dir / "F-Bold.ttf").exists()

    # With offset: additional files with numeric suffix
    out_dir2 = tmp_path / "out2"
    results2 = wa.process_font_all_weights(font, out_dir2, 10.0, runner=runner)
    assert len(results2) == 9
    assert (out_dir2 / "F-Regular-410.ttf").exists()
    assert (out_dir2 / "F-Bold-710.ttf").exists()
