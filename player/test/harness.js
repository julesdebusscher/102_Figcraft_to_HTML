// Tiny test harness (jsc or browser). Test files call test(name, fn) and the assert helpers.
var __T = { passed: 0, failed: 0 };
function test(name, fn) {
  try { fn(); __T.passed++; }
  catch (e) { __T.failed++; print("FAIL: " + name + " -- " + (e && e.message || e)); }
}
function assertEq(actual, expected, msg) {
  var same = actual === expected || (actual !== actual && expected !== expected);
  if (!same) throw new Error((msg ? msg + ": " : "") + "expected " + JSON.stringify(expected) + ", got " + JSON.stringify(actual));
}
function assertClose(actual, expected, eps, msg) {
  if (!(Math.abs(actual - expected) <= (eps === undefined ? 1e-6 : eps)))
    throw new Error((msg ? msg + ": " : "") + "expected ~" + expected + ", got " + actual);
}
function assertTrue(v, msg) { if (!v) throw new Error(msg || "expected truthy"); }
function __report() {
  print(__T.passed + " passed, " + __T.failed + " failed");
  return __T.failed === 0;
}
