import copy
import unittest

from figcraft_export import docfile, walk
from tests.fake_control import FakeControl, canonical, load_fixture

SCENARIO = load_fixture("walk_scenario")
VARIANTS = load_fixture("walk_variants")
EXTRAS = docfile.extras(load_fixture("saveas_scenario")["reply"])


def scenario(selection=None, edit=None, fixture=None):
    """FakeControl over a recorded scenario; `edit(replies_by_cmd_id)` may change or add
    replies (keys (command, id); an added key becomes a reply for {"id": id})."""
    calls = copy.deepcopy((fixture or SCENARIO)["calls"])
    byid = {}
    for cmd, params, reply in calls:
        byid[(cmd, params.get("id"))] = reply
    if selection is not None:
        byid[("document.inspect", None)]["selection"] = list(selection)
    if edit:
        edit(byid)
    replies = {}
    for (cmd, i), reply in byid.items():
        replies[(cmd, canonical({"depth": 0} if cmd == "document.inspect" else {} if i is None else {"id": i}))] = reply
    return FakeControl(replies)


def node_get(byid, i):
    return byid[("node.get", i)]


def child(byid, parent, cid):
    return [c for c in node_get(byid, parent)["children"] if c["id"] == cid][0]


class WalkSelectionTests(unittest.TestCase):
    def test_empty_selection_errors_in_french(self):
        with self.assertRaises(walk.WalkError) as cm:
            walk.walk(scenario(selection=[]), EXTRAS)
        self.assertEqual(str(cm.exception), "Sélectionnez au moins une frame de premier niveau.")

    def test_only_invalid_selection_errors_too(self):
        with self.assertRaises(walk.WalkError) as cm:
            walk.walk(scenario(selection=[164]), EXTRAS)
        self.assertEqual(str(cm.exception), "Sélectionnez au moins une frame de premier niveau.")

    def test_non_frame_and_nested_skipped_and_reported(self):
        w = walk.walk(scenario(), EXTRAS)
        skipped = " ".join(w["proto"]["report"]["skipped"])
        self.assertIn("Rectangle libre", skipped)
        self.assertIn("CTA", skipped)
        self.assertTrue(any("Rectangle libre" in m for m in w["warnings"]))
        self.assertNotIn("164", w["proto"]["screens"])
        # the nested CTA is still exported as a layer of its screen, never as a screen
        self.assertNotIn("150", w["proto"]["screens"])
        self.assertIn("150", w["proto"]["nodes"])

    def test_panel_groups_by_section_in_canvas_reading_order(self):
        w = walk.walk(scenario(), EXTRAS)
        p = w["proto"]
        self.assertEqual(p["panel"], [
            # canvas reading order: rows by top y (overlapping ranges share a row), then x
            {"section": None, "screens": ["146", "163"]},
            {"section": "Parcours", "screens": ["160", "161"]},
        ])
        self.assertEqual(p["pageName"], "Scénario")
        self.assertEqual(p["title"], "Ridgeline onboarding")
        self.assertEqual(w["page_id"], "145")
        self.assertEqual(p["version"], 1)

    def test_sections_ordered_by_their_first_frame(self):
        def move(byid):
            [c for c in node_get(byid, 145)["children"] if c["id"] == 146][0]["x"] = 3000.0
        p = walk.walk(scenario(edit=move), EXTRAS)["proto"]
        self.assertEqual(p["panel"], [
            {"section": "Parcours", "screens": ["160", "161"]},
            {"section": None, "screens": ["163", "146"]},
        ])

    def test_selected_section_expands_to_its_frames(self):
        w = walk.walk(scenario(selection=[169]), EXTRAS)
        self.assertEqual(w["proto"]["panel"], [{"section": "Parcours", "screens": ["160", "161"]}])
        self.assertFalse([m for m in w["warnings"] if "Parcours" in m])
        # with other frames: no duplicates, reading order kept
        w = walk.walk(scenario(selection=[146, 169, 160]), EXTRAS)
        self.assertEqual(w["proto"]["panel"], [{"section": None, "screens": ["146"]},
                                               {"section": "Parcours", "screens": ["160", "161"]}])

    def test_nested_sections_expand_recursively(self):
        def nest(byid):
            sec = node_get(byid, 169)
            fin = [c for c in sec["children"] if c["id"] == 161][0]
            sub = {"id": 900, "name": "Sous-partie", "type": "SECTION", "x": 500.0, "y": 0.0,
                   "width": 450.0, "height": 900.0, "childCount": 1}
            sec["children"] = [c for c in sec["children"] if c["id"] != 161] + [sub]
            byid[("node.get", 900)] = dict(sub, children=[dict(fin, x=40.0, y=40.0)])
        w = walk.walk(scenario(selection=[169], edit=nest), EXTRAS)
        self.assertEqual(w["proto"]["panel"], [{"section": "Parcours", "screens": ["160"]},
                                               {"section": "Sous-partie", "screens": ["161"]}])
        w = walk.walk(scenario(selection=[900], edit=nest), EXTRAS)
        self.assertEqual(w["proto"]["panel"], [{"section": "Sous-partie", "screens": ["161"]}])

    def test_skip_message_names_frames_and_sections(self):
        w = walk.walk(scenario(), EXTRAS)
        self.assertIn("« Rectangle libre » ignoré : seules les frames et sections de premier niveau sont exportées.",
                      w["proto"]["report"]["skipped"])

    def test_reading_order_rows_then_x(self):
        boxes = {"A": (0, 0, 100, 100), "B": (200, 10, 100, 100), "C": (0, 300, 100, 100),
                 "D": (500, -50, 100, 60), "E": (-100, 320, 50, 50)}
        self.assertEqual(walk.reading_order(boxes), ["A", "B", "D", "E", "C"])
        # four screens side by side, listed in reverse layer order: 1, 2, 3, 4
        four = {"4": (1500, 0, 390, 844), "3": (1000, 0, 390, 844), "2": (500, 0, 390, 844), "1": (0, 0, 390, 844)}
        self.assertEqual(walk.reading_order(four), ["1", "2", "3", "4"])

    def test_start_is_flow_start_when_selected_else_first(self):
        self.assertEqual(walk.walk(scenario(), EXTRAS)["proto"]["start"], "160")
        w = walk.walk(scenario(selection=[146, 163, 161]), EXTRAS)
        self.assertEqual(w["proto"]["start"], "146")


class WalkClosureTests(unittest.TestCase):
    def test_closure_follows_navigate_overlay_changeto_across_pages_not_listed_in_panel(self):
        w = walk.walk(scenario(selection=[146]), EXTRAS)
        screens = w["proto"]["screens"]
        # 146 -CTA-> 160 -Suivant-> 170 (page Annexes) -> 146; Menu -overlay-> 162
        self.assertEqual(set(screens), {"146", "160", "162", "170"})
        listed = [s for g in w["proto"]["panel"] for s in g["screens"]]
        self.assertEqual(listed, ["146"])
        self.assertEqual(screens["170"]["name"], "Paramètres")

    def test_closure_through_variant_interactions(self):
        # 163 holds Bouton instances; variant State=Pressed navigates to Fin (161)
        w = walk.walk(scenario(selection=[163]), EXTRAS)
        self.assertIn("161", w["proto"]["screens"])

    def test_closure_terminates_on_cycles(self):
        ctl = scenario()
        w = walk.walk(ctl, EXTRAS)
        gets = [p["id"] for c, p in ctl.calls if c == "node.get"]
        self.assertEqual(len(gets), len(set(gets)), "node.get repeated: %r" % gets)
        self.assertIn("170", w["proto"]["screens"])  # 170 -> 146 -> 160 -> 170

    def test_missing_destination_reported_not_fatal(self):
        w = walk.walk(scenario(), EXTRAS)
        msgs = [m for m in w["warnings"] if "185" in m]
        self.assertEqual(len(msgs), 1)
        self.assertIn("Recommencer", msgs[0])
        self.assertTrue(any("185" in s for s in w["proto"]["report"]["skipped"]))
        self.assertNotIn("185", w["proto"]["screens"])

    def test_missing_destination_as_control_error_also_reported(self):
        from figcraft_export.control import ControlError

        def edit(byid):
            byid[("node.get", 162)] = ControlError("no such layer")
        w = walk.walk(scenario(edit=edit), EXTRAS)
        self.assertNotIn("162", w["proto"]["screens"])
        self.assertTrue(any("162" in m for m in w["warnings"]))

    def test_unknown_interaction_kind_reported_and_skipped(self):
        def edit(byid):
            c = child(byid, 146, 158)
            c["interactions"].append({"trigger": {"type": "onWink"}, "actions": [{"type": "back"}]})
        w = walk.walk(scenario(edit=edit), EXTRAS)
        menu = w["proto"]["nodes"]["158"]
        self.assertEqual(len(menu["interactions"]), 1)
        self.assertTrue(any("Menu" in m and "onWink" in m for m in w["warnings"]))


class WalkVariantTests(unittest.TestCase):
    def setUp(self):
        self.w = walk.walk(scenario(), EXTRAS)
        self.nodes = self.w["proto"]["nodes"]

    def test_variant_interactions_read_from_component_node(self):
        inst = self.nodes["183"]["instance"]
        vi = inst["variantInteractions"]
        hover = vi["State=Default"][0]
        self.assertEqual(hover["trigger"], {"type": "hover"})
        self.assertEqual(hover["actions"][0]["type"], "changeTo")
        self.assertEqual(hover["actions"][0]["variant"], "State=Hover")
        self.assertEqual(vi["State=Hover"][0]["trigger"], {"type": "press"})
        self.assertEqual(vi["State=Pressed"][0]["actions"][0], {
            "type": "navigate", "dest": "161",
            "transition": {"type": "dissolve", "durationMs": 300, "easing": {"type": "easeOut"}}})
        self.assertEqual(self.nodes["183"]["interactions"], [])
        own = self.nodes["181"]["interactions"][0]
        self.assertEqual(own["actions"][0]["variant"], "State=Disabled")

    def test_instance_lists_reachable_variants_only(self):
        a = self.nodes["183"]["instance"]
        self.assertEqual(a["set"], "Bouton")
        self.assertEqual(a["variant"], "State=Default")
        self.assertEqual(set(a["variants"]), {"State=Default", "State=Hover", "State=Pressed"})
        self.assertEqual(a["variants"]["State=Default"], ["183~State=Default~self", "184"])
        self.assertEqual(self.nodes["183"]["children"], a["variants"]["State=Default"])
        self.assertEqual(a["variants"]["State=Hover"], [])  # filled by Task 9
        b = self.nodes["181"]["instance"]
        self.assertEqual(set(b["variants"]), {"State=Default", "State=Hover", "State=Pressed", "State=Disabled"})
        jobs = [(j["instance"], j["variant"]) for j in self.w["jobs"] if j["kind"] == "variant"]
        self.assertEqual(sorted(jobs), sorted([
            ("181", "State=Hover"), ("181", "State=Pressed"), ("181", "State=Disabled"),
            ("183", "State=Hover"), ("183", "State=Pressed")]))
        j = [j for j in self.w["jobs"] if j["kind"] == "variant" and j["instance"] == "183" and j["variant"] == "State=Hover"][0]
        self.assertEqual(j["node"], "183")
        self.assertEqual(j["fc_id"], 183)
        self.assertEqual(j["variant_fc_id"], 174)
        self.assertEqual(j["properties"], {"State": "Hover"})
        self.assertEqual(self.nodes["183"]["kind"], "instance")


class WalkHiddenTests(unittest.TestCase):
    def test_layers_in_hidden_instance_kept_and_jobs_say_what_to_unhide(self):
        def edit(byid):
            child(byid, 163, 183)["visible"] = False
            node_get(byid, 183)["visible"] = False
        w = walk.walk(scenario(selection=[163], edit=edit), EXTRAS)
        self.assertIs(w["proto"]["nodes"]["183"]["visible"], False)
        self.assertIn("184", w["proto"]["nodes"])
        own = [j for j in w["jobs"] if j["node"] == "184"][0]
        self.assertEqual(own["unhide"], [183])
        self.assertEqual([j for j in w["jobs"] if j["node"] == "183~State=Default~self"][0]["unhide"], [183])
        var = [j for j in w["jobs"] if j["kind"] == "variant" and j["instance"] == "183"]
        self.assertTrue(var)
        for j in var:
            self.assertEqual(j["unhide"], [183])


class WalkNodeTests(unittest.TestCase):
    def setUp(self):
        self.w = walk.walk(scenario(), EXTRAS)
        self.nodes = self.w["proto"]["nodes"]
        self.jobs = {}
        for j in self.w["jobs"]:
            if j["kind"] == "own":
                self.jobs[j["node"]] = j

    def test_screen_and_root_geometry(self):
        s = self.w["proto"]["screens"]["146"]
        self.assertEqual(s, {"name": "Accueil", "width": 390, "height": 844, "background": "#FFFFFF",
                             "root": "146", "overflow": "vertical"})
        root = self.nodes["146"]
        self.assertEqual((root["x"], root["y"], root["kind"]), (0, 0, "frame"))
        self.assertEqual(root["children"][:3], ["147", "148", "149"])
        self.assertIsNone(root["paint"])
        self.assertEqual(root["alts"], [])
        self.assertEqual(self.w["bound"]["146"], {"fill": "VariableID:4"})
        self.assertEqual(self.w["parent"]["147"], "146")
        self.assertEqual(self.w["proto"]["variables"], {"collections": {}, "vars": {}})

    def test_text_bound_to_string_or_number_var_becomes_live_text_with_style(self):
        t = self.nodes["147"]
        self.assertEqual(t["kind"], "text")
        self.assertEqual(t["liveText"], {"var": "VariableID:1", "style": {
            "fontFamily": "Inter", "fontSize": 20, "fontWeight": 700, "lineHeight": 30,
            "letterSpacing": 1, "color": "#222222", "align": "center"}})
        n = self.nodes["148"]["liveText"]
        self.assertEqual(n["var"], "VariableID:2")
        self.assertIsNone(n["style"]["lineHeight"])
        self.assertEqual(n["style"]["fontWeight"], 400)
        self.assertNotIn("147", self.jobs)  # live text is not rendered
        self.assertIsNone(self.nodes["151"]["liveText"])  # unbound text stays a rendered paint
        self.assertIn("151", self.jobs)

    def test_live_text_with_a_bound_colour_names_its_variable(self):
        def bind(byid):
            child(byid, 146, 147).setdefault("boundVariables", {})["fill"] = "VariableID:4"
        w = walk.walk(scenario(edit=bind), EXTRAS)
        lt = w["proto"]["nodes"]["147"]["liveText"]
        self.assertEqual(lt["colorVar"], "VariableID:4")
        self.assertEqual(lt["style"]["color"], "#222222")            # fallback colour kept
        self.assertNotIn("colorVar", self.nodes["148"]["liveText"])

    def test_screen_modes_from_its_page_and_its_own_explicit_modes(self):
        th = "VariableCollectionId:2"
        ex = copy.deepcopy(EXTRAS)
        ex["145"] = {"overflow": "none", "position": "scroll", "varModes": {th: th + "/mode2"}}
        ex.setdefault("146", {"overflow": "none", "position": "scroll", "varModes": {}})["page"] = "145"
        ex["163"]["page"] = "145"
        ex["163"]["varModes"] = {th: th + "/mode1"}
        w = walk.walk(scenario(), ex)
        self.assertEqual(w["proto"]["screens"]["146"]["modes"], {th: th + "/mode2"})
        self.assertEqual(w["proto"]["screens"]["163"]["modes"], {th: th + "/mode1"})   # frame wins
        self.assertEqual(w["page_modes"]["146"], {th: th + "/mode2"})
        self.assertNotIn("modes", w["proto"]["screens"]["160"])

    def test_visible_bound_to_boolean_var_sets_bindings_visible(self):
        b = self.nodes["149"]
        self.assertEqual(b["bindings"], {"visible": "VariableID:3"})
        self.assertIs(b["visible"], False)
        self.assertEqual(self.jobs["149"]["unhide"], [149])
        self.assertEqual(self.nodes["147"]["bindings"], {})

    def test_overflow_position_from_docfile_extras(self):
        self.assertEqual(self.nodes["146"]["overflow"], "vertical")
        self.assertEqual(self.nodes["157"]["position"], "fixed")
        self.assertEqual(self.nodes["152"]["position"], "scroll")
        self.assertEqual(self.nodes["152"]["overflow"], "none")
        self.assertEqual(self.w["explicit_modes"], {"163": {"VariableCollectionId:2": "VariableCollectionId:2/mode2"}})

    def test_container_job_hides_children(self):
        self.assertTrue(self.jobs["146"]["hide_children"])
        self.assertTrue(self.jobs["150"]["hide_children"])
        self.assertNotIn("183", self.jobs)  # an instance paints through its ~self child
        self.assertTrue(self.jobs["183~State=Default~self"]["hide_children"])
        self.assertFalse(self.jobs["152"]["hide_children"])
        self.assertFalse(self.jobs["157"]["hide_children"])  # frame without children
        self.assertEqual(self.jobs["146"]["fc_id"], 146)
        self.assertNotIn("159", self.jobs)  # groups have no paint of their own
        self.assertEqual(self.nodes["150"]["css"], {"radius": [12, 12, 12, 12]})
        self.assertTrue(self.nodes["150"]["clip"])

    def test_backdrop_blur_blend_mask_jobs_strip_effects_and_set_css(self):
        self.assertEqual(self.nodes["152"]["css"], {"backdropBlur": 12})
        self.assertEqual(self.jobs["152"]["strip_effects"], ["backgroundBlur"])
        self.assertEqual(self.nodes["153"]["css"], {"blend": "multiply"})
        self.assertEqual(self.jobs["153"]["strip_effects"], ["blend"])
        grp = self.nodes["159"]
        self.assertEqual(grp["kind"], "group")
        self.assertEqual(grp["children"], ["156"])  # the mask layer is not drawn
        self.assertEqual(self.jobs["155"]["mask_for"], "159")
        self.assertEqual((self.nodes["156"]["x"], self.nodes["156"]["y"]), (0, 0))  # group-relative
        approx = " ".join(self.w["proto"]["report"]["approximated"])
        for name in ("Verre", "Mult", "Mask group"):
            self.assertIn(name, approx)

    def test_rotation_kept_with_unrotated_box(self):
        r = self.nodes["154"]
        self.assertEqual((r["x"], r["y"], r["w"], r["h"], r["rotation"]), (256.7, 227.68, 100, 40, 30))

    def test_actions_exposed_for_variables(self):
        types = {a["type"] for a in self.w["actions"]}
        self.assertIn("navigate", types)
        self.assertIn("changeTo", types)


class WalkReviewFixTests(unittest.TestCase):
    """Task 7 review fix round 1."""

    def test_instance_paint_goes_to_synthetic_self_node(self):
        def edit(byid):
            for c in node_get(byid, 163)["children"]:
                if c["id"] == 183:
                    c.update({"blend": "multiply", "opacity": 0.5,
                              "effects": [{"type": "backgroundBlur", "radius": 6, "visible": True}]})
        w = walk.walk(scenario(selection=[163], edit=edit), EXTRAS)
        n = w["proto"]["nodes"]
        self_id = "183~State=Default~self"
        s = n[self_id]
        self.assertEqual((s["kind"], s["x"], s["y"], s["w"], s["h"], s["rotation"]), ("leaf", 0, 0, 120, 48, 0))
        self.assertEqual((s["opacity"], s["css"], s["interactions"], s["paint"]), (1, {}, [], None))
        self.assertIsNone(s["instance"])
        self.assertEqual(n["183"]["css"]["blend"], "multiply")
        self.assertEqual(n["183"]["paint"], None)
        job = [j for j in w["jobs"] if j["node"] == self_id][0]
        self.assertEqual(job["fc_id"], 183)
        self.assertTrue(job["hide_children"])
        self.assertEqual(sorted(job["strip_effects"]), ["backgroundBlur", "blend", "opacity"])
        self.assertEqual(w["parent"][self_id], "183")
        self.assertEqual(w["bound"].get(self_id), w["bound"].get("183"))

    def test_nested_instances_in_variant_components_followed_not_counted(self):
        w = walk.walk(scenario(fixture=VARIANTS), {})
        screens = set(w["proto"]["screens"])
        # 201 via Zone, 202 via the nested Puce of the current variant,
        # 203 via the nested Puce inside the non-current variant Mode=B
        self.assertEqual(screens, {"187", "201", "202", "203"})
        inst = w["proto"]["nodes"]["197"]["instance"]
        self.assertEqual(set(inst["variants"]), {"Mode=A", "Mode=B"})
        nested = w["proto"]["nodes"]["199"]["instance"]
        self.assertEqual(nested["set"], "Puce")
        self.assertEqual(set(nested["variants"]), {"Etat=On", "Etat=Off"})

    def test_instance_children_carry_component_descendant_interactions(self):
        # measured live: node.get of an instance child returns the component child's interactions
        w = walk.walk(scenario(fixture=VARIANTS), {})
        zone = w["proto"]["nodes"]["198"]
        self.assertEqual(zone["interactions"][0]["actions"][0]["dest"], "201")

    def test_actions_include_variant_descendants(self):
        w = walk.walk(scenario(fixture=VARIANTS), {})
        sets = [a for a in w["actions"] if a["type"] == "setVariable"]
        self.assertEqual(len(sets), 1)  # Zone of the non-current variant Mode=B
        self.assertEqual(sets[0]["variable"], "VariableID:2")
        self.assertIn("openOverlay", {a["type"] for a in w["actions"]})

    def test_mask_job_is_the_mask_layers_own_and_group_mask_flattened(self):
        def edit(byid):
            grp = node_get(byid, 159)
            m = grp["children"][0]
            m.update({"type": "GROUP", "childCount": 2})
            # a live text right before would make jobs[-1] wrong
            grp["children"].insert(1, {"id": 999, "type": "RECTANGLE", "name": "x", "width": 1, "height": 1})
        w = walk.walk(scenario(selection=[146], edit=edit), EXTRAS)
        n = w["proto"]["nodes"]
        self.assertEqual(n["155"]["children"], [])
        mjob = [j for j in w["jobs"] if j.get("mask_for")]
        self.assertEqual(len(mjob), 1)
        self.assertEqual(mjob[0]["node"], "155")
        self.assertEqual(mjob[0]["mask_for"], "159")
        self.assertFalse(mjob[0]["hide_children"])
        self.assertNotIn("mask_for", [j for j in w["jobs"] if j["node"] == "999"][0])

    def test_missing_variant_destination_reported_not_emitted(self):
        def edit(byid):
            for c in node_get(byid, 163)["children"]:
                if c["id"] == 181:
                    c["interactions"][0]["actions"][0]["dest"] = 9999
            node_get(byid, 181)["interactions"][0]["actions"][0]["dest"] = 9999
            byid[("node.get", 9999)] = None
        w = walk.walk(scenario(selection=[163], edit=edit), EXTRAS)
        msgs = [m for m in w["warnings"] if "9999" in m]
        self.assertEqual(msgs, ["Lien ignoré : la variante 9999 du calque « Bouton » est introuvable."])
        n = w["proto"]["nodes"]["181"]
        self.assertEqual(n["interactions"], [])
        self.assertEqual(set(n["instance"]["variants"]), {"State=Default", "State=Hover", "State=Pressed"})
        for a in w["actions"]:
            if a["type"] == "changeTo":
                self.assertNotEqual(a["variant"], "9999")


class NestedOwnerTests(unittest.TestCase):
    """A "Change to" on a nested component (Button inside Card) that targets a variant of
    the parent component (Card) switches the Card instance, not the Button."""

    def walker(self):
        props = lambda cid, st: (("component.properties", canonical({"id": cid})), {"set": st})
        ctl = FakeControl(dict([props(31, 30), props(41, 40), props(42, 40), props(50, None)]))
        w = walk._Walker(ctl, {})
        w.parent = {"159": "1", "160": "159", "161": "160"}
        w.inst_main = {"159": 41, "160": 31}   # Card (set 40) contains Button (set 30)
        return w, ctl

    def test_parent_variant_goes_to_the_parent_instance(self):
        w, _ = self.walker()
        self.assertEqual(w._owner("160", 42), "159")

    def test_own_set_variant_stays_on_the_nested_instance(self):
        w, ctl = self.walker()
        ctl.replies[("component.properties", canonical({"id": 32}))] = {"set": 30}
        self.assertEqual(w._owner("160", 32), "160")

    def test_unrelated_component_stays_on_the_nearest_instance(self):
        w, _ = self.walker()
        self.assertEqual(w._owner("160", 50), "160")

    def test_not_nested_asks_nothing(self):
        w, ctl = self.walker()
        self.assertEqual(w._owner("159", 42), "159")
        self.assertEqual(ctl.calls, [])


if __name__ == "__main__":
    unittest.main()
