import unittest

from figcraft_export import variables
from tests.fake_control import FakeControl, load_fixture

THEME = "VariableCollectionId:1"
L, D = THEME + "/mode1", THEME + "/mode2"
SIZE = "VariableCollectionId:2"
S1, S2, S3 = SIZE + "/m1", SIZE + "/m2", SIZE + "/m3"


def rgb(r, g, b, a=1.0):
    return {"type": "color", "value": {"r": r, "g": g, "b": b, "a": a}}


def raw():
    return {
        "collections": [
            {"id": THEME, "name": "Theme", "modes": [{"id": L, "name": "Light"}, {"id": D, "name": "Dark"}]},
            {"id": SIZE, "name": "Size", "modes": [{"id": S1, "name": "S"}, {"id": S2, "name": "M"},
                                                  {"id": S3, "name": "L"}]},
        ],
        "variables": [
            {"id": "VariableID:1", "name": "surface", "collection": THEME, "resolvedType": "color",
             "values": {L: rgb(1, 1, 1), D: rgb(0, 0, 0, 0.5)}},
            {"id": "VariableID:2", "name": "gap", "collection": THEME, "resolvedType": "number",
             "values": {L: {"type": "number", "value": 8.0}, D: {"type": "number", "value": 16.0}}},
            {"id": "VariableID:3", "name": "accent", "collection": SIZE, "resolvedType": "color",
             "values": {S1: rgb(1, 0, 0), S2: rgb(0, 1, 0), S3: rgb(0, 0, 1)}},
        ],
    }


def walked(nodes=None, jobs=None, actions=None, explicit=None, parent=None):
    return {"proto": {"nodes": nodes or {}, "variables": {}}, "jobs": jobs or [], "warnings": [],
            "bound": {n: v for n, v in (nodes or {}).items()} and {}, "explicit_modes": explicit or {},
            "parent": parent or {}, "actions": actions or []}


class ReadTests(unittest.TestCase):
    def test_colour_values_become_css_rgba(self):
        v = variables.parse(raw())
        self.assertEqual(v["vars"]["VariableID:1"]["valuesByMode"],
                         {L: "rgba(255, 255, 255, 1)", D: "rgba(0, 0, 0, 0.5)"})
        self.assertEqual(v["vars"]["VariableID:2"]["valuesByMode"], {L: 8, D: 16})
        self.assertEqual(v["vars"]["VariableID:1"]["type"], "color")
        self.assertEqual(v["vars"]["VariableID:2"]["type"], "number")

    def test_collections_and_default_mode(self):
        v = variables.parse(raw())
        self.assertEqual(v["collections"][THEME],
                         {"name": "Theme", "defaultMode": L, "modes": {L: "Light", D: "Dark"}})
        self.assertEqual(v["vars"]["VariableID:3"]["collection"], SIZE)

    def test_read_calls_variable_list(self):
        ctl = FakeControl({("variable.list", "{}"): raw()})
        self.assertIn("VariableID:1", variables.read(ctl)["vars"])

    def test_fixture_parses(self):
        v = variables.parse(load_fixture("variables")["design_system_with_probe"])
        self.assertEqual(v["collections"]["VariableCollectionId:1"]["defaultMode"], "VariableCollectionId:1/mode1")
        self.assertEqual(variables.parse(load_fixture("variables")["onboarding"]),
                         {"collections": {}, "vars": {}})


class ReachTests(unittest.TestCase):
    def setUp(self):
        self.v = variables.parse(raw())

    def test_defaults_always_reachable(self):
        r = variables.reachable(self.v, [])
        self.assertEqual(r["modes"], {THEME: [L], SIZE: [S1]})
        self.assertEqual(r["values"]["VariableID:1"], ["rgba(255, 255, 255, 1)"])
        self.assertEqual(r["open"], [])

    def test_set_variable_literal_adds_value(self):
        acts = [{"type": "setVariable", "variable": "VariableID:1", "value": {"r": 1, "g": 0, "b": 0, "a": 1}},
                {"type": "setVariable", "variable": "VariableID:2", "value": 40}]
        r = variables.reachable(self.v, acts)
        self.assertEqual(r["values"]["VariableID:1"], ["rgba(255, 255, 255, 1)", "rgba(255, 0, 0, 1)"])
        self.assertEqual(r["values"]["VariableID:2"], [8, 40])
        self.assertEqual(r["set"]["VariableID:1"], ["rgba(255, 0, 0, 1)"])

    def test_set_mode_adds_mode(self):
        acts = [{"type": "setVariableMode", "collection": THEME, "mode": D},
                {"type": "setVariableMode", "collection": THEME, "mode": D},
                {"type": "setVariableMode", "collection": "nope", "mode": D}]
        r = variables.reachable(self.v, acts)
        self.assertEqual(r["modes"][THEME], [L, D])
        self.assertEqual(r["modes"][SIZE], [S1])

    def test_expr_driven_colour_marked_open(self):
        acts = [{"type": "setVariable", "variable": "VariableID:1", "expr": {"op": "x"}}]
        r = variables.reachable(self.v, acts)
        self.assertEqual(r["open"], ["VariableID:1"])
        self.assertEqual(r["values"]["VariableID:1"], ["rgba(255, 255, 255, 1)"])


class AlternativesTests(unittest.TestCase):
    def setUp(self):
        self.v = variables.parse(raw())

    def test_no_reach_no_alts(self):
        r = variables.reachable(self.v, [])
        self.assertEqual(variables.alternatives({"fill": "VariableID:1"}, [THEME], r), ([], False))

    def test_modes_alts(self):
        r = variables.reachable(self.v, [{"type": "setVariableMode", "collection": THEME, "mode": D}])
        whens, capped = variables.alternatives({"fill": "VariableID:1"}, [THEME], r)
        self.assertEqual(whens, [{"modes": {THEME: D}}])
        self.assertFalse(capped)

    def test_pinned_collection_not_varied(self):
        r = variables.reachable(self.v, [{"type": "setVariableMode", "collection": THEME, "mode": D}])
        self.assertEqual(variables.alternatives({"fill": "VariableID:1"}, [], r), ([], False))

    def test_value_alt_precedes_mode_alt_and_overrides_mode(self):
        r = variables.reachable(self.v, [{"type": "setVariableMode", "collection": THEME, "mode": D},
                                         {"type": "setVariable", "variable": "VariableID:1",
                                          "value": "rgba(1, 2, 3, 1)"}])
        whens, _ = variables.alternatives({"fill": "VariableID:1"}, [THEME], r)
        self.assertEqual(whens, [{"vars": {"VariableID:1": "rgba(1, 2, 3, 1)"}}, {"modes": {THEME: D}}])

    def test_non_colour_bound_var_ignored(self):
        r = variables.reachable(self.v, [{"type": "setVariableMode", "collection": THEME, "mode": D}])
        self.assertEqual(variables.alternatives({"gap": "VariableID:2"}, [THEME], r), ([], False))

    def test_cartesian_product_capped_at_32_and_flagged(self):
        v = variables.parse(raw())
        # two colour vars in two collections, 2 x 3 modes + literals => more than 32
        extra = []
        for i in range(40):
            extra.append({"type": "setVariable", "variable": "VariableID:1", "value": "rgba(%d, 0, 0, 1)" % i})
        extra += [{"type": "setVariableMode", "collection": THEME, "mode": D},
                  {"type": "setVariableMode", "collection": SIZE, "mode": S2},
                  {"type": "setVariableMode", "collection": SIZE, "mode": S3}]
        r = variables.reachable(v, extra)
        bound = {"fill": "VariableID:1", "stroke": "VariableID:3"}
        whens, capped = variables.alternatives(bound, [THEME, SIZE], r)
        self.assertTrue(capped)
        self.assertEqual(len(whens), 32)
        # the simplest alternatives (one non-default choice) survive the cap
        self.assertIn({"modes": {THEME: D}}, whens)
        self.assertIn({"modes": {SIZE: S2}}, whens)
        small = variables.alternatives(bound, [THEME, SIZE], r, cap=1000)[0]
        self.assertEqual(len(small), len(set(repr(sorted(w.items())) for w in small)))
        # most specific first
        sizes = [sum(len(x) for x in w.values()) for w in whens]
        self.assertEqual(sizes, sorted(sizes, reverse=True))


def scene(actions, explicit=None):
    v = variables.parse(raw())
    nodes = {
        "1": {"id": "1", "name": "Écran", "alts": [], "children": ["2", "3"]},
        "2": {"id": "2", "name": "Carte", "alts": [], "children": []},
        "3": {"id": "3", "name": "Fixe", "alts": [], "children": []},
    }
    jobs = [{"node": n, "fc_id": int(n), "kind": "own", "hide_children": n == "1", "strip_effects": []}
            for n in ("1", "2", "3")]
    w = {"proto": {"nodes": nodes, "variables": {}}, "jobs": jobs, "warnings": [],
         "bound": {"1": {"fill": "VariableID:1"}, "2": {"fill": "VariableID:1"}, "3": {"fill": "VariableID:2"}},
         "explicit_modes": explicit or {}, "parent": {"1": None, "2": "1", "3": "1"}, "actions": actions}
    return v, w


class AddJobsTests(unittest.TestCase):
    def test_mode_jobs_and_alts(self):
        v, w = scene([{"type": "setVariableMode", "collection": THEME, "mode": D}])
        variables.add_jobs(w, v, variables.reachable(v, w["actions"]))
        mj = [j for j in w["jobs"] if j["kind"] == "mode"]
        self.assertEqual([j["node"] for j in mj], ["1", "2"])
        self.assertEqual(mj[0]["collection"], THEME)
        self.assertEqual(mj[0]["mode"], D)
        self.assertEqual(mj[0]["modes"], {THEME: D})
        self.assertTrue(mj[0]["hide_children"])
        self.assertEqual(mj[0]["alt"], 0)
        self.assertEqual(w["proto"]["nodes"]["2"]["alts"], [{"when": {"modes": {THEME: D}}, "paint": None}])
        self.assertEqual(w["proto"]["nodes"]["3"]["alts"], [])
        self.assertEqual(w["proto"]["variables"], v)
        self.assertEqual(w["warnings"], [])

    def test_var_value_jobs_normalise_action_values(self):
        act = {"type": "setVariable", "variable": "VariableID:1", "value": {"r": 1, "g": 0, "b": 0, "a": 1}}
        v, w = scene([act])
        variables.add_jobs(w, v, variables.reachable(v, w["actions"]))
        self.assertEqual(act["value"], "rgba(255, 0, 0, 1)")
        vj = [j for j in w["jobs"] if j["kind"] == "varValue"]
        self.assertEqual(vj[0]["var"], "VariableID:1")
        self.assertEqual(vj[0]["value"], "rgba(255, 0, 0, 1)")
        self.assertEqual(vj[0]["vars"], {"VariableID:1": "rgba(255, 0, 0, 1)"})

    def test_pinned_frame_subtree_not_varied(self):
        v, w = scene([{"type": "setVariableMode", "collection": THEME, "mode": D}], explicit={"1": {THEME: D}})
        variables.add_jobs(w, v, variables.reachable(v, w["actions"]))
        self.assertEqual([j for j in w["jobs"] if j["kind"] != "own"], [])
        own = [j for j in w["jobs"] if j["kind"] == "own"]
        self.assertTrue(all(j["pinned_modes"] == {THEME: D} for j in own))

    def test_cap_and_open_warnings(self):
        acts = [{"type": "setVariable", "variable": "VariableID:1", "value": "rgba(%d, 0, 0, 1)" % i}
                for i in range(40)]
        acts.append({"type": "setVariable", "variable": "VariableID:1", "expr": {"op": "x"}})
        v, w = scene(acts)
        variables.add_jobs(w, v, variables.reachable(v, acts), cap=32)
        n = len([j for j in w["jobs"] if j["node"] == "2" and j["kind"] != "own"])
        self.assertEqual(n, 32)
        self.assertIn("… alternatives limitées à 32 pour le calque « Carte » : rendu approximé.", w["warnings"])
        self.assertIn("La variable « surface » change par une expression : seules ses valeurs connues sont pré-rendues.",
                      w["warnings"])
        self.assertEqual(len(w["proto"]["nodes"]["2"]["alts"]), 32)


if __name__ == "__main__":
    unittest.main()
