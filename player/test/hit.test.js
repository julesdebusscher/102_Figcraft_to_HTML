function hp(nodes) {
  var o = {};
  nodes.forEach(function (n) { o[n.id] = n; if (!n.children) n.children = []; });
  return { start: "S", screens: {}, nodes: o, variables: { collections: {}, vars: { show: { collection: "c", valuesByMode: {} } } } };
}
var ia = function (type, tag, extra) {
  var t = { type: type }; if (extra) for (var k in extra) t[k] = extra[k];
  return { trigger: t, actions: [{ type: "navigate", dest: tag }] };
};
function resolveIn(p, path, type, vars) {
  var st = FCP.createState(p);
  if (vars) for (var k in vars) st.vars[k] = vars[k];
  return { st: st, r: FCP.resolve(p, st, path, type) };
}

// path order: top-most layer first, then down to the screen root.
test("topmost_trigger_wins", function () {
  var p = hp([{ id: "root", interactions: [ia("click", "R")] }, { id: "btn", interactions: [ia("click", "B")] }]);
  var o = resolveIn(p, ["btn", "root"], "click");
  assertEq(o.r.nodeId, "btn"); assertEq(o.r.interaction.actions[0].dest, "B");
});
test("layer_without_trigger_passes_through", function () {
  var p = hp([{ id: "root", interactions: [ia("click", "R")] }, { id: "btn", interactions: [ia("hover", "H")] }, { id: "plain" }]);
  assertEq(resolveIn(p, ["plain", "btn", "root"], "click").r.nodeId, "root");
  assertEq(resolveIn(p, ["plain", "btn", "root"], "hover").r.nodeId, "btn");
  assertEq(resolveIn(p, ["plain", "btn", "root"], "press").r, null);
});
test("hidden_layer_ignored", function () {
  var p = hp([
    { id: "root", interactions: [ia("click", "R")] },
    { id: "hid", visible: false, interactions: [ia("click", "X")] },
    { id: "kid", interactions: [ia("click", "K")] },
    { id: "bound", bindings: { visible: "show" }, interactions: [ia("click", "BD")] }
  ]);
  // hidden layer and everything under it ignored
  assertEq(resolveIn(p, ["kid", "hid", "root"], "click").r.nodeId, "root");
  assertEq(resolveIn(p, ["bound", "root"], "click", { show: false }).r.nodeId, "root");
  assertEq(resolveIn(p, ["bound", "root"], "click", { show: true }).r.nodeId, "bound");
});
function instProto() {
  return hp([
    { id: "inst", kind: "instance", interactions: [ia("hover", "OWN")],
      instance: { set: "S", variant: "off", variants: { off: [], on: [] },
        variantInteractions: { off: [ia("click", "TURN_ON"), ia("hover", "VOFF")], on: [ia("click", "TURN_OFF")] } } }
  ]);
}
test("instance_plays_shown_variant_interactions", function () {
  var p = instProto(), st = FCP.createState(p);
  assertEq(FCP.interactionsFor(p, st, "inst").filter(function (i) { return i.trigger.type === "click"; })[0].actions[0].dest, "TURN_ON");
  st.variants.inst = "on";
  assertEq(FCP.interactionsFor(p, st, "inst").filter(function (i) { return i.trigger.type === "click"; })[0].actions[0].dest, "TURN_OFF");
  assertEq(FCP.resolve(p, st, ["inst"], "click").interaction.actions[0].dest, "TURN_OFF");
});
test("instance_own_interaction_overrides_same_trigger", function () {
  var p = instProto(), st = FCP.createState(p);
  var hovers = FCP.interactionsFor(p, st, "inst").filter(function (i) { return i.trigger.type === "hover"; });
  assertEq(hovers.length, 1); assertEq(hovers[0].actions[0].dest, "OWN");
  assertEq(FCP.interactionsFor(p, st, "inst").length, 2);
});
test("key_shift_k_does_not_fire_for_k", function () {
  assertEq(FCP.keyMatches("Shift+K", { key: "K", shift: true }), true);
  assertEq(FCP.keyMatches("Shift+K", { key: "k", shift: true }), true);
  assertEq(FCP.keyMatches("Shift+K", { key: "k" }), false);
  assertEq(FCP.keyMatches("K", { key: "k", shift: true }), false);
  assertEq(FCP.keyMatches("K", { key: "k" }), true);
  assertEq(FCP.keyMatches("Ctrl+Alt+K", { key: "k", ctrl: true, alt: true }), true);
  assertEq(FCP.keyMatches("Ctrl+K", { key: "k", ctrl: true, meta: true }), false);
  assertEq(FCP.keyMatches("Enter", { key: "Enter" }), true);
  assertEq(FCP.keyMatches("Space", { key: " " }), true);
});
test("figcraft_key_names_map_to_dom_key_values", function () {
  // FigCraft stores the name as given (setter) or as its key recorder writes it (egui names)
  [["Up", "ArrowUp"], ["ArrowUp", "ArrowUp"], ["Down", "ArrowDown"], ["Left", "ArrowLeft"], ["Right", "ArrowRight"],
   ["Enter", "Enter"], ["Return", "Enter"], ["Escape", "Escape"], ["Esc", "Escape"], ["Space", " "], [" ", " "],
   ["Tab", "Tab"], ["Backspace", "Backspace"], ["Delete", "Delete"], ["Del", "Delete"], ["PageUp", "PageUp"],
   ["PageDown", "PageDown"], ["Home", "Home"], ["End", "End"], ["Plus", "+"], ["Minus", "-"], ["Equals", "="],
   ["Comma", ","], ["Period", "."], ["Slash", "/"], ["Num1", "1"], ["1", "1"], ["F1", "F1"]
  ].forEach(function (p) {
    assertEq(FCP.keyMatches(p[0], { key: p[1] }), true, p[0] + " vs " + JSON.stringify(p[1]));
  });
  assertEq(FCP.keyMatches("Up", { key: "ArrowDown" }), false);
  assertEq(FCP.keyMatches("Shift+Enter", { key: "Enter", shift: true }), true);
  assertEq(FCP.keyMatches("Ctrl+Left", { key: "ArrowLeft", ctrl: true }), true);
  assertEq(FCP.keyMatches("Shift+Tab", { key: "Tab" }), false);
  assertEq(FCP.keyMatches("Ctrl+Plus", { key: "+", ctrl: true }), true);
  assertEq(FCP.keyMatches("Ctrl++", { key: "+", ctrl: true }), true);
});
test("gamepad_key_spec_parsed", function () {
  assertEq(FCP.keyMatches("Gamepad A", { gamepad: "A" }), true);
  assertEq(FCP.keyMatches("Gamepad A", { gamepad: "B" }), false);
  assertEq(FCP.keyMatches("Gamepad A", { key: "A" }), false);
  assertEq(FCP.keyMatches("A", { gamepad: "A" }), false);
});
test("resolve_key_uses_event", function () {
  var p = hp([{ id: "n", interactions: [ia("key", "K1", { key: "Shift+K" })] }]);
  var st = FCP.createState(p);
  assertEq(FCP.resolve(p, st, ["n"], "key", { key: "k" }), null);
  assertEq(FCP.resolve(p, st, ["n"], "key", { key: "k", shift: true }).nodeId, "n");
});
test("hidden_instance_variant_interaction_does_not_fire", function () {
  var p = instProto(); p.nodes.inst.visible = false;
  p.nodes.root = { id: "root", children: [], interactions: [ia("click", "R")] };
  var st = FCP.createState(p);
  assertEq(FCP.resolve(p, st, ["inst", "root"], "click").nodeId, "root");
});
