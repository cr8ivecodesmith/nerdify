from __future__ import annotations

from pathlib import Path
import importlib
import sys
import shutil
import pytest


# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _import_module():
    return importlib.import_module("nameadjust")


def test_humanize_stem_basic_examples():
    na = _import_module()

    s = "PragmataProMonoVF_liga_0902-Extra-bold-NerdFont"
    human = na.humanize_stem(s)
    # Version token (0902) removed
    assert human == "PragmataProMono Liga Extra Bold NerdFont"

    assert na.humanize_stem("my_font-VF-italic") == "My Font Italic"
    assert na.humanize_stem("CoolFont-regular") == "CoolFont Regular"


def test_split_family_subfamily_with_trailing_and_embedded_style():
    na = _import_module()

    human = "PragmataProMono Liga Extra Bold NerdFont"
    fam, sub = na.split_family_subfamily(human)
    # Extract the style phrase and keep remainder as family
    assert sub == "Extra Bold"
    assert fam == "PragmataProMono Liga NerdFont"

    human2 = "CoolFont Regular"
    fam2, sub2 = na.split_family_subfamily(human2)
    assert fam2 == "CoolFont"
    assert sub2 == "Regular"

    # No style tokens -> default Regular
    fam3, sub3 = na.split_family_subfamily("BrandXYZ")
    assert fam3 == "BrandXYZ"
    assert sub3 == "Regular"


def test_ps_name_formatting():
    na = _import_module()
    ps = na.ps_name("Pragmata Pro", "Extra Bold Italic")
    assert ps == "PragmataPro-ExtraBoldItalic"


def test_discover_ttf_mixed(tmp_path: Path):
    na = _import_module()

    d = tmp_path / "a" / "b"; d.mkdir(parents=True)
    t1 = tmp_path / "A.ttf"; t1.write_bytes(b"\0")
    t2 = d / "B.TtF"; t2.write_bytes(b"\0")
    other = d / "readme.md"; other.write_text("hi")

    found = na.discover_ttf([tmp_path, t1])
    assert found == sorted({t1.resolve(), t2.resolve()})


def test_rewrite_name_table_monkeypatched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    na = _import_module()

    calls: list[tuple] = []

    class FakeNameTable:
        def __init__(self):
            self.names = []

        def setName(self, value, nameID, platformID, platEncID, langID):
            calls.append((nameID, platformID, platEncID, langID, value))

    class FakeTTFont:
        def __init__(self, path):
            self.path = Path(path)
            self.tables = {"name": FakeNameTable()}

        def __getitem__(self, key):
            return self.tables[key]

        def save(self, out_path):
            # Simulate write by touching file
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_bytes(b"ok")

        def close(self):
            return None

    monkeypatch.setattr(na, "TTFont", FakeTTFont)

    font = tmp_path / "Font.ttf"
    font.write_bytes(b"\0")

    out = na.rewrite_name_table(font, out_path=None, family="CoolFont", subfamily="Bold Italic")
    # Writes in place when out_path is None
    assert out == font
    assert font.exists()
    # Validate that names were written for Mac and Windows platforms for IDs 16,17,1,2,4,6
    ids = sorted(set(c[0] for c in calls))
    assert ids == [1, 2, 4, 6, 16, 17]


def test_process_font_inplace_and_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    na = _import_module()

    # Monkeypatch TTFont to the same fake used above to avoid heavy real font IO
    class FakeNameTable:
        def __init__(self):
            self.names = []
        def setName(self, value, nameID, platformID, platEncID, langID):
            return None

    class FakeTTFont:
        def __init__(self, path):
            self.path = Path(path)
            self.tables = {"name": FakeNameTable()}
        def __getitem__(self, key):
            return self.tables[key]
        def save(self, out_path):
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_bytes(b"ok")
        def close(self):
            return None

    monkeypatch.setattr(na, "TTFont", FakeTTFont)

    src = tmp_path / "PragmataProMonoVF_liga_0902-Extra-bold-NerdFont.ttf"
    src.write_bytes(b"\0")

    # In-place should rename to cleaned filename and write
    out1 = na.process_font(src, out_dir=None)
    expected_name = "PragmataProMono_Liga_NerdFont-Extra_Bold.ttf"
    assert out1.name == expected_name
    assert out1.exists()
    assert not src.exists()

    # Copy to output dir uses cleaned filename
    out_dir = tmp_path / "out"
    # Use the renamed in-place file as source now
    out2 = na.process_font(out1, out_dir=out_dir)
    assert out2 == out_dir / expected_name
    assert out2.exists()
