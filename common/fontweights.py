from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import sys

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except Exception as e:  # pragma: no cover - repo targets 3.12
    raise RuntimeError("Python >= 3.11 required for tomllib; upgrade your interpreter.") from e


def _normalize_phrase(s: str) -> str:
    """Normalize a weight phrase for case-insensitive, hyphen/space-insensitive matching.

    Rules: lowercase, split on whitespace and hyphens, join with single spaces.
    """
    import re

    if not isinstance(s, str):
        return ""
    parts = [t for t in re.split(r"[\s\-]+", s.strip().lower()) if t]
    return " ".join(parts)


@dataclass(frozen=True)
class FontWeights:
    canonical_to_value: Dict[str, int]
    normalized_to_canonical: Dict[str, str]

    @property
    def known_phrases(self) -> set[str]:
        return set(self.normalized_to_canonical.keys())


def load_config(path: Path | None = None) -> FontWeights:
    """Load `fontweights.toml` and return a FontWeights mapping.

    - When `path` is None, reads from CWD / 'fontweights.toml'.
    - Raises RuntimeError on missing file, parse errors, or invalid schema.
    """
    config_path = Path(path) if path is not None else Path.cwd() / "fontweights.toml"
    if not config_path.exists():
        raise RuntimeError(f"fontweights.toml not found at {config_path}")
    try:
        data = tomllib.loads(config_path.read_text("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Invalid fontweights.toml: {e}") from e

    weights_raw = data.get("weights")
    if not isinstance(weights_raw, dict) or not weights_raw:
        raise RuntimeError("fontweights.toml must define a non-empty [weights] table")

    canonical_to_value: Dict[str, int] = {}
    for name, val in weights_raw.items():
        if not isinstance(name, str):
            raise RuntimeError("[weights] keys must be strings")
        if not isinstance(val, int):
            raise RuntimeError(f"[weights].{name} must be an integer numeric weight (100..900)")
        canonical_to_value[name] = int(val)

    normalized_to_canonical: Dict[str, str] = {}
    # Map canonical names to themselves
    for canon in canonical_to_value.keys():
        normalized_to_canonical[_normalize_phrase(canon)] = canon

    # Apply aliases (optional)
    aliases_raw = data.get("aliases", {})
    if aliases_raw:
        if not isinstance(aliases_raw, dict):
            raise RuntimeError("[aliases] must be a table of alias -> canonical name")
        for alias, canon in aliases_raw.items():
            if not isinstance(alias, str) or not isinstance(canon, str):
                print("WARN: alias entries must be strings; ignoring one entry", file=sys.stderr)
                continue
            norm_alias = _normalize_phrase(alias)
            if canon not in canonical_to_value:
                print(f"WARN: alias '{alias}' refers to unknown canonical '{canon}'; ignoring", file=sys.stderr)
                continue
            normalized_to_canonical[norm_alias] = canon

    return FontWeights(canonical_to_value=canonical_to_value, normalized_to_canonical=normalized_to_canonical)


def standard_weights(cfg: FontWeights) -> List[Tuple[int, str]]:
    """Return [(value, canonical_name), ...] sorted by value asc, then name."""
    items = [(v, k) for k, v in cfg.canonical_to_value.items()]
    items.sort(key=lambda t: (t[0], t[1]))
    return items


def lookup_value(cfg: FontWeights, phrase: str) -> int | None:
    """Return numeric weight for a phrase via canonical or alias, else None."""
    canon = canonical_name_for(cfg, phrase)
    if canon is None:
        return None
    return cfg.canonical_to_value.get(canon)


def canonical_name_for(cfg: FontWeights, phrase: str) -> str | None:
    norm = _normalize_phrase(phrase)
    return cfg.normalized_to_canonical.get(norm)

