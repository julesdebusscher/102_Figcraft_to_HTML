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
    "mainComponentName"?}}; vars: {var: {"collection", "values": {mode: colour}}};
    defaults: {coll: mode}."""

    def __init__(self, nodes, vars_=None, defaults=None, fail_export=None, fail_undo=0):
        self.state = {"nodes": copy.deepcopy(nodes), "vars": copy.deepcopy(vars_ or {})}
        self.defaults = dict(defaults or {})
        self.history = []
        self.calls = []
        self.fail_export = fail_export  # (fc, nth call) -> raise ControlError
        self.exports = 0
        self.fail_undo = fail_undo      # number of edit.undo calls that raise
        for fc, n in self.state["nodes"].items():
            for k in n.get("children") or []:
                self.state["nodes"][k]["parent"] = fc

    def snapshot(self):
        return copy.deepcopy(self.state)

    # -- control API -------------------------------------------------------
    def request(self, method, params=None, timeout_ms=60000):
        raise AssertionError("unexpected request %s" % method)

    def execute(self, command, params=None, timeout_ms=60000):
        params = params or {}
        self.calls.append((command, copy.deepcopy(params)))
        if command == "edit.undo":
            if self.fail_undo:
                self.fail_undo -= 1
                raise ControlError("undo failed")
            if not self.history:
                return {"undone": False}
            self.state = self.history.pop()
            return {"undone": True}
        if command in ("node.set", "instance.setProperties", "variable.setMode", "variable.set", "command.batch"):
            before = self.snapshot()
            try:
                self._mutate(command, params)
            except ControlError:
                self.state = before
                raise
            self.history.append(before)
            return {"ok": True}
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
               if k not in ("children", "bound", "modes", "variants", "parent")}
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
            if self.state["nodes"][cur].get("rotation"):
                return True
            cur = self.state["nodes"][cur].get("parent")
        return False

    def _export(self, p):
        fc = p["ids"][0]
        self.exports += 1
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
