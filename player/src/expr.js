// Expression evaluator for FigCraft variable expressions (pure, no DOM).
// Expr = { value: { type, value } } | { op: { op, args: [Expr] } }
(function () {
  function num(v) { return typeof v === "number" ? v : Number(v); }

  var OPS = {
    add: function (a, b) {
      // Any string operand makes it a join; otherwise numeric sum.
      if (typeof a === "string" || typeof b === "string") return String(a) + String(b);
      return num(a) + num(b);
    },
    subtract: function (a, b) { return num(a) - num(b); },
    multiply: function (a, b) { return num(a) * num(b); },
    // RULING: the API notes do not record FigCraft's result for x/0; we return 0.
    divide: function (a, b) { return num(b) === 0 ? 0 : num(a) / num(b); },
    equals: function (a, b) { return a === b; },
    less: function (a, b) { return num(a) < num(b); },
    greaterOrEqual: function (a, b) { return num(a) >= num(b); },
    // Not in the notes; plain boolean ops.
    and: function (a, b) { return !!a && !!b; },
    or: function (a, b) { return !!a || !!b; },
    not: function (a) { return !a; }
  };

  function evalExpr(expr, getVar) {
    if (!expr || typeof expr !== "object") return undefined;
    if (expr.value && typeof expr.value === "object") {
      if (expr.value.type === "alias") return getVar ? getVar(expr.value.value) : undefined;
      return expr.value.value;
    }
    if (expr.op && typeof expr.op === "object") {
      var name = expr.op.op, args = (expr.op.args || []).map(function (a) { return evalExpr(a, getVar); });
      if (name === "alias") return getVar ? getVar(args[0]) : undefined;
      var fn = OPS.hasOwnProperty(name) ? OPS[name] : null;
      return fn ? fn(args[0], args[1]) : undefined;
    }
    return undefined;
  }

  FCP.evalExpr = evalExpr;
})();
