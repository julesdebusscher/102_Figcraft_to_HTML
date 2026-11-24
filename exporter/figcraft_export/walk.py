"""Selection -> screens, panel, start, transitive closure and contract nodes (paints empty).

Reads only: document.inspect {depth:0}, node.get {id} (one level of children per call,
cached, never twice for an id), component.properties {id}, variable.list {}.
Hand-offs (Tasks 8-9) are described on `walk()`.
"""
from collections import deque

from . import interactions
from .style import num, css_color, effects_css, solid, text_style
from .control import ControlError

SELECT_MSG = "Sélectionnez au moins une frame de premier niveau."
_KINDS = {"FRAME": "frame", "COMPONENT": "frame", "COMPONENT_SET": "frame", "SECTION": "frame",
          "GROUP": "group", "INSTANCE": "instance", "TEXT": "text"}
_SKIP_TYPES = ("SLICE",)


class WalkError(Exception):
    """Nothing exportable (message in French, shown as is)."""


def _variant_props(key):
    out = {}
    for part in str(key).split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


class _Walker(object):
    def __init__(self, ctl, extras):
        self.ctl, self.extras = ctl, extras or {}
        self.cache, self.comps, self.props = {}, {}, {}
        self.nodes, self.screens, self.jobs = {}, {}, []
        self.warnings, self.skipped, self.approx = [], [], []
        self.bound, self.parent, self.screen_of, self.modes = {}, {}, {}, {}
        self.actions, self.var_types = [], {}
        self.queue, self.queued, self.missing = deque(), set(), set()
        self.pending, self.inst_links = [], {}
        self.prefix, self.alias = "", {}  # node ids: alias.get(fc) or prefix + fc (render's variant clones)

    def _id(self, fc):
        return self.alias.get(fc) or self.prefix + str(fc)

    def get(self, fc_id):
        if fc_id not in self.cache:
            try:
                self.cache[fc_id] = self.ctl.execute("node.get", {"id": fc_id})
            except ControlError:
                self.cache[fc_id] = None
        return self.cache[fc_id]

    def warn(self, msg, skipped=True):
        if msg in self.warnings:
            return
        self.warnings.append(msg)
        if skipped:
            self.skipped.append(msg)

    # -- selection ---------------------------------------------------------
    def _top_frames(self, container, section, order, section_of, tops):
        # layers-panel order: topmost first = reverse of `children`
        for c in reversed(container.get("children") or []):
            tops[c["id"]] = c
            if c.get("type") == "FRAME":
                order.append(c["id"])
                section_of[c["id"]] = section
            elif c.get("type") == "SECTION" and c.get("childCount", len(c.get("children") or [])):
                sec = self.get(c["id"]) or {}
                self._top_frames(sec, (c["id"], c.get("name")), order, section_of, tops)

    def run(self):
        insp = self.ctl.request("document.inspect", {"depth": 0}) or {}
        sel = [s for s in insp.get("selection") or []]
        if not sel:
            raise WalkError(SELECT_MSG)
        page_id = insp.get("currentPage")
        page = self.get(page_id) or {}
        order, section_of, tops = [], {}, {}
        self._top_frames(page, None, order, section_of, tops)
        selected = [i for i in order if i in sel]
        for i in sel:
            if i in selected:
                continue
            if i in tops:
                self.warn("« %s » ignoré : seules les frames de premier niveau sont exportées." % tops[i].get("name", i))
            else:
                name = (self.get(i) or {}).get("name", i)
                self.warn("« %s » ignoré : ce calque est dans une frame ; sélectionnez la frame de premier niveau." % name)
        if not selected:
            raise WalkError(SELECT_MSG)
        vl = self.ctl.execute("variable.list", {}) or {}
        self.var_types = {v.get("id"): v.get("resolvedType") for v in vl.get("variables") or []}
        start = selected[0]
        for f in page.get("flows") or []:
            if f.get("start") in selected:
                start = f["start"]
                break
        for i in selected:
            self.enqueue(i, None)
        while self.queue:
            self._screen(*self.queue.popleft())
            self._finish_instances()
        panel, idx = [], {}
        for i in selected:
            sec = section_of.get(i)
            if sec not in idx:
                idx[sec] = len(panel)
                panel.append({"section": sec[1] if sec else None, "screens": []})
            panel[idx[sec]]["screens"].append(str(i))
        proto = {"version": 1, "title": insp.get("name") or page.get("name") or "", "start": str(start),
                 "panel": panel, "pageName": page.get("name") or "", "screens": self.screens,
                 "nodes": self.nodes, "variables": {"collections": {}, "vars": {}},
                 "report": {"approximated": self.approx, "skipped": self.skipped}}
        return {"proto": proto, "jobs": self.jobs, "warnings": self.warnings, "page_id": str(page_id),
                "bound": self.bound, "explicit_modes": self.modes, "parent": self.parent,
                "screen_of": self.screen_of, "variables_raw": vl, "actions": self.actions}

    # -- closure -----------------------------------------------------------
    def enqueue(self, dest, source):
        if dest in self.queued or dest in self.missing:
            return
        raw = self.get(dest)
        if raw is None:
            self.missing.add(dest)
            self.warn("Lien ignoré : la destination %s du calque « %s » est introuvable." % (dest, source))
            return
        self.queued.add(dest)
        self.queue.append((dest, raw))

    def _screen(self, sid, raw):
        nid = str(sid)
        fill = solid(raw)
        self.screens[nid] = {"name": raw.get("name", ""), "width": num(raw.get("width", 0)),
                             "height": num(raw.get("height", 0)),
                             "background": css_color(fill) if fill else "transparent", "root": nid,
                             "overflow": self.extras.get(nid, {}).get("overflow", "none")}
        if nid in self.nodes:
            return
        todo = deque([(raw, None, None, [])])
        while todo:
            r, parent_raw, inst, hidden = todo.popleft()
            todo.extend(self._node(r, parent_raw, inst, hidden, nid)[0])

    def _children(self, raw):
        if raw.get("type") == "BOOLEAN_OPERATION" or (raw.get("type") == "GROUP" and "booleanOperation" in raw):
            return []
        if "children" in raw:
            return raw["children"]
        if raw.get("childCount"):
            return (self.get(raw["id"]) or {}).get("children") or []
        return []

    def _node(self, raw, parent_raw, inst, hidden, screen, flat=False):
        """Adds one contract node; returns ([child work items], its own job or None).
        flat: drawn as one paint (a mask layer), children not listed."""
        fc, nid, t = raw["id"], self._id(raw["id"]), raw.get("type")
        kids = [] if flat else [c for c in self._children(raw) if c.get("type") not in _SKIP_TYPES]
        mask = None
        if t == "GROUP" and kids and kids[0].get("isMask"):
            mask, kids = kids[0], kids[1:]
        kind = "leaf" if flat or (t == "GROUP" and "booleanOperation" in raw) else _KINDS.get(t, "leaf")
        if parent_raw is None:
            x = y = 0
        elif parent_raw.get("type") == "GROUP":
            x, y = raw.get("x", 0) - parent_raw.get("x", 0), raw.get("y", 0) - parent_raw.get("y", 0)
        else:
            x, y = raw.get("x", 0), raw.get("y", 0)
        if raw.get("visible", True) is False:
            hidden = hidden + [fc]
        ex = self.extras.get(nid, {})
        css, strip, approx = effects_css(raw, bool(kids))
        if raw.get("opacity", 1) < 1:
            strip.append("opacity")  # the element's own opacity applies it
        name = raw.get("name", "")
        if mask is not None:
            approx.append("masque")
        if approx:
            self.approx.append("« %s » : %s (approximation CSS)" % (name, ", ".join(approx)))
        bv = raw.get("boundVariables") or {}
        live = None
        if t == "TEXT" and self.var_types.get(bv.get("characters")) in ("string", "number"):
            live = {"var": bv["characters"], "style": text_style(raw)}
        bindings = {}
        if self.var_types.get(bv.get("visible")) == "boolean":
            bindings["visible"] = bv["visible"]
        node = {"id": nid, "name": name, "kind": kind, "x": num(round(x, 4)), "y": num(round(y, 4)),
                "w": num(raw.get("width", 0)), "h": num(raw.get("height", 0)),
                "rotation": num(raw.get("rotation", 0)), "opacity": num(raw.get("opacity", 1)),
                "visible": raw.get("visible", True) is not False, "clip": bool(raw.get("clip")),
                "overflow": ex.get("overflow", "none"), "position": ex.get("position", "scroll"),
                "paint": None, "alts": [], "css": css, "liveText": live, "bindings": bindings,
                "instance": None, "children": [self._id(c["id"]) for c in kids], "interactions": []}
        self.nodes[nid] = node
        self.parent[nid] = self._id(parent_raw["id"]) if parent_raw is not None else None
        self.screen_of[nid] = screen
        if bv:
            self.bound[nid] = dict(bv)
        if ex.get("varModes"):
            self.modes[nid] = dict(ex["varModes"])
        job_node, job_kids = nid, bool(kids)
        if t == "INSTANCE":
            inst = nid
            self.inst_links.setdefault(nid, [])
            key0 = self._key0(raw)
            self.pending.append((raw, hidden, key0))
            job_node, job_kids = self._self_node(raw, node, key0, screen), True
        self._interactions(raw, node, inst)
        job = None
        if kind != "group" and live is None:
            job = {"node": job_node, "fc_id": fc, "kind": "own", "hide_children": job_kids, "strip_effects": strip}
            if hidden:
                job["unhide"] = list(hidden)
            self.jobs.append(job)
        if mask is not None:
            mjob = self._node(mask, raw, inst, hidden, screen, flat=True)[1]  # in nodes, drawn by no parent
            if mjob is not None:
                mjob["mask_for"] = nid
        return [(c, raw, inst, hidden) for c in kids], job

    def _self_node(self, raw, node, key0, screen):
        """The instance's own paint as a first child "<inst>~<key>~self" (the instance
        element keeps opacity/css/interactions; its paint lives in variants[key])."""
        nid = node["id"]
        sid = "%s~%s~self" % (nid, key0)
        self.nodes[sid] = {"id": sid, "name": node["name"], "kind": "leaf", "x": 0, "y": 0, "w": node["w"],
                           "h": node["h"], "rotation": 0, "opacity": 1, "visible": True, "clip": False,
                           "overflow": "none", "position": "scroll", "paint": None, "alts": [], "css": {},
                           "liveText": None, "bindings": {}, "instance": None, "children": [], "interactions": []}
        node["children"].insert(0, sid)
        self.parent[sid], self.screen_of[sid] = nid, screen
        if nid in self.bound:
            self.bound[sid] = dict(self.bound[nid])
        return sid

    def _interactions(self, raw, node, inst):
        for ri in raw.get("interactions") or []:
            lk = interactions.links(ri)
            if inst is not None:
                self.inst_links[inst].extend(lk["variants"])
            conv = self._convert(ri, node["name"])
            if conv is not None:
                node["interactions"].append(conv)
            for d in lk["screens"]:
                self.enqueue(d, node["name"])

    def _convert(self, ri, name):
        for d in interactions.links(ri)["variants"]:
            if self._component(d) is None:
                self.warn("Lien ignoré : la variante %s du calque « %s » est introuvable." % (d, name))
        try:
            conv = interactions.convert(ri, variant_key=self._variant_key)
        except ValueError as e:
            self.warn("Interaction ignorée sur « %s » : type inconnu « %s »." % (name, e))
            return None
        if ri.get("actions") and not conv["actions"]:
            return None
        self.actions.extend(interactions.flat_actions(conv))
        return conv

    # -- variants ----------------------------------------------------------
    def _component(self, cid):
        """{name, raw (root interactions), screens, variants} of a variant component, cached."""
        if cid not in self.comps:
            raw = self.get(cid)
            info = None
            if raw is not None:
                # nested: per nested instance, [its main component] + its own changeTo dests
                info = {"name": raw.get("name", str(cid)), "raw": raw.get("interactions") or [],
                        "screens": [], "variants": [], "nested": [], "desc": [], "conv": None, "linked": False}
                todo = [(raw, None)]
                while todo:
                    r, nest = todo.pop(0)
                    for ri in r.get("interactions") or []:
                        lk = interactions.links(ri)
                        info["screens"] += lk["screens"]
                        (info["variants"] if nest is None else nest).extend(lk["variants"])
                        if r is not raw:
                            info["desc"].append(ri)
                    for c in self._children(r):
                        if c.get("type") == "INSTANCE":
                            lst = [c.get("mainComponent")]
                            info["nested"].append(lst)
                            todo.append((c, lst))
                        else:
                            todo.append((c, nest))
            self.comps[cid] = info
        return self.comps[cid]

    def _variant_key(self, dest):
        comp = self._component(dest)
        return comp["name"] if comp else None

    def _reach(self, start):
        """Component ids reachable from `start` through changeTo chains (missing ones dropped)."""
        out, todo = [], list(start)
        while todo:
            cid = todo.pop(0)
            comp = self._component(cid) if cid is not None else None
            if comp is None or cid in out:
                continue
            out.append(cid)
            todo.extend(comp["variants"])
        return out

    def _comp_conv(self, cid):
        comp = self._component(cid)
        if comp["conv"] is None:
            comp["conv"] = [c for c in (self._convert(ri, comp["name"]) for ri in comp["raw"]) if c]
        return comp["conv"]

    def _comp_links(self, cid):
        """Once per component: follow its screen links, nested instances' variants, and add
        its descendants' actions to `actions` (Task 9 builds the nodes)."""
        comp = self._component(cid)
        if comp["linked"]:
            return
        comp["linked"] = True
        self._comp_conv(cid)
        for d in comp["screens"]:
            self.enqueue(d, comp["name"])
        for ri in comp["desc"]:
            self._convert(ri, comp["name"])
        for lst in comp["nested"]:
            for c2 in self._reach(lst):
                self._comp_links(c2)

    def _key0(self, raw):
        main = raw.get("mainComponent")
        first = self._component(main) if main is not None and not raw.get("mainComponentName") else None
        return raw.get("mainComponentName") or (first["name"] if first else str(raw["id"]))

    def _set_name(self, raw):
        main = raw.get("mainComponent")
        if main not in self.props:
            try:
                p = self.ctl.execute("component.properties", {"id": raw["id"]}) or {}
                s = self.get(p.get("set")) if p.get("set") is not None else None
                self.props[main] = (s or {}).get("name") or ""
            except ControlError:
                self.props[main] = ""
        return self.props[main]

    def _finish_instances(self):
        while self.pending:
            raw, hidden, key0 = self.pending.pop(0)
            nid = self._id(raw["id"])
            node = self.nodes[nid]
            main = raw.get("mainComponent")
            reach = {}
            for cid in self._reach([main] + self.inst_links.get(nid, [])):
                key = key0 if cid == main else self._component(cid)["name"]
                if key not in reach:
                    reach[key] = cid
                    self._comp_links(cid)
            vi = {key: self._comp_conv(cid) for key, cid in reach.items()}
            variants = {key0: list(node["children"])}
            for key, cid in reach.items():
                if key == key0:
                    continue
                variants[key] = []
                job = {"node": nid, "fc_id": raw["id"], "kind": "variant", "hide_children": False,
                       "strip_effects": [], "instance": nid, "variant": key, "variant_fc_id": cid,
                       "properties": _variant_props(key)}
                if hidden:
                    job["unhide"] = list(hidden)
                self.jobs.append(job)
            node["instance"] = {"set": self._set_name(raw), "variant": key0, "variants": variants,
                                "variantInteractions": vi}


def walk(ctl, extras):
    """Walk the current page's selected top-level frames and everything they link to.

    Returns Walked = {"proto", "jobs", "warnings", "page_id", "bound", "explicit_modes",
    "parent", "screen_of", "variables_raw", "actions"}: see task-7-report.md for the
    exact shapes and what Tasks 8 (mode/varValue jobs, variables) and 9 (paints,
    non-current variant subtrees) must fill in. Raises WalkError (French) when nothing
    exportable is selected.
    """
    return _Walker(ctl, extras).run()
