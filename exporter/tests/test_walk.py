import copy
import unittest

from figcraft_export import docfile, walk
from tests.fake_control import FakeControl, canonical, load_fixture

SCENARIO = load_fixture("walk_scenario")
EXTRAS = docfile.extras(load_fixture("saveas_scenario")["reply"])


def scenario(selection=None, edit=None):
    """FakeControl over the recorded scenario; `edit(replies_by_cmd_id)` may change replies."""
    calls = copy.deepcopy(SCENARIO["calls"])
    byid = {}
    for cmd, params, reply in calls:
        byid[(cmd, params.get("id"))] = reply
    if selection is not None:
        byid[("document.inspect", None)]["selection"] = list(selection)
    if edit:
        edit(byid)
    replies = {}
    for cmd, params, reply in calls:
        replies[(cmd, canonical(params))] = byid[(cmd, params.get("id"))]
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

    def test_panel_groups_by_section_in_layer_order(self):
        w = walk.walk(scenario(), EXTRAS)
        p = w["proto"]
        self.assertEqual(p["panel"], [
            {"section": None, "screens": ["146", "163"]},
            {"section": "Parcours", "screens": ["160", "161"]},
        ])
        self.assertEqual(p["pageName"], "Scénario")
        self.assertEqual(p["title"], "Ridgeline onboarding")
        self.assertEqual(w["page_id"], "145")
        self.assertEqual(p["version"], 1)

    def test_start_is_flow_start_when_selected_else_first(self):
        self.assertEqual(walk.walk(scenario(), EXTRAS)["proto"]["start"], "160")
        w = walk.walk(scenario(selection=[163, 146, 161]), EXTRAS)
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
        self.assertEqual(a["variants"]["State=Default"], ["184"])
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
        self.assertTrue(self.jobs["183"]["hide_children"])
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


if __name__ == "__main__":
    unittest.main()
