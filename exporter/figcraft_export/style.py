"""Node styling read from node.get: css colours, live-text style, CSS-handled effects."""
import re

_WEIGHTS = [("thin", 100), ("extralight", 200), ("ultralight", 200), ("light", 300),
            ("semibold", 600), ("demibold", 600), ("extrabold", 800), ("ultrabold", 800),
            ("medium", 500), ("bold", 700), ("black", 900), ("heavy", 900)]


def num(v):
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def css_color(fill):
    """A node.get solid fill ({color:"#RRGGBB", opacity?}) -> css colour."""
    c = str(fill.get("color") or "#000000")
    op = fill.get("opacity", 1)
    if op is None or op >= 1 or not re.match(r"^#[0-9A-Fa-f]{6}$", c):
        return c
    return "rgba(%d, %d, %d, %g)" % (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), round(op, 3))


def solid(raw):
    for f in raw.get("fills") or []:
        if f.get("type") == "solid" and f.get("visible", True):
            return f
    return None


def _weight(style):
    s = str(style or "").lower().replace(" ", "").replace("-", "").replace("italic", "")
    for name, w in _WEIGHTS:
        if name in s:
            return w
    return 400


def _measure(v, size):
    """'150%' -> size*1.5, '1' / '24px' -> 24, 'Auto' -> None."""
    if v is None or isinstance(v, (int, float)):
        return num(v)
    s = str(v).strip().lower()
    if s in ("", "auto"):
        return None
    try:
        if s.endswith("%"):
            return num(round(float(s[:-1]) * float(size) / 100.0, 3))
        return num(float(s[:-2] if s.endswith("px") else s))
    except ValueError:
        return None


def text_style(raw):
    size = num(raw.get("fontSize", 12))
    fill = solid(raw)
    align = raw.get("textAlign") or "left"
    return {"fontFamily": raw.get("fontFamily") or "", "fontSize": size, "fontWeight": _weight(raw.get("fontStyle")),
            "lineHeight": _measure(raw.get("lineHeight"), size),
            "letterSpacing": _measure(raw.get("letterSpacing"), size) or 0,
            "color": css_color(fill) if fill else "#000000",
            "align": "justify" if align == "justified" else align}


def _blend(b):
    return re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), b)


def effects_css(raw, has_children):
    """-> (css, strip_effects, [approximation labels]); see the RenderJob notes on walk()."""
    css, strip, approx = {}, [], []
    for e in raw.get("effects") or []:
        if not e.get("visible", True):
            continue
        t = e.get("type")
        if t == "backgroundBlur":
            css["backdropBlur"] = num(e.get("radius", 0))
            approx.append("flou d'arrière-plan")
        elif t == "glass":
            css["backdropBlur"] = num(e.get("frost", 0))
            approx.append("effet verre (rendu en flou d'arrière-plan)")
        elif t == "layerBlur" and has_children:
            css["layerBlur"] = num(e.get("radius", 0))
            approx.append("flou de calque")
        else:
            continue
        if t not in strip:
            strip.append(t)
    b = raw.get("blend")
    if b and b not in ("normal", "passThrough"):
        css["blend"] = _blend(b)
        strip.append("blend")
        approx.append("mode de fusion %s" % b)
    r = raw.get("cornerRadius")
    if raw.get("clip") and has_children and r:
        radii = [num(x) for x in (r if isinstance(r, list) else [r] * 4)]
        if any(radii):
            css["radius"] = radii
    return css, strip, approx
