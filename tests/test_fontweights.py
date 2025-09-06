from __future__ import annotations

from pathlib import Path
import pytest


def test_load_config_missing_file_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    from common import fontweights as fw

    with pytest.raises(RuntimeError):
        fw.load_config()


def test_parse_and_sort_weights_and_lookup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    toml = (
        """
        [weights]
        Thin = 100
        "Extra-Light" = 200

        [aliases]
        "Extra Light" = "Extra-Light"
        "ULTRA   LIGHT" = "Extra-Light"
        """
    )
    (tmp_path / "fontweights.toml").write_text(toml, encoding="utf-8")
    from common import fontweights as fw

    cfg = fw.load_config()
    weights = fw.standard_weights(cfg)
    assert weights == [(100, "Thin"), (200, "Extra-Light")]

    # canonical name lookup
    assert fw.canonical_name_for(cfg, "Extra Light") == "Extra-Light"
    assert fw.canonical_name_for(cfg, "extra-light") == "Extra-Light"
    assert fw.canonical_name_for(cfg, "ULTRA LIGHT") == "Extra-Light"
    assert fw.lookup_value(cfg, "Thin") == 100
    assert fw.lookup_value(cfg, "unknown") is None


def test_invalid_weights_table_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    # Non-dict weights
    (tmp_path / "fontweights.toml").write_text("weights = 1\n", encoding="utf-8")
    from common import fontweights as fw
    with pytest.raises(RuntimeError):
        fw.load_config()

    # Empty dict
    (tmp_path / "fontweights.toml").write_text("[weights]\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        fw.load_config()

    # Non-int value
    (tmp_path / "fontweights.toml").write_text("[weights]\nThin = '100'\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        fw.load_config()


def test_alias_warnings_and_ignores(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture):
    monkeypatch.chdir(tmp_path)
    toml = (
        """
        [weights]
        Thin = 100

        [aliases]
        Foo = "Unknown"
        Bad = 123
        """
    )
    (tmp_path / "fontweights.toml").write_text(toml, encoding="utf-8")
    from common import fontweights as fw

    cfg = fw.load_config()
    captured = capsys.readouterr()
    assert "alias 'Foo' refers to unknown canonical 'Unknown'" in captured.err
    assert "alias entries must be strings" in captured.err

    # Unknown alias is ignored
    assert fw.canonical_name_for(cfg, "Foo") is None
    # Valid canonical still works
    assert fw.lookup_value(cfg, "Thin") == 100

