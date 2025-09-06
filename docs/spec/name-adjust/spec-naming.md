Collection Naming Playbook
===

## 1) Name table hygiene (so apps group styles correctly)

Change these consistently across all members:

* **ID 16 (Typographic Family)** → shared family name (e.g., `MyFamily`)
* **ID 17 (Typographic Subfamily)** → precise style (e.g., `Regular`, `SemiBold`, `Black Italic`)
* **ID 1 (Legacy Family)** → use for the *4-style* legacy group only (`MyFamily`)

  * If you have >4 styles (Thin…Black), keep **ID 1** as `MyFamily` for everyone, and rely on **ID 16/17** + **STAT** (modern) for grouping.
* **ID 2 (Subfamily)** → style keyword used by legacy apps (`Regular`, `Bold`, `Italic`, `Bold Italic`, `Light`, etc.)
* **ID 4 (Full name)** → `MyFamily Style` (e.g., `MyFamily SemiBold Italic`)
* **ID 6 (PostScript name)** → ASCII, no spaces, `MyFamily-SemiBoldItalic`
* Provide Windows/Unicode name records (platform 3, enc 1, lang 0x409) at minimum.

Tip: Pick one naming vocabulary and stick to it (`SemiBold` *or* `DemiBold`, not both).

## 2) Weight/width/italic flags (so bold/italic work everywhere)

* **OS/2.usWeightClass**: 100–900 to match the style (e.g., SemiBold=600, Bold=700).
* **OS/2.usWidthClass**: 1–9 (Ultra-Condensed…Ultra-Expanded) if you have widths.
* **OS/2.fsSelection** bits:

  * **ITALIC** set for italic styles
  * **BOLD** set *only* for “Bold” styles
  * **REGULAR** set only on the “Regular” upright
* **head.macStyle** bits must match (Bold / Italic) for legacy apps.

## 3) Modern family grouping (strongly recommended)

* Add a **STAT** table (even for static fonts). Define a **Weight** axis (and **Width/Slope** if used) and AxisValue records per style. This is how modern OSes/apps group large families cleanly.
* For variable fonts: also set **name ID 25** (Variations PS Name Prefix).

## 4) Uniqueness (avoid cache collisions)

* **Name ID 6** (PS name) and **Name ID 3** (Unique ID) must be unique per face.
* Keep **Version** (ID 5 & `head.fontRevision`) in sync across family releases.

## 5) Glyph/feature consistency (nice-to-have for collections)

* It’s fine if coverage differs, but avoid accidental regressions (e.g., one weight missing ₱ or diacritics).
* Keep OpenType features (GSUB/GPOS) naming consistent where applicable.

## 6) When building a TTC/OTC

* Each member’s **name table** is per-font (and will *not* be shared).
* If you use `shareTables=True`, only byte-identical tables get deduped—safe but don’t rely on it.
* Mixed flavors are allowed (TTF/CFF), but keep naming/flags aligned so hosts treat the set as one family.

## 7) Validate

* Run **FontBakery** checks; fix name/OS/2/STAT violations before shipping.
* Clear OS/app font caches after changes when testing.

---

## Example: normalize names & flags with `fonttools`

This script rewrites the key IDs and flags to make members “collection-ready,” then saves a `.ttc`.

```python
from fontTools.ttLib import TTFont
from fontTools.ttLib.ttCollection import TTCollection

def set_name(name_table, name_id, text, langID=0x409):
    # Ensure Windows Unicode record exists and is updated
    for rec in list(name_table.names):
        if rec.nameID == name_id and rec.platformID == 3 and rec.platEncID == 1 and rec.langID == langID:
            rec.string = text.encode(rec.getEncoding())
            break
    else:
        name_table.setName(text, name_id, 3, 1, langID)

def normalize_font(path, family, style, weight, italic=False, width_class=5, ps_family=None, vendor_id="XXXX"):
    font = TTFont(path)
    name = font["name"]

    # Family & style
    set_name(name, 16, family)                 # Typographic Family
    set_name(name, 17, style)                  # Typographic Subfamily
    set_name(name, 1, family)                  # Legacy Family
    set_name(name, 2, style)                   # Legacy Subfamily
    set_name(name, 4, f"{family} {style}")     # Full name

    # PostScript name (ASCII, no spaces)
    psfam = (ps_family or family).replace(" ", "")
    psstyle = style.replace(" ", "")
    set_name(name, 6, f"{psfam}-{psstyle}")

    # OS/2 metrics & style linking
    os2 = font["OS/2"]
    os2.usWeightClass = int(weight)
    os2.usWidthClass = int(width_class)

    # fsSelection bits: 0=ITALIC, 5=BOLD, 6=REGULAR
    fs = os2.fsSelection
    def set_bit(value, bit, on): 
        return (value | (1 << bit)) if on else (value & ~(1 << bit))

    is_bold_style = "Bold" in style  # be strict—don’t treat Medium/600 as bold
    is_regular_upright = (style == "Regular") and not italic

    fs = set_bit(fs, 0, italic)
    fs = set_bit(fs, 5, is_bold_style)
    fs = set_bit(fs, 6, is_regular_upright)
    os2.fsSelection = fs

    # head macStyle bits: 0=Bold, 1=Italic
    head = font["head"]
    mac = head.macStyle
    mac = set_bit(mac, 0, is_bold_style)
    mac = set_bit(mac, 1, italic)
    head.macStyle = mac

    # Optional: vendor ID
    if hasattr(os2, "achVendID") and vendor_id and len(vendor_id) == 4:
        os2.achVendID = vendor_id

    return font

# Example usage (edit paths & styles to your family)
members = [
    normalize_font("MyFamily-Regular.ttf",        "MyFamily", "Regular",        400, italic=False),
    normalize_font("MyFamily-Italic.ttf",         "MyFamily", "Italic",         400, italic=True),
    normalize_font("MyFamily-Bold.ttf",           "MyFamily", "Bold",           700, italic=False),
    normalize_font("MyFamily-BoldItalic.ttf",     "MyFamily", "Bold Italic",    700, italic=True),
    normalize_font("MyFamily-SemiBold.ttf",       "MyFamily", "SemiBold",       600, italic=False),
    normalize_font("MyFamily-SemiBoldItalic.ttf", "MyFamily", "SemiBold Italic",600, italic=True),
]

# Save TTC (tables auto-deduped where identical)
ttc = TTCollection()
ttc.fonts = members
ttc.save("MyFamily.ttc", shareTables=True)
```

### TL;DR checklist

* ✅ IDs 16/17/1/2/4/6 aligned and unique
* ✅ `usWeightClass`, `fsSelection`, `macStyle` set correctly
* ✅ Consider a `STAT` table for clean grouping (especially >4 styles)
* ✅ Unique `nameID 3` & `6` per face
* ✅ Validate with FontBakery; clear caches when testing

