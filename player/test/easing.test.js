test("linear(0.5) = 0.5", function () { assertClose(FCP.easing({ type: "linear" })(0.5), 0.5, 1e-9); });
test("easeInOut is symmetric", function () {
  var f = FCP.easing({ type: "easeInOut" });
  assertClose(f(0.25) + f(0.75), 1, 1e-4);
});
test("bezier hits 0 and 1 at the ends", function () {
  var f = FCP.easing({ type: "customBezier", bezier: [0.42, 0, 0.58, 1] });
  assertClose(f(0), 0, 1e-9); assertClose(f(1), 1, 1e-9);
});
test("every preset id resolves and ends at 0..1", function () {
  ["linear","easeIn","easeOut","easeInOut","easeInBack","easeOutBack","easeInOutBack","gentle","quick","bouncy","slow"].forEach(function (id) {
    var f = FCP.easing({ type: id });
    assertTrue(typeof f === "function", id);
    assertClose(f(0), 0, 1e-6, id); assertClose(f(1), 1, 1e-3, id);
  });
});
test("easeOutBack overshoots", function () {
  var f = FCP.easing({ type: "easeOutBack" }), m = 0;
  for (var t = 0; t <= 1; t += 0.01) m = Math.max(m, f(t));
  assertTrue(m > 1.01, "max " + m);
});
test("unknown easing falls back to linear", function () { assertClose(FCP.easing({ type: "nope" })(0.3), 0.3, 1e-9); });
test("spring settles at 1", function () {
  var s = FCP.spring({ mass: 1, stiffness: 300, damping: 20 });
  assertTrue(s.duration > 0);
  assertClose(s.at(s.duration), 1, 0.001); assertClose(s.at(0), 0, 1e-9);
});
test("underdamped spring overshoots, overdamped does not", function () {
  var u = FCP.spring({ mass: 1, stiffness: 600, damping: 15 }), m = 0, t;
  for (t = 0; t <= u.duration; t += 5) m = Math.max(m, u.at(t));
  assertTrue(m > 1.05, "max " + m);
  var o = FCP.spring({ mass: 1, stiffness: 80, damping: 20 }); m = 0;
  for (t = 0; t <= o.duration; t += 5) m = Math.max(m, o.at(t));
  assertTrue(m <= 1.0001, "max " + m);
});
test("springFor resolves spring presets and custom", function () {
  assertTrue(FCP.springFor({ type: "bouncy" }) !== null);
  assertEq(FCP.springFor({ type: "customSpring", spring: { mass: 2, stiffness: 5, damping: 1 } }).mass, 2);
  assertEq(FCP.springFor({ type: "easeIn" }), null);
});
