from pathlib import Path

import pytest


def write_header(path: Path, header: bytes) -> None:
    path.write_bytes(header + b"\x00" * 16)


@pytest.fixture
def tdir(tmp_path: Path) -> Path:
    return tmp_path


def test_discover_fonts(tdir: Path):
    from createcollection import discover_fonts

    a = tdir / "A.ttf"
    b = tdir / "B.otf"
    c = tdir / "C.txt"
    sub = tdir / "sub"
    sub.mkdir()
    d = sub / "D.TTF"
    for p, h in [
        (a, b"\x00\x01\x00\x00"),
        (b, b"OTTO"),
        (d, b"\x00\x01\x00\x00"),
    ]:
        write_header(p, h)
    c.write_text("noop")

    out = discover_fonts([tdir])
    assert [p.name for p in out] == ["A.ttf", "B.otf", "D.TTF"]


def test_sniff_sfnt_type_and_infer(tdir: Path):
    from createcollection import infer_collection_type, sniff_sfnt_type

    ttf = tdir / "a.ttf"
    otf = tdir / "b.otf"
    write_header(ttf, b"\x00\x01\x00\x00")
    write_header(otf, b"OTTO")

    assert sniff_sfnt_type(ttf) == "ttf"
    assert sniff_sfnt_type(otf) == "otf"

    assert infer_collection_type([ttf], None) == "ttc"
    assert infer_collection_type([otf], None) == "otc"

    with pytest.raises(ValueError):
        infer_collection_type([ttf, otf], None)

    # Forced type must match inputs
    with pytest.raises(ValueError):
        infer_collection_type([ttf], "otc")
    with pytest.raises(ValueError):
        infer_collection_type([otf], "ttc")


def test_sanitize_filename():
    from createcollection import sanitize_filename

    assert sanitize_filename("Cool Font!@#") == "Cool_Font"


def test_derive_collection_basename_internal_family(monkeypatch, tdir: Path):
    from createcollection import derive_collection_basename

    f1 = tdir / "Family-Regular.ttf"
    f2 = tdir / "Family-Bold.ttf"
    write_header(f1, b"\x00\x01\x00\x00")
    write_header(f2, b"\x00\x01\x00\x00")

    import createcollection as cc

    monkeypatch.setattr(cc, "read_family_and_subfamily", lambda p: ("Cool Family", "Regular"))

    name = derive_collection_basename([f1, f2])
    assert name == "Cool Family"


def test_derive_collection_basename_filename_fallback(monkeypatch, tdir: Path):
    from createcollection import derive_collection_basename

    f1 = tdir / "MyFont-0902-Regular.ttf"
    f2 = tdir / "MyFont-0902-Bold.ttf"
    write_header(f1, b"\x00\x01\x00\x00")
    write_header(f2, b"\x00\x01\x00\x00")

    import createcollection as cc

    # No internal names
    monkeypatch.setattr(cc, "read_family_and_subfamily", lambda p: (None, None))

    name = derive_collection_basename([f1, f2])
    assert name == "MyFont"


def test_sort_fonts_by_weight_and_italic(monkeypatch, tdir: Path):
    from createcollection import sort_fonts

    f_reg = tdir / "A-Regular.ttf"
    f_bold = tdir / "A-Bold.ttf"
    f_reg_it = tdir / "A-Regular-Italic.ttf"
    for p in (f_reg, f_bold, f_reg_it):
        write_header(p, b"\x00\x01\x00\x00")

    import createcollection as cc

    # Use OS/2 data to drive sorting (monkeypatched)
    mapping = {
        f_reg: (400, False),
        f_bold: (700, False),
        f_reg_it: (400, True),
    }
    monkeypatch.setattr(cc, "read_weight_and_italic", lambda p: mapping[p])

    ordered = sort_fonts([f_reg_it, f_bold, f_reg])
    assert ordered == [f_reg, f_reg_it, f_bold]


def test_write_collection_monkeypatched(monkeypatch, tdir: Path):
    from createcollection import write_collection

    f1 = tdir / "A-Regular.ttf"
    f2 = tdir / "A-Bold.ttf"
    for p in (f1, f2):
        write_header(p, b"\x00\x01\x00\x00")

    out = tdir / "A.ttc"

    # Dummy TTFont/TTCollection
    opened = []
    saved = {}

    class DummyTTFont:
        def __init__(self, path, lazy=True, recalcTimestamp=False):
            opened.append(Path(path))

        def close(self):
            pass

    class DummyTTCollection:
        def __init__(self):
            self.fonts = []

        def save(self, path):
            saved["path"] = Path(path)
            saved["count"] = len(self.fonts)

    # Patch fonttools import points inside module
    import createcollection as cc

    def fake_import_ttfont():
        return DummyTTFont, DummyTTCollection

    monkeypatch.setattr(cc, "_import_fonttools_tt", fake_import_ttfont)

    write_collection([f1, f2], out, "ttc")
    assert saved["path"] == out
    assert saved["count"] == 2
    assert opened == [f1, f2]


def test_cli_dry_run(monkeypatch, tdir: Path, capsys):
    import createcollection as cc

    a = tdir / "MyFont-Regular.ttf"
    b = tdir / "MyFont-Bold.ttf"
    for p in (a, b):
        write_header(p, b"\x00\x01\x00\x00")

    # Avoid fonttools dependency in sorting and name derivation
    monkeypatch.setattr(cc, "read_family_and_subfamily", lambda p: (None, None))
    monkeypatch.setattr(cc, "read_weight_and_italic", lambda p: (400, False))

    rc = cc.main([str(tdir), "--dry-run", "--name", "MyFont"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "type=ttc" in out
    assert "MyFont" in out
