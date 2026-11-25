var T = function (ms) { return { type: "dissolve", durationMs: ms || 200, easing: { type: "linear" } }; };
function mkProto() {
  return {
    start: "A",
    screens: { A: { root: "A" }, B: { root: "B" }, C: { root: "C" }, O1: { root: "O1" }, O2: { root: "O2" } },
    nodes: {
      A: { id: "A", children: ["inst"] },
      inst: { id: "inst", kind: "instance", children: ["innerA"], instance: { set: "S", variant: "off", variants: { off: ["innerA"], on: ["innerB"] } } },
      innerA: { id: "innerA", children: [] },
      innerB: { id: "innerB", children: [] },
      B: { id: "B", children: [] }, C: { id: "C", children: [] }, O1: { id: "O1", children: [] }, O2: { id: "O2", children: [] }
    },
    variables: {
      collections: { c1: { name: "c", defaultMode: "m1", modes: { m1: "Light", m2: "Dark" } } },
      vars: { count: { name: "count", collection: "c1", type: "number", valuesByMode: { m1: 0, m2: 5 } } }
    }
  };
}
var nav = function (d, ms) { return { type: "navigate", dest: d, transition: T(ms) }; };
var ov = function (t, d) { return { type: t, dest: d, position: "center", closeOnClickOutside: true, transition: T(100) }; };
var ctx = { nodeId: "A" };

test("navigate_replaces_screen_and_pushes_history", function () {
  var s = FCP.createState(mkProto());
  assertEq(s.screen, "A");
  var fx = s.run([nav("B", 300)], ctx);
  assertEq(s.screen, "B");
  assertEq(fx.length, 1);
  assertEq(fx[0].kind, "screen"); assertEq(fx[0].from, "A"); assertEq(fx[0].to, "B");
  assertEq(fx[0].transition.durationMs, 300);
  assertTrue(!fx[0].reverse);
});
test("navigate_from_overlay_closes_overlays", function () {
  var s = FCP.createState(mkProto());
  s.run([ov("openOverlay", "O1"), ov("openOverlay", "O2")], ctx);
  assertEq(s.overlays.length, 2);
  var fx = s.run([nav("B")], ctx);
  assertEq(s.overlays.length, 0); assertEq(s.screen, "B");
  assertEq(fx.filter(function (e) { return e.kind === "overlayClose"; }).length, 2);
  assertEq(fx.filter(function (e) { return e.kind === "screen"; }).length, 1);
});
test("back_closes_top_overlay_first", function () {
  var s = FCP.createState(mkProto());
  s.run([nav("B"), ov("openOverlay", "O1")], ctx);
  var fx = s.run([{ type: "back" }], ctx);
  assertEq(fx[0].kind, "overlayClose"); assertEq(fx[0].id, "O1");
  assertEq(s.overlays.length, 0); assertEq(s.screen, "B");
});
test("back_returns_with_reverse_transition", function () {
  var s = FCP.createState(mkProto());
  s.run([nav("B", 333)], ctx);
  var fx = s.run([{ type: "back" }], ctx);
  assertEq(s.screen, "A");
  assertEq(fx[0].kind, "screen"); assertEq(fx[0].from, "B"); assertEq(fx[0].to, "A");
  assertEq(fx[0].reverse, true); assertEq(fx[0].transition.durationMs, 333);
});
test("back_on_first_screen_is_noop", function () {
  var s = FCP.createState(mkProto());
  var fx = s.run([{ type: "back" }], ctx);
  assertEq(fx.length, 0); assertEq(s.screen, "A");
});
test("swap_overlay_replaces_top", function () {
  var s = FCP.createState(mkProto());
  s.run([ov("openOverlay", "O1")], ctx);
  var fx = s.run([ov("swapOverlay", "O2")], { nodeId: "inst" });
  assertEq(s.overlays.length, 1); assertEq(s.overlays[0].id, "O2"); assertEq(s.overlays[0].sourceNodeId, "inst");
  assertEq(fx[0].kind, "overlaySwap"); assertEq(fx[0].id, "O2");
});
test("close_overlay_pops", function () {
  var s = FCP.createState(mkProto());
  s.run([ov("openOverlay", "O1"), ov("openOverlay", "O2")], ctx);
  var fx = s.run([{ type: "closeOverlay" }], ctx);
  assertEq(s.overlays.length, 1); assertEq(s.overlays[0].id, "O1");
  assertEq(fx[0].kind, "overlayClose"); assertEq(fx[0].id, "O2");
});
test("restart_clears_history_overlays_and_vars", function () {
  var s = FCP.createState(mkProto());
  s.run([nav("B"), ov("openOverlay", "O1"),
    { type: "setVariable", variable: "count", value: 9 },
    { type: "setVariableMode", collection: "c1", mode: "m2" },
    { type: "changeTo", variant: "on", transition: T() }], { nodeId: "innerA" });
  s.restart();
  assertEq(s.screen, "A"); assertEq(s.overlays.length, 0);
  assertEq(s.vars.count, 0); assertEq(s.modes.c1, "m1");
  assertEq(s.variants.inst, undefined);
  assertEq(s.run([{ type: "back" }], ctx).length, 0);
});
test("set_variable_expr_count_plus_one", function () {
  var s = FCP.createState(mkProto());
  assertEq(s.vars.count, 0);
  var a = { type: "setVariable", variable: "count", expr: { op: { op: "add", args: [{ value: { type: "alias", value: "count" } }, { value: { type: "number", value: 1 } }] } } };
  var fx = s.run([a], ctx);
  assertEq(s.vars.count, 1); assertEq(fx[0].kind, "vars");
  s.run([a], ctx);
  assertEq(s.vars.count, 2);
});
test("set_variable_mode_changes_modes", function () {
  var s = FCP.createState(mkProto());
  var fx = s.run([{ type: "setVariableMode", collection: "c1", mode: "m2" }], ctx);
  assertEq(s.modes.c1, "m2"); assertEq(fx[0].kind, "vars");
});
test("conditional_runs_first_matching_block_else_last", function () {
  var s = FCP.createState(mkProto());
  var bool = function (b) { return { value: { type: "boolean", value: b } }; };
  var set = function (v) { return { type: "setVariable", variable: "count", value: v }; };
  s.run([{ type: "conditional", blocks: [
    { condition: bool(false), actions: [set(1)] },
    { condition: bool(true), actions: [set(2)] },
    { condition: bool(true), actions: [set(3)] },
    { actions: [set(4)] }] }], ctx);
  assertEq(s.vars.count, 2);
  s.run([{ type: "conditional", blocks: [{ condition: bool(false), actions: [set(1)] }, { actions: [set(4)] }] }], ctx);
  assertEq(s.vars.count, 4);
});
test("change_to_records_variant", function () {
  var s = FCP.createState(mkProto());
  var fx = s.run([{ type: "changeTo", variant: "on", transition: T(50) }], { nodeId: "innerA" });
  assertEq(s.variants.inst, "on");
  assertEq(fx[0].kind, "variant"); assertEq(fx[0].node, "inst"); assertEq(fx[0].from, "off"); assertEq(fx[0].to, "on");
  assertEq(fx[0].transition.durationMs, 50);
});
test("navigate_to_missing_screen_is_noop_no_throw", function () {
  var s = FCP.createState(mkProto());
  var fx = s.run([nav("nope"), ov("openOverlay", "nope"), ov("swapOverlay", "nope"),
    { type: "changeTo", variant: "zzz", transition: T() }], { nodeId: "inst" });
  assertEq(fx.length, 0); assertEq(s.screen, "A"); assertEq(s.overlays.length, 0);
  assertEq(s.run([{ type: "changeTo", variant: "on", transition: T() }], { nodeId: "ghost" }).length, 0);
});
test("scroll_and_url_effects", function () {
  var s = FCP.createState(mkProto());
  var fx = s.run([{ type: "scrollTo", dest: "B", offset: [0, 5], transition: T() }, { type: "openUrl", url: "http://x", newTab: true }], ctx);
  assertEq(fx[0].kind, "scroll"); assertEq(fx[0].target, "B"); assertEq(fx[1].kind, "url"); assertEq(fx[1].newTab, true);
});

test("set_variable_survives_mode_switch", function () {
  var s = FCP.createState(mkProto());
  s.run([{ type: "setVariable", variable: "count", value: 9 }, { type: "setVariableMode", collection: "c1", mode: "m2" }], ctx);
  assertEq(s.vars.count, 9);
  s.restart(); assertEq(s.vars.count, 0);
});
test("unset_variable_follows_mode", function () {
  var s = FCP.createState(mkProto());
  s.run([{ type: "setVariableMode", collection: "c1", mode: "m2" }], ctx);
  assertEq(s.vars.count, 5);
  assertEq(s.run([{ type: "setVariableMode", collection: "c1", mode: "bogus" }], ctx).length, 0);
  assertEq(s.modes.c1, "m2");
});
test("change_to_from_icon_inside_button_changes_button", function () {
  var p = mkProto();
  p.nodes.inst.children = ["btn"];
  p.nodes.btn = { id: "btn", kind: "instance", children: ["icon"], instance: { set: "I", variant: "a", variants: { a: ["icon"], b: ["icon2"] } } };
  p.nodes.icon = { id: "icon", children: [] };
  var s = FCP.createState(p);
  var fx = s.run([{ type: "changeTo", variant: "on", transition: T() }], { nodeId: "icon" });
  assertEq(fx[0].node, "inst"); assertEq(s.variants.inst, "on");
  var fx2 = s.run([{ type: "changeTo", variant: "b", transition: T() }], { nodeId: "icon" });
  assertEq(fx2[0].node, "btn");
  assertEq(s.run([{ type: "changeTo", variant: "b", transition: T() }], { nodeId: "icon" }).length, 0, "already active");
});
test("overlay_and_navigate_effects_carry_renderer_data", function () {
  var s = FCP.createState(mkProto());
  var a = { type: "openOverlay", dest: "O1", position: "topLeft", anchor: "triggerInside", offset: [1, 2], closeOnClickOutside: true, background: "#000", transition: T() };
  var fx = s.run([a], ctx);
  assertEq(fx[0].position, "topLeft"); assertEq(fx[0].anchor, "triggerInside"); assertEq(fx[0].offset[1], 2);
  assertEq(fx[0].closeOnClickOutside, true); assertEq(fx[0].background, "#000");
  assertEq(s.overlays[0].position, "topLeft"); assertEq(s.overlays[0].background, "#000");
  var sw = s.run([{ type: "swapOverlay", dest: "O2", position: "center", closeOnClickOutside: false, transition: T() }], ctx);
  assertEq(sw[0].position, "center"); assertEq(sw[0].closeOnClickOutside, false);
  var nv = s.run([{ type: "navigate", dest: "B", preserveScroll: true, transition: T() }], ctx);
  assertEq(nv[nv.length - 1].preserveScroll, true);
});

test("close_overlay_at_closes_that_one_not_the_top", function () {
  var p = { start: "A", screens: { A: {}, O1: {}, O2: {} }, nodes: {}, variables: { collections: {}, vars: {} } };
  var st = FCP.createState(p);
  st.run([{ type: "openOverlay", dest: "O1", transition: { type: "dissolve" } }, { type: "openOverlay", dest: "O2" }], {});
  var fx = st.closeOverlayAt(0);
  assertEq(fx[0].id, "O1"); assertEq(fx[0].index, 0); assertEq(fx[0].transition.type, "dissolve");
  assertEq(st.overlays.length, 1); assertEq(st.overlays[0].id, "O2");
  assertEq(st.run([{ type: "closeOverlay" }], {})[0].transition, undefined);
});
test("screen_modes_seed_start_restart_and_navigate", function () {
  var p = mkProto();
  p.screens.A.modes = { c1: "m2" };
  p.screens.B.modes = { c1: "m1", nope: "x" };
  p.screens.O1.modes = { c1: "bad" };
  var s = FCP.createState(p);
  assertEq(s.modes.c1, "m2"); assertEq(s.vars.count, 5);
  s.run([nav("B")], ctx);
  assertEq(s.modes.c1, "m1"); assertEq(s.vars.count, 0);
  assertEq(s.modes.nope, undefined);                       // unknown collection ignored
  s.run([{ type: "setVariableMode", collection: "c1", mode: "m2" }], ctx);
  s.run([nav("C")], ctx);
  assertEq(s.modes.c1, "m2");                               // a screen without modes keeps them
  s.run([{ type: "back" }], ctx);
  assertEq(s.modes.c1, "m1");                               // back to B: its modes again
  s.run([ov("openOverlay", "O1")], ctx);
  assertEq(s.modes.c1, "m1");                               // overlays don't change modes
  s.restart();
  assertEq(s.modes.c1, "m2"); assertEq(s.vars.count, 5);
});
test("no_screen_modes_keeps_default_modes", function () {
  var s = FCP.createState(mkProto());
  assertEq(s.modes.c1, "m1");
  s.run([nav("B")], ctx);
  assertEq(s.modes.c1, "m1");
});
