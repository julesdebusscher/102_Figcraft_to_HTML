"""A tiny in-memory FigCraft document for render tests: node.get/set, command.batch,
instance.setProperties, variable.setMode/set, edit.undo (one history step per successful
call) and a file.export whose SVG shows what would be drawn."""
import base64
import copy

from figcraft_export.control import ControlError

PNG_HEAD = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


class SimDoc(object):
    """nodes: {fc: {"type", "name", "width", "height", "x", "y", "visible"?, "rotation"?,
    "opacity"?, "blend"?, "effects"?, "fills"?, "children"?: [fc], "bound"?: var,
    "modes"?: {coll: mode}, "variants"?: {key: {"children", "fills", "width", "height"}},
    "mainComponentName"?, "mainComponent"?: fc, "main_of"?: fc}}; vars: {var: {"collection", "values": {mode: colour}}};
    defaults: {coll: mode}.
    "main_of": a layer inside an instance; its rotation is the main component layer's and
    node.set rotation on it is refused, like FigCraft."""

    def __init__(self, nodes, vars_=None, defaults=None, fail_export=None, fail_undo=0, undo_script=None,
                 on_export=None, timeout_edit=None, redo_fails=False, inspect_fail_after_undo=0):
        self.state = {"nodes": copy.deepcopy(nodes), "vars": copy.deepcopy(vars_ or {})}
        self.defaults = dict(defaults or {})
        self.history = []               # [(label, state before)], newest last
        self.redo = []                  # [(label, state after)], newest last
        self.calls = []
        self.fail_export = fail_export  # (fc, nth call) -> raise ControlError
        self.exports = 0
        # edit.undo behaviours in order: "raise" (nothing undone), "raise_after" (undone, then
        # raises), "interrupt" (undone, then KeyboardInterrupt), "user_first" (a user step lands
        # just before the undo, which then reverts it), "user_first_raise" (same, then the undo
        # raises), "raise_then_user" (nothing undone, a user step lands, then it raises); then normal
        self.undo_script = list(undo_script or []) + ["raise"] * fail_undo
        self.on_export = on_export      # f(doc, fc): e.g. a user edit while we render
        self.timeout_edit = timeout_edit  # nth edit call: applied, then "timed out"
        self.edit_calls = 0
        self.redo_fails = redo_fails    # edit.redo answers {redone:false} and does nothing
        self.inspect_fail_after_undo = inspect_fail_after_undo  # next n document.inspect raise after an undo
        self._inspect_fails = 0
        for fc, n in self.state["nodes"].items():
            for k in n.get("children") or []:
                self.state["nodes"][k]["parent"] = fc

    def snapshot(self):
        return copy.deepcopy(self.state)

    def user_edit(self, fc, props):
        """A step made by the user in FigCraft (not through our calls)."""
        before = self.snapshot()
        self.state["nodes"][fc].update(props)
        self.history.append(("Set properties", before))
        self.redo = []

    # -- control API -------------------------------------------------------
    def request(self, method, params=None, timeout_ms=60000):
        self.calls.append((method, copy.deepcopy(params or {})))
        if method == "document.inspect":
            if self._inspect_fails:
                self._inspect_fails -= 1
                raise ControlError("FigCraft n'a pas répondu à temps.")
            return {"history": {"undo": [h[0] for h in reversed(self.history)], "redo": len(self.redo)}}
        raise AssertionError("unexpected request %s" % method)

    def execute(self, command, params=None, timeout_ms=60000):
        params = params or {}
        self.calls.append((command, copy.deepcopy(params)))
        if command == "edit.undo":
            self._inspect_fails = self.inspect_fail_after_undo
            how = self.undo_script.pop(0) if self.undo_script else None
            if how == "raise":
                raise ControlError("undo failed")
            if how == "raise_then_user":   # nothing undone, the call fails, then the user edits
                self.user_edit(1, {"name": "user step after a failed undo"})
                raise ControlError("FigCraft n'a pas répondu à temps.")
            if how in ("user_first", "user_first_raise"):
                self.user_edit(1, {"name": "racing user step"})
            if not self.history:
                return {"undone": False}
            label, before = self.history.pop()
            self.redo.append((label, self.snapshot()))
            self.state = before
            if how in ("raise_after", "user_first_raise"):
                raise ControlError("FigCraft n'a pas répondu à temps.")
            if how == "interrupt":
                raise KeyboardInterrupt()
            return {"undone": True}
        if command == "edit.redo":
            if not self.redo or self.redo_fails:
                return {"redone": False}
            label, after = self.redo.pop()
            self.history.append((label, self.snapshot()))
            self.state = after
            return {"redone": True}
        if command in ("node.set", "instance.setProperties", "variable.setMode", "variable.set", "command.batch"):
            before = self.snapshot()
            try:
                self._mutate(command, params)
            except ControlError:
                self.state = before
                raise
            self.history.append((params.get("label") or "Batch" if command == "command.batch"
                                 else "Set properties", before))
            self.redo = []
            self.edit_calls += 1
            if self.timeout_edit == self.edit_calls:
                raise ControlError("FigCraft n'a pas répondu à temps.")
            return [{"ok": True}] * len(params["commands"]) if command == "command.batch" else {"ok": True}
        if command == "node.get":
            return self._get(params)
        if command == "file.export":
            return self._export(params)
        raise AssertionError("unexpected command %s" % command)

    def _mutate(self, command, p):
        if command == "command.batch":
            for c in p["commands"]:
                self._mutate(c["command"], c.get("params") or {})
            return
        nodes = self.state["nodes"]
        if command == "node.set":
            for i in p["ids"]:
                if i not in nodes:
                    raise ControlError("no such node %s" % i)
                if "rotation" in p["props"] and nodes[i].get("main_of") is not None:
                    raise ControlError("command `node.set` is not available right now: A layer's position "
                                       "comes from the main component in an instance: edit the main "
                                       "component, or detach the instance")
                props = copy.deepcopy(p["props"])
                for axis, key in (("horizontal", "sizingH"), ("vertical", "sizingV")):
                    if key in props:
                        nodes[i].setdefault("sizing", {})[axis] = props.pop(key)
                nodes[i].update(props)
                self._relayout()
        elif command == "instance.setProperties":
            for i in p["ids"]:
                n = nodes[i]
                key = ", ".join("%s=%s" % kv for kv in sorted(p["properties"].items()))
                v = n["variants"][key]
                n.update({"children": list(v["children"]), "fills": v["fills"], "width": v["width"],
                          "height": v["height"], "mainComponentName": key})
                for k in v["children"]:
                    nodes[k]["parent"] = i
        elif command == "variable.setMode":
            for i in p["ids"]:
                m = nodes[i].setdefault("modes", {})
                if p["mode"] is None:
                    m.pop(p["collection"], None)
                else:
                    m[p["collection"]] = p["mode"]
        elif command == "variable.set":
            self.state["vars"][p["variable"]]["values"][p["mode"]] = p["value"]

    def _relayout(self):
        """Auto layout: a "hug" axis shrinks to 10 when no child shows (like FigCraft's hug)."""
        nodes = self.state["nodes"]
        for n in nodes.values():
            hug = [a for a, v in (n.get("sizing") or {}).items() if v == "hug"]
            if hug and n.get("children") and all(nodes[k].get("visible", True) is False for k in n["children"]):
                n.update({("width" if a == "horizontal" else "height"): 10 for a in hug})

    def _public(self, fc):
        n = self.state["nodes"][fc]
        out = {k: copy.deepcopy(v) for k, v in n.items()
               if k not in ("children", "bound", "modes", "variants", "parent", "main_of")}
        if n.get("main_of") is not None:
            out["rotation"] = self.state["nodes"][n["main_of"]].get("rotation", 0)
        out["id"] = fc
        if n.get("bound"):
            out["boundVariables"] = {"fill": n["bound"]}
        if n.get("children"):
            out["childCount"] = len(n["children"])
        return out

    def _get(self, p):
        fc = p["id"]
        if fc not in self.state["nodes"]:
            return None
        n = self.state["nodes"][fc]
        if p.get("outline"):
            return {"id": fc, "children": [{"id": k, "name": self.state["nodes"][k].get("name", ""),
                                            "type": self.state["nodes"][k]["type"],
                                            "visible": self.state["nodes"][k].get("visible", True)}
                                           for k in n.get("children") or []]}
        if p.get("fields"):
            pub = self._public(fc)
            return dict({k: pub[k] for k in p["fields"] if k in pub}, id=fc)
        out = self._public(fc)
        if n.get("children"):
            out["children"] = [self._public(k) for k in n["children"]]
        return out

    def mode_of(self, fc, coll):
        cur = fc
        while cur is not None:
            m = (self.state["nodes"][cur].get("modes") or {}).get(coll)
            if m:
                return m
            cur = self.state["nodes"][cur].get("parent")
        return self.defaults[coll]

    def colour(self, fc):
        n = self.state["nodes"][fc]
        if n.get("bound"):
            v = self.state["vars"][n["bound"]]
            return v["values"][self.mode_of(fc, v["collection"])]
        return (n.get("fills") or [{}])[0].get("color")

    def rotated(self, fc):
        cur = fc
        while cur is not None:
            n = self.state["nodes"][cur]
            if (self.state["nodes"][n["main_of"]] if n.get("main_of") is not None else n).get("rotation"):
                return True
            cur = self.state["nodes"][cur].get("parent")
        return False

    def _export(self, p):
        fc = p["ids"][0]
        self.exports += 1
        if self.on_export:
            self.on_export(self, fc)
        if self.fail_export and self.fail_export == (fc, self.exports):
            raise ControlError("export failed")
        n = self.state["nodes"][fc]
        w, h = n["width"], n["height"]
        if n.get("visible", True) is False:
            return self._out(p, "<svg width=\"%g\" height=\"%g\"></svg>" % (w, h), w, h)
        body, minx, miny, maxx, maxy = [], 0.0, 0.0, float(w), float(h)
        shadows = [e for e in n.get("effects") or [] if e["type"] == "dropShadow"]
        if not p.get("includeBoundingBox"):
            for e in shadows:
                m = 1.5 * e["radius"]
                minx, miny = min(minx, e["offset"][0] - m), min(miny, e["offset"][1] - m)
                maxx, maxy = max(maxx, w + e["offset"][0] + m), max(maxy, h + e["offset"][1] + m)
        for e in shadows:
            body.append('<path transform="matrix(1 0 0 1 %g %g)" d="shadow"/>' % (e["offset"][0] - minx, e["offset"][1] - miny))
        tags = []
        if n.get("opacity", 1) < 1:
            tags.append("opacity=%g" % n["opacity"])
        if n.get("blend") not in (None, "normal"):
            tags.append("blend=%s" % n["blend"])
        for e in n.get("effects") or []:
            if e["type"] != "dropShadow":
                tags.append("effect=%s" % e["type"])
        if self.rotated(fc):
            tags.append("rotated")
        if self.colour(fc) and not n.get("isMask"):  # a mask layer draws nothing itself
            body.append('<path transform="matrix(1 0 0 1 %g %g)" d="box" fill="%s" data-tags="%s"/>'
                        % (-minx, -miny, self.colour(fc), " ".join(tags)))
        for k in n.get("children") or []:
            if self.state["nodes"][k].get("visible", True) is not False:
                body.append('<path transform="matrix(1 0 0 1 0 0)" d="kid%s"/>' % k)
        svg = '<svg width="%g" height="%g" viewBox="0 0 %g %g"><g>%s</g><defs><clipPath id="c"><path d="M0 0"/></clipPath></defs></svg>' % (
            maxx - minx, maxy - miny, maxx - minx, maxy - miny, "".join(body))
        return self._out(p, svg, maxx - minx, maxy - miny)

    def _out(self, p, svg, w, h):
        if p.get("format") == "png":
            s = p.get("scale", 1)
            data = PNG_HEAD + int(w * s).to_bytes(4, "big") + int(h * s).to_bytes(4, "big") + svg.encode("utf-8")
            return {"format": "png", "data": base64.b64encode(data).decode("ascii")}
        return {"format": "svg", "data": base64.b64encode(svg.encode("utf-8")).decode("ascii")}
