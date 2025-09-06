from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
import importlib
import pytest


def _import_module():
    return importlib.import_module("weightadjust")


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


def test_process_font_all_weights_creates_expected_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    wa = _import_module()

    font = tmp_path / "F.ttf"; font.write_bytes(b"\0")
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
