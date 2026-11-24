// Smart Animate layer matching (pure) and timing samples.
function sp(list) {
  // list: [id, name, [childIds]]
  var nodes = {};
  list.forEach(function (r) { nodes[r[0]] = { id: r[0], name: r[1], children: r[2] || [] }; });
  return { nodes: nodes };
}
function pairsStr(pairs) { return pairs.map(function (p) { return p[0] + ">" + p[1]; }).join(","); }

test("matches_by_name_path", function () {
  var p = sp([
    ["A", "Screen A", ["a.hdr", "a.grp"]], ["a.hdr", "Header"], ["a.grp", "Group", ["a.card"]], ["a.card", "Card"],
    ["B", "Screen B", ["b.card", "b.grp", "b.hdr"]], ["b.hdr", "Header"], ["b.grp", "Group", ["b.card2"]],
    ["b.card2", "Card"], ["b.card", "Card"]
  ]);
  // Same name AND same name-path: Group/Card matches Group/Card, not the top-level Card.
  assertEq(pairsStr(FCP.matchLayers("A", "B", p)), "a.hdr>b.hdr,a.grp>b.grp,a.card>b.card2");
});

test("unmatched_layers_excluded", function () {
  var p = sp([
    ["A", "A", ["a.x", "a.only", "a.g"]], ["a.x", "X"], ["a.only", "Only in A"], ["a.g", "G", ["a.in"]], ["a.in", "Inner"],
    ["B", "B", ["b.x", "b.new", "b.h"]], ["b.x", "X"], ["b.new", "Only in B"], ["b.h", "H", ["b.in"]], ["b.in", "Inner"]
  ]);
  // Inner sits under G in A and under H in B: different paths, so no match.
  assertEq(pairsStr(FCP.matchLayers("A", "B", p)), "a.x>b.x");
});

test("duplicate_names_match_in_order", function () {
  var p = sp([
    ["A", "A", ["a1", "a2"]], ["a1", "Row"], ["a2", "Row"],
    ["B", "B", ["b1", "bz", "b2", "b3"]], ["b1", "Row"], ["bz", "Other"], ["b2", "Row"], ["b3", "Row"]
  ]);
  assertEq(pairsStr(FCP.matchLayers("A", "B", p)), "a1>b1,a2>b2");
});

test("match_uses_given_children_for_variants", function () {
  var p = sp([["I", "Button", ["I~D~bg"]], ["I~D~bg", "Bg"], ["I~H~bg", "Bg"], ["I~H~dot", "Dot"]]);
  var kids = function (id, side) { return id === "I" ? (side === "from" ? ["I~D~bg"] : ["I~H~bg", "I~H~dot"]) : p.nodes[id].children; };
  assertEq(pairsStr(FCP.matchLayers("I", "I", p, kids)), "I~D~bg>I~H~bg");
});

test("timing_samples_spring_overshoot_and_end", function () {
  var t = FCP.timing({ type: "smartAnimate", durationMs: 300, easing: { type: "bouncy" } });
  assertTrue(t.duration > 300, "spring plays until it settles, not the duration field");
  var max = 0;
  t.samples.forEach(function (s) { if (s.p > max) max = s.p; });
  assertTrue(max > 1, "bouncy overshoots");
  assertEq(t.samples[0].offset, 0); assertEq(t.samples[t.samples.length - 1].offset, 1);
  assertEq(t.samples[t.samples.length - 1].p, 1);
  assertEq(FCP.timing({ type: "instant", durationMs: 300 }).duration, 0);
  assertEq(FCP.timing({ type: "dissolve", durationMs: 200, easing: { type: "linear" } }).duration, 200);
});
