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
