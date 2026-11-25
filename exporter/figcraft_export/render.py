"""Paints: renders every RenderJob over control, inside temporary edits that are always undone.

Per job, one batched edit (`command.batch` = one undo step): unhide the hidden chain, hide the
children, drop CSS-drawn effects / blend / opacity, set rotation 0 on the node and its rotated
ancestors (paints are drawn unrotated), apply the alt's variable modes and values. Then
`file.export` and one `edit.undo`. Non-current variants: switch the instance, build and render
its "<inst>~<key>~..." nodes, undo the switch.

Paint offsets: the normal SVG export covers what the layer paints (shadows, outside strokes);
the `includeBoundingBox` export is exactly the layer box. Both draw the same elements, so the
difference of their first `transform="matrix(...)"` translation is the box's place in the image.
"""
import base64
import hashlib
import re
from collections import deque

from . import variables, walk
from .edits import BATCH_LABEL, UNDO_FAILED, EditSession, RenderError  # noqa: F401 (re-exported)
from .summary import NO_REDO, steps_left
from .style import effects_css, num

_PNG_EFFECTS = ("layerBlur", "noise", "texture", "glass", "backgroundBlur")
_FIELDS = ["type", "effects", "fills", "strokes", "rotation", "opacity", "blend", "sizing", "fontSize", "isMask"]
_DEFS = re.compile(r"<defs\b.*?</defs>", re.S)
_DRAW = re.compile(r"<(path|rect|circle|ellipse|line|polyline|polygon|image|text|use)\b")
_MATRIX = re.compile(r'transform="matrix\(([^)]*)\)"')
_SIZE = re.compile(r'<svg\b[^>]*?\bwidth="([-\d.e]+)"[^>]*?\bheight="([-\d.e]+)"')


def sanitise(node_id):
    """Asset file name part: layer ids only, every other character becomes "_"."""
    return re.sub(r"[^A-Za-z0-9_~-]", "_", str(node_id))


class _UnknownVariable(Exception):
    pass


def _svg_text(data):
    return data.decode("utf-8", "replace")


def _draws(svg):
    return bool(_DRAW.search(_DEFS.sub("", svg)))


def _origin(svg):
    m = _MATRIX.search(_DEFS.sub("", svg))
    if not m:
        return None
    parts = [float(v) for v in re.split(r"[\s,]+", m.group(1).strip())]
    return (parts[4], parts[5]) if len(parts) == 6 else None


def _size(svg):
    m = _SIZE.search(svg)
    return (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)


def _pad(svg, m):
    """Widen an SVG by m px on every side (text glyphs may overflow the text box, and FigCraft
    exports a text layer at its box)."""
    w, h = _size(svg)
    vb = re.search(r'viewBox="([^"]*)"', svg)
    a, b, c, d = [float(v) for v in re.split(r"[\s,]+", vb.group(1).strip())] if vb else (0, 0, w, h)
    sx, sy = (c / w if w else 1), (d / h if h else 1)
    head = '<svg width="%g" height="%g" viewBox="%g %g %g %g"' % (w + 2 * m, h + 2 * m, a - m * sx, b - m * sy,
                                                                  c + 2 * m * sx, d + 2 * m * sy)
    tag_end = svg.index(">")
    rest = re.sub(r'\s(width|height|viewBox)="[^"]*"', "", svg[4:tag_end])
    return head + rest + svg[tag_end:]


def _raster_paint(f):
    """Images and gradients go to PNG: FigCraft's SVG writes gradients in user space, which
    turns their angle on non-square layers."""
    return f.get("visible", True) is not False and (
        f.get("type") in ("image", "video", "gradient") or "image" in f or "Gradient" in str(f.get("type")))


def _r(v):
    return num(round(v, 3) + 0.0)  # + 0.0: no "-0"


class _CloneWalker(walk._Walker):
    """The walk's node rules for a switched instance's subtree, ids "<inst>~<key>~<childId>"."""

    def __init__(self, ctl, prefix, inst_id, inst_fc, var_types, extras):
        walk._Walker.__init__(self, ctl, extras)
        self.prefix, self.alias, self.var_types = prefix, {inst_fc: inst_id}, var_types
        self.inst_links[inst_id] = []

    def enqueue(self, dest, source):
        pass  # screens reached through variants were already followed by the walk


class _Renderer(object):
    def __init__(self, ctl, walked, scale):
        self.ctl, self.w, self.scale = ctl, walked, scale
        self.proto = walked["proto"]
        self.nodes = self.proto["nodes"]
        self.assets, self.by_hash, self.taken = [], {}, set()
        self.fc = {}
        self.reach = None
        self.var_types = {v.get("id"): v.get("resolvedType")
                          for v in (walked.get("variables_raw") or {}).get("variables") or []}
        self.stats = {"jobs": 0, "exports": 0, "edits": 0}
        self.dropped = set()   # (node, alt index) that could not be rendered

    # -- helpers -------------------------------------------------------------
    def _approx(self, msg):
        lst = self.proto.setdefault("report", {}).setdefault("approximated", [])
        if msg not in lst:
            lst.append(msg)

    def _warn(self, msg, skipped=True):
        if msg not in self.w.setdefault("warnings", []):
            self.w["warnings"].append(msg)
        lst = self.proto.setdefault("report", {}).setdefault("skipped", [])
        if skipped and msg not in lst:
            lst.append(msg)

    def fc_of(self, nid):
        if nid in self.fc:
            return self.fc[nid]
        last = str(nid).split("~")[-1]
        return int(last) if last.isdigit() else None

    def _export(self, fc, fmt, **extra):
        params = {"ids": [fc], "format": fmt}
        params.update(extra)
        self.stats["exports"] += 1
        reply = self.ctl.execute("file.export", params) or {}
        return base64.b64decode(reply.get("data") or "")

    def _store(self, nid, alt, ext, data):
        digest = hashlib.sha256(data).hexdigest()
        if digest in self.by_hash:
            return self.by_hash[digest]
        base = "assets/" + sanitise(nid) + ("__alt%d" % alt if alt is not None else "")
        path, n = base + "." + ext, 2
        while path in self.taken:
            path, n = "%s_%d.%s" % (base, n, ext), n + 1
        self.taken.add(path)
        self.by_hash[digest] = path
        self.assets.append({"path": path, "data": data})
        return path

    def _rotated(self, nid, fc, own_rotation):
        ids = [fc] if own_rotation else []
        parent = self.w.get("parent") or {}
        cur, guard = parent.get(nid), 0
        while cur is not None and guard < 10000:
            guard += 1
            n = self.nodes.get(cur)
            f = self.fc_of(cur)
            if n and n.get("rotation") and f is not None and f not in ids:
                ids.append(f)
            cur = parent.get(cur)
        return ids

    def _mode_target(self, nid):
        screen = (self.w.get("screen_of") or {}).get(nid)
        f = self.fc_of(screen) if screen is not None else None
        if f is None:
            f = int(self.w["page_id"])
        return f

    def _var_edits(self, job, nid):
        edits = []
        modes = job.get("modes") or {}
        if modes:
            target = self._mode_target(nid)
            for c in sorted(modes):
                edits.append(("variable.setMode", {"ids": [target], "collection": c, "mode": modes[c]}))
        vs = self.proto.get("variables") or {}
        for v in sorted(job.get("vars") or {}):
            coll = (vs.get("collections") or {}).get(((vs.get("vars") or {}).get(v) or {}).get("collection")) or {}
            if not coll.get("modes"):
                raise _UnknownVariable(v)
            for m in coll["modes"]:
                edits.append(("variable.set", {"variable": v, "mode": m, "value": job["vars"][v]}))
        return edits

    # -- jobs ----------------------------------------------------------------
    def run(self, job):
        if job.get("kind") == "variant":
            self._variant(job)
        else:
            self._paint_job(job)

    def _paint_job(self, job):
        nid, fc = job["node"], job["fc_id"]
        self.fc.setdefault(nid, fc)
        self.stats["jobs"] += 1
        info = self.ctl.execute("node.get", {"id": fc, "fields": _FIELDS}) or {}
        edits = []
        if job.get("unhide"):
            edits.append(("node.set", {"ids": list(job["unhide"]), "props": {"visible": True}}))
        if job.get("hide_children"):
            kids = (self.ctl.execute("node.get", {"id": fc, "outline": True}) or {}).get("children") or []
            shown = [k["id"] for k in kids if k.get("visible", True) is not False]
            hug = {("sizingH" if a == "horizontal" else "sizingV"): "fixed"
                   for a, v in (info.get("sizing") or {}).items() if v == "hug"}
            if hug and shown:  # auto layout "hug" would shrink once the children are hidden: freeze first
                edits.append(("node.set", {"ids": [fc], "props": hug}))
            if shown:
                edits.append(("node.set", {"ids": shown, "props": {"visible": False}}))
        strip = job.get("strip_effects") or []
        effects = info.get("effects") or []
        kept = [e for e in effects if e.get("type") not in strip]
        props = {}
        if len(kept) != len(effects):
            props["effects"] = kept
        if "blend" in strip:
            props["blend"] = "normal"
        if "opacity" in strip:
            props["opacity"] = 1
        if info.get("isMask"):
            props["isMask"] = False  # a mask layer draws nothing; its shape becomes css.maskSrc
        if props:
            edits.append(("node.set", {"ids": [fc], "props": props}))
        rot = self._rotated(nid, fc, info.get("rotation"))
        if rot:
            edits.append(("node.set", {"ids": rot, "props": {"rotation": 0}}))
        try:
            edits += self._var_edits(job, nid)
        except _UnknownVariable as e:   # this alternative can't be made: dropped from alts
            self._warn("Variable %s de collection inconnue : alternative ignorée pour « %s »."
                       % (e, self.nodes[nid]["name"]))
            self.dropped.add((nid, job["alt"]))
            return
        png = any(e.get("type") in _PNG_EFFECTS and e.get("visible", True) for e in kept) or any(
            _raster_paint(f) for f in (info.get("fills") or []) + (info.get("strokes") or []))
        self.stats["edits"] += 1 if edits else 0
        with EditSession(self.ctl) as s:
            s.batch(edits)
            paint = self._paint(nid, fc, job.get("alt"), png, info)
        if job.get("alt") is not None:
            self.nodes[nid]["alts"][job["alt"]]["paint"] = paint
        else:
            self.nodes[nid]["paint"] = paint
            if job.get("mask_for") and paint and job["mask_for"] in self.nodes:
                # the mask layer is drawn by no parent: its paint becomes the group's mask image,
                # placed at the mask layer's box in the group plus the paint's offset
                n = self.nodes[nid]
                self.nodes[job["mask_for"]]["css"].update({
                    "maskSrc": paint["src"],
                    "maskBox": [_r(n["x"] + paint["dx"]), _r(n["y"] + paint["dy"]), paint["w"], paint["h"]]})
                n["paint"] = None

    def _paint(self, nid, fc, alt, png, info):
        svg = self._export(fc, "svg")
        text = _svg_text(svg)
        if not _draws(text):
            return None
        box = _origin(_svg_text(self._export(fc, "svg", includeBoundingBox=True)))
        own = _origin(text)
        dx, dy = (box[0] - own[0], box[1] - own[1]) if box and own else (0.0, 0.0)
        if not (box and own):
            self._approx("« %s » : position du rendu inconnue (approximation)" % self.nodes[nid]["name"])
        w, h = _size(text)
        if png:
            src = self._store(nid, alt, "png", self._export(fc, "png", scale=self.scale))
        else:
            if info.get("type") == "TEXT":
                m = max(4.0, float(info.get("fontSize") or 0) / 2)
                text, dx, dy, w, h = _pad(text, m), dx - m, dy - m, w + 2 * m, h + 2 * m
                svg = text.encode("utf-8")
            src = self._store(nid, alt, "svg", svg)
        return {"src": src, "dx": _r(dx), "dy": _r(dy), "w": _r(w), "h": _r(h)}

    def _variant(self, job):
        inst, key, fc = job["instance"], job["variant"], job["fc_id"]
        prefix = "%s~%s~" % (inst, key)
        hidden = list(job.get("unhide") or [])
        with EditSession(self.ctl) as s:
            s.apply("instance.setProperties", {"ids": [fc], "properties": job["properties"]})
            self.stats["edits"] += 1
            raw = self.ctl.execute("node.get", {"id": fc}) or {}
            vw = _CloneWalker(self.ctl, prefix, inst, fc, self.var_types, self.w.get("extras"))
            screen = (self.w.get("screen_of") or {}).get(inst)
            if raw.get("boundVariables"):
                vw.bound[inst] = dict(raw["boundVariables"])
            tmp = {"id": inst, "name": raw.get("name", ""), "w": num(raw.get("width", 0)),
                   "h": num(raw.get("height", 0)), "children": []}
            sid = vw._self_node(raw, tmp, key, screen)
            vw.bound.pop(inst, None)
            _, strip, _ = effects_css(raw, True)
            if raw.get("opacity", 1) < 1:
                strip.append("opacity")
            sjob = {"node": sid, "fc_id": fc, "kind": "own", "hide_children": True, "strip_effects": strip}
            if hidden:
                sjob["unhide"] = list(hidden)
            kids = [c for c in vw._children(raw) if c.get("type") not in walk._SKIP_TYPES]
            todo = deque((c, raw, inst, list(hidden)) for c in kids)
            while todo:
                todo.extend(vw._node(*(todo.popleft() + (screen,)))[0])
            vw._finish_instances()
            self.nodes.update(vw.nodes)
            for name, attr in (("parent", "parent"), ("screen_of", "screen_of"), ("bound", "bound"),
                               ("explicit_modes", "modes")):
                self.w.setdefault(name, {}).update(getattr(vw, attr))
            self.nodes[inst]["instance"]["variants"][key] = [sid] + [vw._id(c["id"]) for c in kids]
            report = self.proto.setdefault("report", {"approximated": [], "skipped": []})
            for key, msgs in (("approximated", vw.approx), ("skipped", vw.skipped)):
                for m in msgs:
                    if m not in report.setdefault(key, []):
                        report[key].append(m)
            for m in vw.warnings:
                self._warn(m, skipped=False)
            jobs = [sjob] + vw.jobs
            jobs += self._alt_jobs([j for j in jobs if j["kind"] == "own"], vw.bound)
            for j in jobs:
                self.run(j)

    def _alt_jobs(self, own_jobs, bound):
        """Task 8's alternatives for the clone nodes (their colours may be bound too)."""
        vs = self.proto.get("variables") or {}
        if not bound or not vs.get("vars"):
            return []
        if self.reach is None:
            self.reach = variables.reachable(vs, self.w.get("actions"))
        mini = {"proto": self.proto, "jobs": list(own_jobs), "bound": bound, "parent": self.w.get("parent") or {},
                "explicit_modes": self.w.get("explicit_modes") or {}, "warnings": [], "actions": [],
                "screen_of": self.w.get("screen_of") or {}, "page_modes": self.w.get("page_modes") or {}}
        variables.add_jobs(mini, vs, self.reach)
        warnings = self.w.setdefault("warnings", [])
        for m in mini["warnings"]:
            if m not in warnings:
                warnings.append(m)
        return mini["jobs"][len(own_jobs):]


def _screen_fc(walked):
    """FigCraft id of a top-level frame we rendered (a screen), or None."""
    parent = walked.get("parent") or {}
    for j in walked["jobs"]:
        if j.get("kind") == "own" and parent.get(j["node"], 0) is None:
            return j["fc_id"]
    return None


def _clear_redo(ctl, walked, baseline):
    """Our undone steps sit on FigCraft's redo stack: Cmd/Ctrl+Maj+Z would re-apply the last one.
    When the history is back at the run's baseline, one labelled no-op batch (`visible: true` on a
    visible screen) clears the redo stack, and its undo leaves only that no-op there (redoing it
    changes nothing). Never fails the export: a problem becomes a remark."""
    warnings = walked.setdefault("warnings", [])
    try:
        top, depth, redo, _ = EditSession(ctl)._hist()
        if baseline is None or (top, depth) != tuple(baseline) or not redo:
            return
        fc = _screen_fc(walked)
        info = ctl.execute("node.get", {"id": fc, "fields": ["visible"]}) if fc is not None else None
        if not isinstance(info, dict) or info.get("visible", True) is False:
            raise ValueError("no visible screen")
        with EditSession(ctl) as s:
            s.batch([("node.set", {"ids": [fc], "props": {"visible": True}})], final=True)
    except RenderError as e:
        for m in [str(e)] + ([steps_left(len(e.remaining))] if e.remaining and not e.user_undone else []):
            if m not in warnings:
                warnings.append(m)
    except Exception:
        if NO_REDO not in warnings:
            warnings.append(NO_REDO)


def render_all(ctl, walked, scale=2):
    """Render every job of `walked` (after variables.add_jobs). Fills `paint`, `alts[i].paint`
    and `css.maskSrc`/`css.maskBox` in walked["proto"]["nodes"], adds the non-current variants' nodes
    ("<inst>~<key>~...") and sets `instance.variants[key]`. Returns [Asset] =
    [{"path": "assets/<sanitised id>[__alt<i>].svg|png", "data": bytes}], one per distinct
    content. Every temporary edit is undone before returning or raising; RenderError (French)
    when an undo failed. `walked["render_stats"]` = {"jobs", "exports", "edits"}. Afterwards the
    redo stack holds no temporary step of ours (see _clear_redo)."""
    r = _Renderer(ctl, walked, scale)
    try:
        baseline = EditSession(ctl)._hist()[:2] if walked["jobs"] else None
    except Exception:
        baseline = None
    for job in list(walked["jobs"]):
        r.run(job)
    _clear_redo(ctl, walked, baseline)
    for nid in sorted(set(n for n, _ in r.dropped)):
        alts = r.nodes[nid]["alts"]
        r.nodes[nid]["alts"] = [a for i, a in enumerate(alts) if (nid, i) not in r.dropped]
    walked["render_stats"] = r.stats
    return r.assets
