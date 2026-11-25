import unittest
from unittest import mock

from figcraft_export import render
from figcraft_export.control import ControlError
from tests.sim_doc import SimDoc

THEME = "VariableCollectionId:1"
LIGHT, DARK = THEME + "/mode1", THEME + "/mode2"
SURF = "VariableID:1"


def cnode(nid, kind="leaf", w=100, h=60, children=(), **kw):
    n = {"id": nid, "name": kw.pop("name", "n" + nid), "kind": kind, "x": 0, "y": 0, "w": w, "h": h,
         "rotation": 0, "opacity": 1, "visible": True, "clip": False, "overflow": "none",
         "position": "scroll", "paint": None, "alts": [], "css": {}, "liveText": None, "bindings": {},
         "instance": None, "children": list(children), "interactions": []}
    n.update(kw)
    return n


def job(nid, fc, hide=False, strip=(), **kw):
    j = {"node": nid, "fc_id": fc, "kind": "own", "hide_children": hide, "strip_effects": list(strip)}
    j.update(kw)
    return j


def rect(name="r", w=100, h=60, color="#00AAFF", **kw):
    n = {"type": "RECTANGLE", "name": name, "width": w, "height": h, "x": 0, "y": 0,
         "fills": [{"type": "solid", "color": color}]}
    n.update(kw)
    return n


def make(doc_nodes, proto_nodes, jobs, parent, variables=None, vars_=None, defaults=None, **sim):
    doc = SimDoc(doc_nodes, vars_=vars_, defaults=defaults, **sim)
    screen_of = {n["id"]: "1" for n in proto_nodes}
    walked = {"proto": {"nodes": {n["id"]: n for n in proto_nodes},
                        "variables": variables or {"collections": {}, "vars": {}},
                        "report": {"approximated": [], "skipped": []}},
              "jobs": jobs, "warnings": [], "parent": parent, "screen_of": screen_of,
              "bound": {}, "explicit_modes": {}, "actions": [], "variables_raw": {}}
    return doc, walked


def svg_of(assets, paint):
    return {a["path"]: a["data"] for a in assets}[paint["src"]].decode("utf-8")


def calls(doc, name):
    return [p for c, p in doc.calls if c == name]


def flat_edits(doc):
    """Every editing command, batches expanded: [(command, params)]."""
    out = []
    for c, p in doc.calls:
        if c == "command.batch":
            out.extend((s["command"], s["params"]) for s in p["commands"])
        elif c in ("node.set", "instance.setProperties", "variable.setMode", "variable.set"):
            out.append((c, p))
    return out


def basic():
    doc_nodes = {
        1: {"type": "FRAME", "name": "Écran", "width": 390, "height": 844, "x": 0, "y": 0,
            "fills": [{"type": "solid", "color": "#FFFFFF"}], "children": [2, 3]},
        2: rect("Bouton", color="#00AAFF"),
        3: {"type": "FRAME", "name": "Carte", "width": 200, "height": 100, "x": 0, "y": 0,
            "fills": [{"type": "solid", "color": "#EEEEEE"}], "children": [4]},
        4: rect("Texte", color="#222222"),
    }
    proto = [cnode("1", "frame", 390, 844, ["2", "3"]), cnode("2"), cnode("3", "frame", 200, 100, ["4"]),
             cnode("4")]
    jobs = [job("1", 1, hide=True), job("2", 2), job("3", 3, hide=True), job("4", 4)]
    parent = {"1": None, "2": "1", "3": "1", "4": "3"}
    return doc_nodes, proto, jobs, parent


def variant_scene(doc_edit=None, w_edit=None, **sim):
    doc_nodes = {
        1: {"type": "FRAME", "name": "Écran", "width": 390, "height": 844, "x": 0, "y": 0,
            "fills": [{"type": "solid", "color": "#FFFFFF"}], "children": [10]},
        10: {"type": "INSTANCE", "name": "Carte", "width": 200, "height": 100, "x": 5, "y": 5,
             "fills": [{"type": "solid", "color": "#0000AA"}], "children": [11],
             "mainComponentName": "Mode=A", "mainComponent": 20,
             "variants": {"Mode=A": {"children": [11], "fills": [{"type": "solid", "color": "#0000AA"}],
                                     "width": 200, "height": 100},
                          "Mode=B": {"children": [12, 13], "fills": [{"type": "solid", "color": "#00BB00"}],
                                     "width": 240, "height": 120}}},
        11: rect("Titre A", 50, 20, "#111111", x=10, y=10),
        12: rect("Titre B", 60, 20, "#222222", x=12, y=14),
        13: rect("Pied B", 60, 20, "#333333", x=12, y=80, visible=False),
    }
    for k in (12, 13):
        doc_nodes[k]["parent"] = 10
    sid = "10~Mode=A~self"
    inst = cnode("10", "instance", 200, 100, [sid, "11"], x=5, y=5,
                 instance={"set": "Carte", "variant": "Mode=A",
                           "variants": {"Mode=A": [sid, "11"], "Mode=B": []}, "variantInteractions": {}})
    proto = [cnode("1", "frame", 390, 844, ["10"]), inst, cnode(sid, w=200, h=100), cnode("11", w=50, h=20)]
    jobs = [job("1", 1, hide=True), job(sid, 10, hide=True), job("11", 11),
            {"node": "10", "fc_id": 10, "kind": "variant", "hide_children": False, "strip_effects": [],
             "instance": "10", "variant": "Mode=B", "variant_fc_id": 30, "properties": {"Mode": "B"}}]
    parent = {"1": None, "10": "1", sid: "10", "11": "10"}
    if doc_edit:
        doc_edit(doc_nodes)
    doc, w = make(doc_nodes, proto, jobs, parent, **sim)
    if w_edit:
        w_edit(w)
    return doc, w


VARIABLES = {"collections": {THEME: {"name": "Theme", "defaultMode": LIGHT, "modes": {LIGHT: "Light", DARK: "Dark"}}},
             "vars": {SURF: {"name": "surface", "collection": THEME, "type": "color",
                             "valuesByMode": {LIGHT: "rgba(255, 255, 255, 1)", DARK: "rgba(17, 17, 17, 1)"}}}}
VARS = {SURF: {"collection": THEME, "values": {LIGHT: "#FFFFFF", DARK: "#111111"}}}


class RenderTests(unittest.TestCase):
    def test_container_paint_excludes_children(self):
        doc, w = make(*basic())
        start = doc.snapshot()
        assets = render.render_all(doc, w)
        nodes = w["proto"]["nodes"]
        svg = svg_of(assets, nodes["3"]["paint"])
        self.assertIn("#EEEEEE", svg)
        self.assertNotIn("kid4", svg)
        self.assertNotIn("kid", svg_of(assets, nodes["1"]["paint"]))
        # hide happened before the container's export and was undone after it
        i_export = [k for k, (c, p) in enumerate(doc.calls) if c == "file.export" and p["ids"] == [3]][0]
        before = [c for c, p in doc.calls[:i_export] if c in ("node.set", "command.batch")]
        self.assertTrue(before)
        self.assertIn("edit.undo", [c for c, p in doc.calls[i_export:]])
        self.assertIn(("node.set", {"ids": [4], "props": {"visible": False}}), flat_edits(doc))
        self.assertEqual(doc.snapshot(), start)
        self.assertEqual(doc.history, [])

    def test_redo_holds_only_a_no_op_step_after_render(self):
        doc, w = make(*basic())
        start = doc.snapshot()
        render.render_all(doc, w)
        self.assertEqual(doc.history, [])
        self.assertEqual(len(doc.redo), 1)                         # only the final no-op is redoable
        label, after = doc.redo[0]
        self.assertRegex(label, r"^Export HTML \(fin\) [0-9a-f]{4}$")
        self.assertIs(after["nodes"][1].pop("visible"), True)      # redoing it changes nothing
        self.assertEqual(after, start)
        self.assertEqual(doc.snapshot(), start)
        fin = [p for c, p in doc.calls if c == "command.batch" and p["label"].startswith("Export HTML (fin)")]
        self.assertEqual(fin[0]["commands"], [{"command": "node.set", "params": {"ids": [1], "props": {"visible": True}}}])

    def test_no_final_step_when_the_history_top_moved(self):
        doc, w = make(*basic())
        orig = render._Renderer.run

        def run(r, job):
            orig(r, job)
            if job["node"] == "4":                                  # the last job: a user step lands
                doc.user_edit(2, {"name": "user step after our last undo"})
        with mock.patch.object(render._Renderer, "run", run):
            render.render_all(doc, w)
        self.assertEqual([p["label"] for c, p in doc.calls if c == "command.batch"
                          if p["label"].startswith("Export HTML (fin)")], [])
        self.assertEqual(doc.history[-1][0], "Set properties")
        self.assertEqual(w["warnings"], [])

    def test_refused_final_step_becomes_a_remark_not_a_failure(self):
        doc, w = make(*basic())
        orig = doc.execute

        def execute(command, params=None, timeout_ms=60000):
            if command == "command.batch" and params["label"].startswith("Export HTML (fin)"):
                raise ControlError("refusé")
            return orig(command, params, timeout_ms)
        doc.execute = execute
        render.render_all(doc, w)
        self.assertEqual(w["warnings"], ["N'utilisez pas Rétablir (Cmd/Ctrl+Maj+Z) juste après l'export."])
        self.assertEqual(doc.history, [])

    def test_no_final_step_without_temporary_edits(self):
        doc_nodes = {1: rect("seul")}
        doc, w = make(doc_nodes, [cnode("1")], [job("1", 1)], {"1": None})
        render.render_all(doc, w)
        self.assertEqual(calls(doc, "command.batch"), [])
        self.assertEqual(doc.redo, [])

    def test_hug_container_keeps_its_size_without_children(self):
        doc_nodes, proto, jobs, parent = basic()
        doc_nodes[3]["sizing"] = {"horizontal": "hug", "vertical": "hug"}
        doc, w = make(doc_nodes, proto, jobs, parent)
        start = doc.snapshot()
        render.render_all(doc, w)
        p = w["proto"]["nodes"]["3"]["paint"]
        self.assertEqual((p["w"], p["h"]), (200, 100))
        self.assertEqual(doc.snapshot(), start)

    def test_edits_undone_after_error(self):
        doc, w = make(*basic(), fail_export=(3, 5))
        start = doc.snapshot()
        with self.assertRaises(ControlError):
            render.render_all(doc, w)
        self.assertEqual(doc.snapshot(), start)
        self.assertEqual(doc.history, [])
        edits = len([c for c, p in doc.calls if c in ("node.set", "command.batch", "instance.setProperties",
                                                       "variable.setMode", "variable.set")])
        self.assertEqual(len(calls(doc, "edit.undo")), edits)

    def test_user_step_between_our_edit_and_the_undo_is_never_reverted(self):
        def user(doc, fc):
            if fc == 1 and doc.exports == 1:
                doc.user_edit(2, {"name": "renamed by the user"})
        doc, w = make(*basic(), on_export=user)
        with self.assertRaises(render.RenderError):
            render.render_all(doc, w)
        self.assertEqual(calls(doc, "edit.undo"), [])
        self.assertEqual(doc.history[-1][0], "Set properties")        # the user's step is still there
        self.assertEqual(doc.state["nodes"][2]["name"], "renamed by the user")

    def test_timed_out_edit_that_landed_is_undone(self):
        doc, w = make(*basic(), timeout_edit=1)
        start = doc.snapshot()
        with self.assertRaises(ControlError):
            render.render_all(doc, w)
        self.assertEqual(len(calls(doc, "edit.undo")), 1)
        self.assertEqual(doc.snapshot(), start)
        self.assertEqual(doc.history, [])

    def test_ctrl_c_while_rendering_still_undoes_then_reraises(self):
        def interrupt(doc, fc):
            if fc == 3:
                raise KeyboardInterrupt()
        doc, w = make(*basic(), on_export=interrupt)
        start = doc.snapshot()
        with self.assertRaises(KeyboardInterrupt):
            render.render_all(doc, w)
        self.assertEqual(doc.snapshot(), start)
        self.assertEqual(doc.history, [])

    def test_asset_name_uses_sanitised_id_not_layer_name(self):
        self.assertEqual(render.sanitise("181~State=Hover, Size=L~182"), "181~State_Hover__Size_L~182")
        doc, w = make(*basic())
        assets = render.render_all(doc, w)
        paths = sorted(a["path"] for a in assets)
        self.assertIn("assets/1.svg", paths)
        for p in paths:
            self.assertRegex(p, r"^assets/[A-Za-z0-9_~-]+\.(svg|png)$")
            self.assertNotIn("cran", p)

    def test_duplicate_bytes_share_one_asset(self):
        doc_nodes, proto, jobs, parent = basic()
        doc_nodes[4] = rect("Texte", color="#00AAFF")   # same bytes as node 2
        doc, w = make(doc_nodes, proto, jobs, parent)
        assets = render.render_all(doc, w)
        nodes = w["proto"]["nodes"]
        self.assertEqual(nodes["2"]["paint"]["src"], nodes["4"]["paint"]["src"])
        self.assertEqual(len(assets), len(set(a["data"] for a in assets)))
        self.assertEqual(len(assets), 3)

    def test_mode_alt_renders_with_mode_then_restores(self):
        doc_nodes, proto, jobs, parent = basic()
        doc_nodes[2]["bound"] = SURF
        variables = {"collections": {THEME: {"name": "Theme", "defaultMode": LIGHT,
                                             "modes": {LIGHT: "Light", DARK: "Dark"}}},
                     "vars": {SURF: {"name": "surface", "collection": THEME, "type": "color",
                                     "valuesByMode": {LIGHT: "rgba(255, 255, 255, 1)",
                                                      DARK: "rgba(17, 17, 17, 1)"}}}}
        vars_ = {SURF: {"collection": THEME, "values": {LIGHT: "#FFFFFF", DARK: "#111111"}}}
        proto[1]["alts"] = [{"when": {"vars": {SURF: "rgba(255, 0, 0, 1)"}}, "paint": None},
                            {"when": {"modes": {THEME: DARK}}, "paint": None}]
        jobs.append(dict(job("2", 2), kind="varValue", alt=0, when=proto[1]["alts"][0]["when"],
                         vars={SURF: "rgba(255, 0, 0, 1)"}, modes={}, var=SURF, value="rgba(255, 0, 0, 1)"))
        jobs.append(dict(job("2", 2), kind="mode", alt=1, when=proto[1]["alts"][1]["when"],
                         vars={}, modes={THEME: DARK}, collection=THEME, mode=DARK))
        doc, w = make(doc_nodes, proto, jobs, parent, variables=variables, vars_=vars_,
                      defaults={THEME: LIGHT})
        start = doc.snapshot()
        assets = render.render_all(doc, w)
        n = w["proto"]["nodes"]["2"]
        self.assertIn("#FFFFFF", svg_of(assets, n["paint"]))
        self.assertIn("rgba(255, 0, 0, 1)", svg_of(assets, n["alts"][0]["paint"]))
        self.assertIn("#111111", svg_of(assets, n["alts"][1]["paint"]))
        self.assertTrue(n["alts"][1]["paint"]["src"].endswith("__alt1.svg"))
        # the mode is set on the screen root, the value in every mode of the collection
        self.assertIn(("variable.setMode", {"ids": [1], "collection": THEME, "mode": DARK}), flat_edits(doc))
        sets = [p for c, p in flat_edits(doc) if c == "variable.set"]
        self.assertEqual(sorted(p["mode"] for p in sets), [LIGHT, DARK])
        self.assertEqual(doc.snapshot(), start)

    def test_variant_render_switches_then_restores(self):
        doc, w = variant_scene()
        start = doc.snapshot()
        assets = render.render_all(doc, w)
        nodes = w["proto"]["nodes"]
        bself, b12, b13 = "10~Mode=B~self", "10~Mode=B~12", "10~Mode=B~13"
        self.assertEqual(nodes["10"]["instance"]["variants"]["Mode=B"], [bself, b12, b13])
        self.assertEqual((nodes[bself]["w"], nodes[bself]["h"]), (240, 120))
        self.assertIn("#00BB00", svg_of(assets, nodes[bself]["paint"]))
        self.assertNotIn("kid", svg_of(assets, nodes[bself]["paint"]))
        self.assertIn("#222222", svg_of(assets, nodes[b12]["paint"]))
        self.assertEqual((nodes[b12]["x"], nodes[b12]["y"], nodes[b12]["w"]), (12, 14, 60))
        self.assertFalse(nodes[b13]["visible"])
        self.assertIsNotNone(nodes[b13]["paint"])          # hidden layer still painted (unhidden for it)
        self.assertEqual(w["parent"][b12], "10")
        self.assertTrue(nodes[bself]["paint"]["src"].startswith("assets/10~Mode_B~self"))
        self.assertIn(("instance.setProperties", {"ids": [10], "properties": {"Mode": "B"}}), flat_edits(doc))
        self.assertEqual(doc.snapshot(), start)
        self.assertEqual(doc.history, [])

    def test_variant_clone_gets_alternatives_and_extras_and_its_warnings(self):
        def doc_edit(doc_nodes):
            doc_nodes[12]["bound"] = SURF
            doc_nodes[13]["blend"] = "multiply"

        def w_edit(w):
            w["proto"]["variables"] = VARIABLES
            w["actions"] = [{"type": "setVariableMode", "collection": THEME, "mode": DARK}]
            w["extras"] = {"12": {"position": "fixed"}}
        doc, w = variant_scene(doc_edit, w_edit, vars_=VARS, defaults={THEME: LIGHT})
        start = doc.snapshot()
        assets = render.render_all(doc, w)
        n = w["proto"]["nodes"]["10~Mode=B~12"]
        self.assertEqual(n["position"], "fixed")
        self.assertIn("#FFFFFF", svg_of(assets, n["paint"]))   # bound: Light by default
        self.assertEqual([a["when"] for a in n["alts"]], [{"modes": {THEME: DARK}}])
        self.assertIn("#111111", svg_of(assets, n["alts"][0]["paint"]))
        self.assertTrue(any("Pied B" in m for m in w["proto"]["report"]["approximated"]))
        self.assertEqual(doc.snapshot(), start)

    def test_unparsed_offset_listed_as_approximation(self):
        doc_nodes, proto, jobs, parent = basic()
        doc, w = make(doc_nodes, proto, jobs, parent)
        real = doc._export
        doc._export = lambda p: ({"format": "svg", "data": __import__("base64").b64encode(
            b'<svg width="100" height="60"><rect width="1" height="1"/></svg>').decode()}
            if p["ids"] == [2] and p["format"] == "svg" else real(p))
        render.render_all(doc, w)
        self.assertEqual(w["proto"]["nodes"]["2"]["paint"]["dx"], 0)
        self.assertIn("« n2 » : position du rendu inconnue (approximation)", w["proto"]["report"]["approximated"])

    def test_variable_of_unknown_collection_skips_the_alternative_with_a_warning(self):
        doc_nodes, proto, jobs, parent = basic()
        proto[1]["alts"] = [{"when": {"vars": {"VariableID:9": "rgba(1, 2, 3, 1)"}}, "paint": None},
                            {"when": {"modes": {THEME: DARK}}, "paint": None}]
        doc_nodes[2]["bound"] = SURF
        jobs.append(dict(job("2", 2), kind="varValue", alt=0, when=proto[1]["alts"][0]["when"],
                         vars={"VariableID:9": "rgba(1, 2, 3, 1)"}, modes={}))
        jobs.append(dict(job("2", 2), kind="mode", alt=1, when=proto[1]["alts"][1]["when"], vars={},
                         modes={THEME: DARK}))
        doc, w = make(doc_nodes, proto, jobs, parent, variables=VARIABLES, vars_=VARS, defaults={THEME: LIGHT})
        assets = render.render_all(doc, w)
        alts = w["proto"]["nodes"]["2"]["alts"]
        self.assertEqual([a["when"] for a in alts], [{"modes": {THEME: DARK}}])
        self.assertIn("#111111", svg_of(assets, alts[0]["paint"]))
        msg = "Variable VariableID:9 de collection inconnue : alternative ignorée pour « n2 »."
        self.assertIn(msg, w["warnings"])
        self.assertIn(msg, w["proto"]["report"]["skipped"])

    def test_paint_offsets_account_for_shadow_bounds(self):
        doc_nodes, proto, jobs, parent = basic()
        doc_nodes[2]["effects"] = [{"type": "dropShadow", "offset": [10, 4], "radius": 16, "spread": 0,
                                    "visible": True}]
        doc, w = make(doc_nodes, proto, jobs, parent)
        render.render_all(doc, w)
        self.assertEqual(w["proto"]["nodes"]["2"]["paint"], {"src": "assets/2.svg", "dx": -14, "dy": -20,
                                                            "w": 148, "h": 108})
        self.assertEqual(w["proto"]["nodes"]["4"]["paint"]["dx"], 0)
        self.assertEqual(w["proto"]["nodes"]["4"]["paint"]["w"], 100)

    def test_rotated_node_and_ancestor_rendered_unrotated(self):
        doc_nodes, proto, jobs, parent = basic()
        doc_nodes[3]["rotation"] = 30
        proto[2]["rotation"] = 30
        doc, w = make(doc_nodes, proto, jobs, parent)
        start = doc.snapshot()
        assets = render.render_all(doc, w)
        nodes = w["proto"]["nodes"]
        self.assertNotIn("rotated", svg_of(assets, nodes["3"]["paint"]))
        self.assertNotIn("rotated", svg_of(assets, nodes["4"]["paint"]))
        self.assertEqual(doc.snapshot(), start)

    def test_strip_effects_blend_opacity_and_unhide(self):
        doc_nodes, proto, jobs, parent = basic()
        doc_nodes[2].update({"opacity": 0.5, "blend": "multiply", "visible": False,
                             "effects": [{"type": "backgroundBlur", "radius": 12, "visible": True},
                                         {"type": "innerShadow", "radius": 2, "visible": True}]})
        jobs[1] = job("2", 2, strip=["backgroundBlur", "blend", "opacity"], unhide=[2])
        doc, w = make(doc_nodes, proto, jobs, parent)
        start = doc.snapshot()
        assets = render.render_all(doc, w)
        svg = svg_of(assets, w["proto"]["nodes"]["2"]["paint"])
        self.assertIn("effect=innerShadow", svg)
        for gone in ("backgroundBlur", "blend=", "opacity="):
            self.assertNotIn(gone, svg)
        self.assertEqual(doc.snapshot(), start)

    def test_mask_for_sets_group_mask_src_and_empty_paint_is_null(self):
        doc_nodes, proto, jobs, parent = basic()
        doc_nodes[3]["fills"] = []                  # a container with nothing of its own
        doc_nodes[4]["isMask"] = True               # drawn only once it is not a mask any more
        jobs[3]["mask_for"] = "3"
        doc, w = make(doc_nodes, proto, jobs, parent)
        start = doc.snapshot()
        assets = render.render_all(doc, w)
        nodes = w["proto"]["nodes"]
        self.assertIsNone(nodes["3"]["paint"])
        self.assertEqual(nodes["3"]["css"]["maskSrc"], nodes["4"]["paint"]["src"])
        self.assertIn("#222222", svg_of(assets, nodes["4"]["paint"]))
        self.assertEqual(doc.snapshot(), start)

    def test_gradient_fill_or_stroke_rendered_as_png(self):
        # FigCraft's SVG writes gradients in user space: wrong angle on non-square layers
        doc_nodes, proto, jobs, parent = basic()
        doc_nodes[2]["fills"] = [{"type": "gradient", "kind": "linear", "color": "#123456"}]
        doc_nodes[4]["strokes"] = [{"type": "gradient", "kind": "radial", "visible": True}]
        doc, w = make(doc_nodes, proto, jobs, parent)
        render.render_all(doc, w)
        nodes = w["proto"]["nodes"]
        self.assertEqual((nodes["2"]["paint"]["src"], nodes["4"]["paint"]["src"]), ("assets/2.png", "assets/4.png"))
        self.assertEqual(nodes["3"]["paint"]["src"], "assets/3.svg")

    def test_text_svg_padded_so_overflowing_glyphs_show(self):
        doc_nodes, proto, jobs, parent = basic()
        doc_nodes[4].update({"type": "TEXT", "fontSize": 20, "characters": "Maya"})
        doc, w = make(doc_nodes, proto, jobs, parent)
        assets = render.render_all(doc, w)
        p = w["proto"]["nodes"]["4"]["paint"]
        self.assertEqual(p, {"src": "assets/4.svg", "dx": -10, "dy": -10, "w": 120, "h": 80})
        svg = svg_of(assets, p)
        self.assertTrue(svg.startswith('<svg width="120" height="80" viewBox="-10 -10 120 80"'), svg[:80])

    def test_image_fill_rendered_as_png_at_scale(self):
        doc_nodes, proto, jobs, parent = basic()
        doc_nodes[2]["fills"] = [{"type": "image", "image": "abc", "color": "#123456"}]
        doc, w = make(doc_nodes, proto, jobs, parent)
        assets = render.render_all(doc, w, scale=3)
        p = w["proto"]["nodes"]["2"]["paint"]
        self.assertEqual(p, {"src": "assets/2.png", "dx": 0, "dy": 0, "w": 100, "h": 60})
        data = {a["path"]: a["data"] for a in assets}["assets/2.png"]
        self.assertEqual(int.from_bytes(data[16:20], "big"), 300)
        pngs = [p for p in calls(doc, "file.export") if p["format"] == "png"]
        self.assertEqual(pngs, [{"ids": [2], "format": "png", "scale": 3}])



class SvgParsingTests(unittest.TestCase):
    """Strings trimmed from real FigCraft 0.18.1 `file.export` replies (task 9 probe)."""
    SHADOW = ('<svg width="152" height="112" viewBox="0 0 152 112" fill="none" xmlns="http://www.w3.org/2000/svg">'
              '<g opacity="0.502"><g filter="url(#filter1)"><path transform="matrix(1 0 0 1 26 26)" d="M0 0L100 0L100 60L0 60Z" fill="#000000"/></g></g>'
              '<g style="mix-blend-mode:multiply"><path transform="matrix(1 0 0 1 16 22)" d="M0 0L100 0L100 60L0 60Z" fill="#00AAFF"/></g>'
              '<defs><filter id="filter1" filterUnits="userSpaceOnUse" x="-8" y="-8" width="168" height="128"/></defs></svg>')
    SHADOW_BOX = ('<svg width="100" height="60" viewBox="0 0 100 60" fill="none" xmlns="http://www.w3.org/2000/svg">'
                  '<g opacity="0.502"><g filter="url(#filter1)"><path transform="matrix(1 0 0 1 10 4)" d="M0 0L100 0L100 60L0 60Z" fill="#000000"/></g></g>'
                  '<g style="mix-blend-mode:multiply"><path transform="matrix(1 0 0 1 0 0)" d="M0 0L100 0L100 60L0 60Z" fill="#00AAFF"/></g></svg>')
    EMPTY = ('<svg width="390" height="844" viewBox="0 0 390 844" fill="none" xmlns="http://www.w3.org/2000/svg"><g></g>'
             '<defs><clipPath id="clip1"><path d="M0 0L390 0L390 844L0 844Z"/></clipPath></defs></svg>')
    HIDDEN = '<svg width="40" height="20" viewBox="0 0 40 20" fill="none" xmlns="http://www.w3.org/2000/svg"></svg>'

    def test_offset_is_the_difference_of_the_first_translations(self):
        own, box = render._origin(self.SHADOW), render._origin(self.SHADOW_BOX)
        self.assertEqual((box[0] - own[0], box[1] - own[1]), (-16, -22))
        self.assertEqual(render._size(self.SHADOW), (152, 112))
        self.assertEqual(render._origin('<svg><path transform="matrix(0.866025 -0.5 0.5 0.866025 0 50)"/></svg>'), (0, 50))

    def test_empty_exports_draw_nothing(self):
        self.assertFalse(render._draws(self.EMPTY))
        self.assertFalse(render._draws(self.HIDDEN))
        self.assertTrue(render._draws(self.SHADOW))

    def test_pad_keeps_the_rest_of_the_root_tag(self):
        out = render._pad(self.SHADOW_BOX, 4)
        self.assertTrue(out.startswith('<svg width="108" height="68" viewBox="-4 -4 108 68" fill="none" xmlns='), out[:90])
        self.assertEqual(out.count("<svg"), 1)


if __name__ == "__main__":
    unittest.main()
