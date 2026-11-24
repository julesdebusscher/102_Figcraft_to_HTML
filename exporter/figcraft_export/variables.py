"""Variables: the contract `variables`, which values/modes are reachable, and per-layer alternatives.

`read(ctl)` -> contract variables. `reachable(variables, actions)` -> what the prototype's
actions can set. `alternatives(...)` -> the "when" conditions a layer with bound colours must
be pre-rendered for. `add_jobs(walked, variables, reach)` wires them into the walk's jobs.
"""
import re

from .interactions import css_rgba

CAP = 32
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_TYPES = {"color": "color", "colour": "color", "float": "number", "number": "number",
          "string": "string", "boolean": "boolean", "bool": "boolean"}


def _num(v):
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def norm_colour(v):
    """{r,g,b,a} (0..1) or '#RRGGBB' -> css 'rgba(...)'; anything else unchanged."""
    if isinstance(v, dict) and "r" in v:
        return css_rgba(v)
    if isinstance(v, str) and _HEX.match(v):
        return "rgba(%d, %d, %d, 1)" % (int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16))
    return v


def _value(vtype, entry):
    v = entry.get("value") if isinstance(entry, dict) and "value" in entry else entry
    return norm_colour(v) if vtype == "color" else _num(v)


def parse(raw):
    """variable.list reply -> {"collections": {...}, "vars": {...}} (contract). The default
    mode of a collection is its first mode."""
    colls, vs = {}, {}
    for c in (raw or {}).get("collections") or []:
        modes = c.get("modes") or []
        colls[str(c.get("id"))] = {"name": c.get("name", ""),
                                   "defaultMode": str(modes[0]["id"]) if modes else None,
                                   "modes": {str(m["id"]): m.get("name", "") for m in modes}}
    for v in (raw or {}).get("variables") or []:
        t = _TYPES.get(str(v.get("resolvedType", "")).lower(), str(v.get("resolvedType", "")).lower())
        vs[str(v.get("id"))] = {"name": v.get("name", ""), "collection": str(v.get("collection")), "type": t,
                                "valuesByMode": {str(m): _value(t, e) for m, e in (v.get("values") or {}).items()}}
    return {"collections": colls, "vars": vs}


def read(ctl):
    return parse(ctl.execute("variable.list", {}))


def _default(variables, var):
    d = variables["vars"][var]
    coll = variables["collections"].get(d["collection"]) or {}
    return d["valuesByMode"].get(coll.get("defaultMode"))


def reachable(variables, actions):
    """{"modes": {coll: [mode]}, "values": {var: [value]}, "open": [var], "set": {var: [literal]},
    "types": {var: type}, "collection": {var: coll}}.
    Defaults always come first; `values` = default + literals set by setVariable; `open` =
    variables also written by an expression (their results are unknown)."""
    colls, vs = variables["collections"], variables["vars"]
    modes = {c: [d["defaultMode"]] for c, d in colls.items()}
    values = {v: [_default(variables, v)] for v in vs}
    sets, opened = {}, []
    for a in actions or []:
        if a.get("type") == "setVariableMode":
            c, m = a.get("collection"), a.get("mode")
            if c in colls and m in colls[c]["modes"] and m not in modes[c]:
                modes[c].append(m)
        elif a.get("type") == "setVariable" and a.get("variable") in vs:
            v = a["variable"]
            if a.get("expr") is not None:
                if v not in opened:
                    opened.append(v)
                continue
            lit = norm_colour(a.get("value")) if vs[v]["type"] == "color" else a.get("value")
            if lit not in sets.setdefault(v, []):
                sets[v].append(lit)
            if lit not in values[v]:
                values[v].append(lit)
    return {"modes": modes, "values": values, "open": opened, "set": sets,
            "types": {v: d["type"] for v, d in vs.items()},
            "collection": {v: d["collection"] for v, d in vs.items()}}


def colour_vars(bound_vars, reach):
    """Ids of the colour variables among a node's bound variables (the only ones that change a paint)."""
    out = []
    for v in (bound_vars or {}).values():
        if reach["types"].get(v) == "color" and v not in out:
            out.append(v)
    return out


def alternatives(bound_vars, modes_used, reach, cap=CAP):
    """Pre-render conditions for a layer: ([When], capped). `modes_used`: the collections whose
    mode may vary for this layer (not pinned by a frame). The all-default combination is the
    layer's main paint and is not listed. Most specific condition first (the player takes the
    first match); when capped, the combinations with the fewest non-default choices are kept."""
    cvars = colour_vars(bound_vars, reach)
    dims = []  # [(kind, key, [choices])] choice None = default
    for c in modes_used:
        ms = reach["modes"].get(c) or []
        if len(ms) > 1 and any(reach["collection"].get(v) == c for v in cvars):
            dims.append(("mode", c, [None] + list(ms[1:])))
    for v in cvars:
        lits = reach["set"].get(v) or []
        if lits:
            dims.append(("var", v, [None] + list(lits)))
    combos = [[]]
    for _, _, ch in dims:
        combos = [c + [x] for c in combos for x in ch]
    combos = [c for c in combos if any(x is not None for x in c)]
    combos.sort(key=lambda c: (sum(x is not None for x in c), [x is None for x in c]))  # simplest first, modes before values
    whens, seen = [], set()
    for c in combos:
        pick = {(k, key): x for (k, key, _), x in zip(dims, c) if x is not None}
        vars_ = {key: x for (k, key), x in pick.items() if k == "var"}
        modes = {}
        for (k, key), x in pick.items():
            if k == "mode" and not all(v in vars_ for v in cvars if reach["collection"].get(v) == key):
                modes[key] = x  # an overridden var ignores the mode
        w = {}
        if vars_:
            w["vars"] = vars_
        if modes:
            w["modes"] = modes
        sig = repr((sorted(vars_.items(), key=repr), sorted(modes.items())))
        if w and sig not in seen:
            seen.add(sig)
            whens.append(w)
    capped = len(whens) > cap
    whens = whens[:cap]
    whens.sort(key=lambda w: -(len(w.get("vars", {})) + len(w.get("modes", {}))))
    return whens, capped


def _pinned(walked, nid):
    out, cur, guard = {}, nid, 0
    parent = walked.get("parent") or {}
    while cur is not None and guard < 10000:
        guard += 1
        for c, m in (walked.get("explicit_modes", {}).get(cur) or {}).items():
            out.setdefault(c, m)
        cur = parent.get(cur)
    return out


def _normalise_actions(variables, actions):
    for a in actions or []:
        if a.get("type") == "setVariable" and a.get("expr") is None:
            d = variables["vars"].get(a.get("variable"))
            if d and d["type"] == "color":
                a["value"] = norm_colour(a.get("value"))


def add_jobs(walked, variables, reach, cap=CAP):
    """Fills proto["variables"], appends "mode"/"varValue" jobs to walked["jobs"] and writes the
    "when" placeholders (paint None) of node["alts"] for every node with an own job."""
    proto, nodes = walked["proto"], walked["proto"]["nodes"]
    proto["variables"] = variables
    _normalise_actions(variables, walked.get("actions"))
    warn = walked["warnings"]
    new_jobs, open_seen = [], []
    for job in list(walked["jobs"]):
        if job.get("kind") != "own":
            continue
        nid = job["node"]
        bound = (walked.get("bound") or {}).get(nid) or {}
        if not bound:
            continue
        pinned = _pinned(walked, nid)
        if pinned:
            job["pinned_modes"] = dict(pinned)
        for v in colour_vars(bound, reach):
            if v in reach["open"] and v not in open_seen:
                open_seen.append(v)
                warn.append("La variable « %s » change par une expression : seules ses valeurs connues sont pré-rendues."
                            % variables["vars"][v]["name"])
        used = [c for c in reach["modes"] if c not in pinned]
        whens, capped = alternatives(bound, used, reach, cap)
        if capped:
            warn.append("… alternatives limitées à %d pour le calque « %s » : rendu approximé."
                        % (cap, nodes[nid]["name"]))
        nodes[nid]["alts"] = [{"when": w, "paint": None} for w in whens]
        for i, w in enumerate(whens):
            j = {k: val for k, val in job.items() if k not in ("kind", "pinned_modes")}
            j["alt"] = i
            j["when"] = w
            j["modes"] = dict(w.get("modes", {}))
            j["vars"] = dict(w.get("vars", {}))
            if pinned:
                j["pinned_modes"] = dict(pinned)
            if w.get("vars"):
                k = sorted(w["vars"])[0]
                j.update({"kind": "varValue", "var": k, "value": w["vars"][k]})
            else:
                k = sorted(w["modes"])[0]
                j.update({"kind": "mode", "collection": k, "mode": w["modes"][k]})
            new_jobs.append(j)
    walked["jobs"].extend(new_jobs)
