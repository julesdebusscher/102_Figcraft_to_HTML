"""Export FigCraft frames to a standalone HTML prototype (stdlib only, Python >= 3.8)."""

MIN_VERSION = (0, 18, 1)


def parse_version(text):
    """'0.19.0-alpha' -> (0, 19, 0); '1.0' -> (1, 0, 0); None if unreadable."""
    import re

    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", str(text or ""))
    if not m:
        return None
    return tuple(int(g) if g else 0 for g in m.groups())


def version_ok(version_str):
    """True when the version is at least 0.18.1."""
    v = parse_version(version_str)
    return v is not None and v >= MIN_VERSION
