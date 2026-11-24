// Hover ownership with interactive components (variantInteractions).
function chipProto() {
  var ch = function (type, v) { return { trigger: { type: type }, actions: [{ type: "changeTo", variant: v, transition: { type: "instant" } }] }; };
  var leaf = function (id) { return { id: id, name: "Bg", children: [], interactions: [] }; };
  var nodes = {
    S: { id: "S", name: "S", children: ["I"], interactions: [] },
    I: { id: "I", name: "Chip", children: ["I~D~bg"], interactions: [],
         instance: { set: "Chip", variant: "Default",
                     variants: { Default: ["I~D~bg"], Hover: ["I~H~bg"], Pressed: ["I~P~bg"] },
                     variantInteractions: { Default: [ch("hover", "Hover")], Hover: [ch("press", "Pressed")], Pressed: [] } } },
    "I~D~bg": leaf("I~D~bg"), "I~H~bg": leaf("I~H~bg"), "I~P~bg": leaf("I~P~bg")
  };
  return { start: "S", screens: { S: { root: "S" } }, nodes: nodes, variables: { collections: {}, vars: {} } };
}

test("hover_owner_kept_while_pointer_inside_after_variant_change", function () {
  var p = chipProto(), st = FCP.createState(p);
  var first = FCP.hoverStep(p, st, ["I~D~bg", "I", "S"], null);
  assertEq(first.r.nodeId, "I");
  st.run(first.r.interaction.actions, { nodeId: "I" });
  assertEq(st.variants.I, "Hover");
  // The Hover variant has no hover trigger: resolving anew would find nothing (the flicker).
  assertEq(FCP.resolve(p, st, ["I~H~bg", "I", "S"], "hover"), null);
  assertEq(FCP.hoverStep(p, st, ["I~H~bg", "I", "S"], "I").keep, true);
  // Its press comes from the variant shown.
  assertEq(FCP.resolve(p, st, ["I~H~bg", "I", "S"], "press").interaction.actions[0].variant, "Pressed");
});

test("hover_owner_released_when_pointer_leaves", function () {
  var p = chipProto(), st = FCP.createState(p);
  var s = FCP.hoverStep(p, st, ["S"], "I");
  assertEq(s.keep, undefined);
  assertEq(s.r, null);
});

test("nested_hover_takes_over_from_parent_hover", function () {
  var hv = function (tag) { return { trigger: { type: "hover" }, actions: [{ type: "navigate", dest: tag }] }; };
  var p = { start: "S", screens: {}, variables: { collections: {}, vars: {} }, nodes: {
    S: { id: "S", children: ["card"], interactions: [] },
    card: { id: "card", children: ["btn", "txt"], interactions: [hv("C")] },
    btn: { id: "btn", children: [], interactions: [hv("B")] },
    txt: { id: "txt", children: [], interactions: [] } } };
  var st = FCP.createState(p);
  assertEq(FCP.hoverStep(p, st, ["txt", "card", "S"], null).r.nodeId, "card");
  // From the card onto its child button: the button's own hover wins.
  assertEq(FCP.hoverStep(p, st, ["btn", "card", "S"], "card").r.nodeId, "btn");
  // Back onto the card (the button left the path): the card takes the hover again.
  assertEq(FCP.hoverStep(p, st, ["txt", "card", "S"], "btn").r.nodeId, "card");
  // Still on the button, which resolves to itself: kept.
  assertEq(FCP.hoverStep(p, st, ["btn", "card", "S"], "btn").keep, true);
});

test("visit_tokens_go_stale_on_each_variant_change", function () {
  var v = FCP.createVisits();
  var a = v.snap(["I"]);                 // Default armed
  assertTrue(v.valid(a));
  v.bump("I");                           // -> Hover
  var b = v.snap(["I"]);
  v.bump("I");                           // -> Default again before the delay ended
  var c = v.snap(["I"]);
  assertEq(v.valid(a), false, "first Default visit is stale");
  assertEq(v.valid(b), false, "Hover visit is stale");
  assertEq(v.valid(c), true, "re-entered Default is armed again");
  var nested = v.snap(["kid", "I"]);
  v.bump("I");
  assertEq(v.valid(nested), false, "a timer inside the instance goes stale with it");
});
