function E(op) { var a = Array.prototype.slice.call(arguments, 1); return { op: { op: op, args: a } }; }
function V(type, value) { return { value: { type: type, value: value } }; }
var N = function (n) { return V("number", n); }, S = function (s) { return V("string", s); }, B = function (b) { return V("boolean", b); };
var none = function () { return undefined; };

test("add numbers", function () { assertEq(FCP.evalExpr(E("add", N(1), N(2)), none), 3); });
test("add string joins", function () { assertEq(FCP.evalExpr(E("add", S("a"), N(1)), none), "a1"); });
test("subtract / multiply", function () {
  assertEq(FCP.evalExpr(E("subtract", N(5), N(2)), none), 3);
  assertEq(FCP.evalExpr(E("multiply", N(4), N(2)), none), 8);
});
test("divide", function () { assertEq(FCP.evalExpr(E("divide", N(9), N(3)), none), 3); });
test("divide by zero returns 0", function () { assertEq(FCP.evalExpr(E("divide", N(1), N(0)), none), 0); });
test("equals / less / greaterOrEqual", function () {
  assertEq(FCP.evalExpr(E("equals", N(2), N(2)), none), true);
  assertEq(FCP.evalExpr(E("equals", S("a"), S("b")), none), false);
  assertEq(FCP.evalExpr(E("less", N(1), N(2)), none), true);
  assertEq(FCP.evalExpr(E("less", N(2), N(2)), none), false);
  assertEq(FCP.evalExpr(E("greaterOrEqual", N(2), N(2)), none), true);
  assertEq(FCP.evalExpr(E("greaterOrEqual", N(1), N(2)), none), false);
});
test("and / or / not", function () {
  assertEq(FCP.evalExpr(E("and", B(true), B(false)), none), false);
  assertEq(FCP.evalExpr(E("and", B(true), B(true)), none), true);
  assertEq(FCP.evalExpr(E("or", B(false), B(true)), none), true);
  assertEq(FCP.evalExpr(E("or", B(false), B(false)), none), false);
  assertEq(FCP.evalExpr(E("not", B(false)), none), true);
});
test("alias reads getVar", function () {
  var get = function (id) { return id === "v1" ? 41 : undefined; };
  assertEq(FCP.evalExpr(V("alias", "v1"), get), 41);
  assertEq(FCP.evalExpr(E("add", V("alias", "v1"), N(1)), get), 42);
  assertEq(FCP.evalExpr(E("alias", S("v1")), get), 41);
});
test("unknown op returns undefined, no throw", function () {
  assertEq(FCP.evalExpr(E("frobnicate", N(1)), none), undefined);
  assertEq(FCP.evalExpr(null, none), undefined);
  assertEq(FCP.evalExpr({}, none), undefined);
});
