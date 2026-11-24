"""FigCraft interaction JSON (as node.get returns it) -> data.js contract Interaction.

Reply shape (docs/figcraft-api-notes.md §2): {trigger, actions, transition, duration_ms,
easing, delay_ms?} with snake_case keys (close_on_outside, new_tab, preserve_scroll).
"""

TRIGGERS = {
    "onClick": "click", "onHover": "hover", "onPress": "press", "onDrag": "drag",
    "mouseEnter": "mouseEnter", "mouseLeave": "mouseLeave", "mouseDown": "mouseDown",
    "mouseUp": "mouseUp", "afterDelay": "afterDelay", "keyPress": "key",
}
SCREEN_ACTIONS = ("navigate", "openOverlay", "swapOverlay")
DEFAULT_DURATION_MS = 300
DEFAULT_EASING = "easeOut"


def _num(v):
    """Whole floats as ints (800.0 -> 800), others unchanged."""
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def css_rgba(c):
    """{r,g,b,a} in 0..1 -> 'rgba(r, g, b, a)'."""
    def ch(k):
        return int(round(max(0.0, min(1.0, float(c.get(k, 0)))) * 255))
    return "rgba(%d, %d, %d, %g)" % (ch("r"), ch("g"), ch("b"), round(float(c.get("a", 1)), 3))


def easing(spec):
    if spec is None:
        spec = DEFAULT_EASING
    if isinstance(spec, str):
        return {"type": spec}
    if isinstance(spec, dict) and "customBezier" in spec:
        b = spec["customBezier"]
        return {"type": "customBezier", "bezier": [b.get("x1", 0), b.get("y1", 0), b.get("x2", 1), b.get("y2", 1)]}
    if isinstance(spec, dict) and "customSpring" in spec:
        s = spec["customSpring"]
        return {"type": "customSpring",
                "spring": {"mass": s.get("mass", 1), "stiffness": s.get("stiffness", 100), "damping": s.get("damping", 10)}}
    raise ValueError("easing %r" % (spec,))


def _transition(raw):
    t = raw.get("transition") or {"type": "instant"}
    out = {"type": t.get("type", "instant")}
    if t.get("direction"):
        out["direction"] = t["direction"]
    out["durationMs"] = _num(raw.get("duration_ms", raw.get("durationMs", DEFAULT_DURATION_MS)))
    out["easing"] = easing(raw.get("easing"))
    return out


def _trigger(raw):
    t = raw.get("trigger") or {}
    kind = t.get("type")
    if kind not in TRIGGERS:
        raise ValueError(str(kind))
    out = {"type": TRIGGERS[kind]}
    if kind == "afterDelay":
        out["delayMs"] = _num(t.get("ms", 0))
    elif raw.get("delay_ms") is not None or raw.get("delayMs") is not None:
        out["delayMs"] = _num(raw.get("delay_ms", raw.get("delayMs")))
    if t.get("key") is not None:
        out["key"] = t["key"]
    return out


def _pair(v):
    return [_num(v[0]), _num(v[1])]


def _action(a, transition, variant_key):
    kind = a.get("type")
    if kind == "navigate":
        out = {"type": kind, "dest": str(a.get("dest"))}
        if a.get("preserve_scroll", a.get("preserveScroll")):
            out["preserveScroll"] = True
        out["transition"] = transition
        return out
    if kind in ("back", "closeOverlay"):
        return {"type": kind}
    if kind == "scrollTo":
        out = {"type": kind, "dest": str(a.get("dest"))}
        if a.get("offset") is not None:
            out["offset"] = _pair(a["offset"])
        out["transition"] = transition
        return out
    if kind in ("openOverlay", "swapOverlay"):
        out = {"type": kind, "dest": str(a.get("dest")), "position": a.get("position") or "center"}
        if a.get("anchor"):
            out["anchor"] = a["anchor"]
        if a.get("offset") is not None:
            out["offset"] = _pair(a["offset"])
        coo = a.get("close_on_outside", a.get("closeOnClickOutside"))
        out["closeOnClickOutside"] = True if coo is None else bool(coo)
        if a.get("background"):
            bg = a["background"]
            out["background"] = css_rgba(bg) if isinstance(bg, dict) else str(bg)
        out["transition"] = transition
        return out
    if kind == "openUrl":
        nt = a.get("new_tab", a.get("openInNewTab"))
        return {"type": kind, "url": a.get("url", ""), "newTab": True if nt is None else bool(nt)}
    if kind == "changeTo":
        key = variant_key(a.get("dest"))
        if key is None:
            return None  # missing variant: the caller reports it
        return {"type": kind, "variant": key, "transition": transition}
    if kind == "setVariable":
        out = {"type": kind, "variable": a.get("variable")}
        if a.get("expr") is not None:
            out["expr"] = a["expr"]
        else:
            out["value"] = a.get("value")
        return out
    if kind == "setVariableMode":
        return {"type": kind, "collection": a.get("collection"), "mode": a.get("mode")}
    if kind == "conditional":
        blocks = []
        for b in a.get("blocks") or []:
            nb = {}
            if b.get("condition") is not None:
                nb["condition"] = b["condition"]
            nb["actions"] = _actions(b.get("actions"), transition, variant_key)
            blocks.append(nb)
        return {"type": kind, "blocks": blocks}
    raise ValueError(str(kind))


def _actions(actions, transition, variant_key):
    out = (_action(x, transition, variant_key) for x in actions or [])
    return [x for x in out if x is not None]


def convert(raw, variant_key=None):
    """Contract Interaction; raises ValueError (message = the unknown kind) on an unknown
    trigger, action or easing. `variant_key(dest_id) -> VariantKey | None` names changeTo
    targets (default: the id as a string); None drops that changeTo (missing variant)."""
    vk = variant_key or (lambda d: str(d))
    trigger = _trigger(raw)
    transition = _transition(raw)
    return {"trigger": trigger, "actions": _actions(raw.get("actions"), transition, vk)}


def _walk_actions(actions):
    for a in actions or []:
        yield a
        if a.get("type") == "conditional":
            for b in a.get("blocks") or []:
                for x in _walk_actions(b.get("actions")):
                    yield x


def links(raw):
    """Raw destination ids: {"screens": [navigate/overlay dests], "variants": [changeTo dests]}."""
    screens, variants = [], []
    for a in _walk_actions(raw.get("actions")):
        kind = a.get("type")
        if kind in SCREEN_ACTIONS and a.get("dest") is not None:
            screens.append(a["dest"])
        elif kind == "changeTo" and a.get("dest") is not None:
            variants.append(a["dest"])
    return {"screens": screens, "variants": variants}


def flat_actions(interaction):
    """Every contract action of a converted interaction, conditional blocks included."""
    return list(_walk_actions(interaction.get("actions")))
