from __future__ import annotations

from pathlib import Path
import pytest


def _write_cfg(tmp_path: Path):
    (tmp_path / "fontweights.toml").write_text(
        """
        [weights]
        Thin = 100
        "Extra-Light" = 200
        Regular = 400

        [aliases]
        "Ultra Light" = "Extra-Light"
        """,
        encoding="utf-8",
    )


def test_split_family_subfamily_uses_alias(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from nameadjust import split_family_subfamily

    monkeypatch.chdir(tmp_path)
    _write_cfg(tmp_path)

    fam, sub = split_family_subfamily("Cool Ultra Light Italic")
    assert fam == "Cool"
    assert sub == "Ultra Light Italic"


def test_infer_weight_and_italic_from_subfamily(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from nameadjust import _infer_weight_and_italic_from_subfamily

    monkeypatch.chdir(tmp_path)
    _write_cfg(tmp_path)

    w, it = _infer_weight_and_italic_from_subfamily("Ultra Light Italic")
    assert w == 200 and it is True

