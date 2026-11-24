import unittest

from figcraft_export import interactions
from tests.fake_control import load_fixture

FX = load_fixture("interactions_all_kinds")
ALL = FX["scenario_164"] + FX["spike"]


def conv(raw, **kw):
    return interactions.convert(raw, **kw)


def by_trigger(items, ttype):
    return [i for i in items if i["trigger"]["type"] == ttype]


class InteractionTests(unittest.TestCase):
    def test_every_trigger_and_action_kind_converts(self):
        out = [conv(r, variant_key=lambda d: "V%s" % d) for r in ALL]
        triggers = {o["trigger"]["type"] for o in out}
        self.assertEqual(
            triggers,
            {"click", "hover", "press", "drag", "mouseEnter", "mouseLeave", "mouseDown", "mouseUp", "afterDelay", "key"},
        )
        kinds = set()

        def collect(actions):
            for a in actions:
                kinds.add(a["type"])
                for b in a.get("blocks", []):
                    collect(b["actions"])

        for o in out:
            collect(o["actions"])
        self.assertEqual(
            kinds,
            {"navigate", "back", "closeOverlay", "scrollTo", "openOverlay", "swapOverlay", "openUrl",
             "changeTo", "setVariable", "setVariableMode", "conditional"},
        )

    def test_trigger_details(self):
        after = conv(by_trigger(ALL, "afterDelay")[0])
        self.assertEqual(after["trigger"], {"type": "afterDelay", "delayMs": 800})
        enter = conv(by_trigger(ALL, "mouseEnter")[0])
        self.assertEqual(enter["trigger"], {"type": "mouseEnter", "delayMs": 200})
        keys = [conv(r)["trigger"] for r in by_trigger(ALL, "keyPress")]
        self.assertIn({"type": "key", "key": "Shift+K"}, keys)
        self.assertIn({"type": "key", "key": "Gamepad A"}, keys)

    def test_navigate_with_transition(self):
        raw = {"trigger": {"type": "onClick"}, "actions": [{"type": "navigate", "dest": 24}],
               "transition": {"type": "push", "direction": "left"}, "duration_ms": 400, "easing": "easeOut"}
        self.assertEqual(conv(raw), {
            "trigger": {"type": "click"},
            "actions": [{"type": "navigate", "dest": "24", "transition": {
                "type": "push", "direction": "left", "durationMs": 400, "easing": {"type": "easeOut"}}}],
        })
        ps = [conv(r) for r in ALL if r["actions"][0].get("preserve_scroll")][0]
        self.assertTrue(ps["actions"][0]["preserveScroll"])
        self.assertEqual(ps["actions"][0]["transition"]["type"], "slideOut")

    def test_overlay_fields(self):
        with_bg = [conv(r) for r in ALL if r["actions"][0]["type"] == "openOverlay" and r["actions"][0].get("background")][0]
        a = with_bg["actions"][0]
        self.assertEqual(a["background"], "rgba(0, 0, 0, 0.4)")
        self.assertIs(a["closeOnClickOutside"], True)
        self.assertEqual(a["position"], "center")
        self.assertEqual(a["dest"], "2")
        manual = [conv(r) for r in ALL if r["actions"][0].get("position") == "manual"][0]["actions"][0]
        self.assertEqual(manual["anchor"], "triggerOutside")
        self.assertEqual(manual["offset"], [4, 8])
        self.assertIs(manual["closeOnClickOutside"], False)
        self.assertNotIn("background", manual)

    def test_open_url_new_tab_defaults_true(self):
        urls = [conv(r)["actions"][0] for r in ALL if r["actions"][0]["type"] == "openUrl"]
        self.assertIn({"type": "openUrl", "url": "https://example.com", "newTab": False}, urls)
        self.assertIn({"type": "openUrl", "url": "https://example.com", "newTab": True}, urls)

    def test_variables_and_conditional(self):
        drag = conv(by_trigger(ALL, "onDrag")[0])["actions"][0]
        self.assertEqual(drag["variable"], "VariableID:2")
        self.assertEqual(drag["expr"]["op"]["op"], "add")
        self.assertNotIn("value", drag)
        leave = conv(by_trigger(ALL, "mouseLeave")[0])["actions"][0]
        self.assertEqual(leave, {"type": "setVariable", "variable": "VariableID:1", "value": "Bob"})
        cond = conv(by_trigger(ALL, "mouseDown")[0])["actions"][0]
        self.assertEqual(cond["blocks"][0]["condition"]["op"]["op"], "greaterOrEqual")
        self.assertEqual(cond["blocks"][0]["actions"], [{"type": "back"}])
        self.assertNotIn("condition", cond["blocks"][1])
        self.assertEqual(cond["blocks"][1]["actions"][0]["type"], "swapOverlay")
        self.assertEqual(cond["blocks"][1]["actions"][0]["dest"], "162")
        mode = [conv(r)["actions"][0] for r in ALL if r["actions"][0]["type"] == "setVariableMode"][0]
        self.assertEqual(mode, {"type": "setVariableMode", "collection": "VariableCollectionId:1",
                                "mode": "VariableCollectionId:1/mode2"})

    def test_scroll_to_offset(self):
        a = [conv(r)["actions"][0] for r in ALL if r["actions"][0]["type"] == "scrollTo"][0]
        self.assertEqual(a["dest"], "365")
        self.assertEqual(a["offset"], [0, 44])
        self.assertIn("transition", a)

    def test_custom_bezier_and_spring_convert(self):
        bez = conv(by_trigger(ALL, "afterDelay")[0])["actions"][0]["transition"]
        self.assertEqual(bez["easing"], {"type": "customBezier", "bezier": [0.2, 0.0, 0.0, 1.0]})
        self.assertEqual(bez["type"], "smartAnimate")
        self.assertEqual(bez["durationMs"], 300)
        spring = [conv(r)["actions"][0]["transition"]["easing"] for r in ALL
                  if isinstance(r.get("easing"), dict) and "customSpring" in r["easing"]][0]
        self.assertEqual(spring, {"type": "customSpring", "spring": {"mass": 1.0, "stiffness": 300.0, "damping": 20.0}})
        self.assertEqual(conv(by_trigger(ALL, "onClick")[0])["actions"][0].get("transition", {"easing": {"type": "easeOut"}})["easing"]["type"], "easeOut")

    def test_change_to_uses_variant_key(self):
        raw = {"trigger": {"type": "onHover"}, "actions": [{"type": "changeTo", "dest": 174}],
               "transition": {"type": "smartAnimate"}, "duration_ms": 200, "easing": "easeInOut"}
        a = conv(raw, variant_key=lambda d: {174: "State=Hover"}[d])["actions"][0]
        self.assertEqual(a["variant"], "State=Hover")
        self.assertEqual(a["transition"]["durationMs"], 200)
        self.assertNotIn("dest", a)
        self.assertEqual(conv(raw)["actions"][0]["variant"], "174")

    def test_unknown_kinds_raise_value_error(self):
        with self.assertRaises(ValueError):
            conv({"trigger": {"type": "onWink"}, "actions": [{"type": "back"}]})
        with self.assertRaises(ValueError):
            conv({"trigger": {"type": "onClick"}, "actions": [{"type": "teleport"}]})

    def test_links_lists_destinations(self):
        raw = by_trigger(ALL, "mouseDown")[0]
        self.assertEqual(interactions.links(raw), {"screens": [162], "variants": []})
        hover = {"trigger": {"type": "onHover"}, "actions": [{"type": "changeTo", "dest": 179}]}
        self.assertEqual(interactions.links(hover), {"screens": [], "variants": [179]})


if __name__ == "__main__":
    unittest.main()
