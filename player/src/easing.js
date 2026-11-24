// Easing curves (pure, no DOM). One table per kind so values can be corrected later.
(function () {
  // Preset cubic beziers [x1,y1,x2,y2] — Figma's published values.
  var BEZIER_PRESETS = {
    linear: [0, 0, 1, 1],
    easeIn: [0.42, 0, 1, 1],
    easeOut: [0, 0, 0.58, 1],
    easeInOut: [0.42, 0, 0.58, 1],
    easeInBack: [0.3, -0.05, 0.7, -0.5],
    easeOutBack: [0.45, 1.45, 0.8, 1],
    easeInOutBack: [0.7, -0.4, 0.4, 1.4]
  };
  // Preset springs — Figma's published values.
  var SPRING_PRESETS = {
    gentle: { mass: 1, stiffness: 100, damping: 15 },
    quick: { mass: 1, stiffness: 300, damping: 20 },
    bouncy: { mass: 1, stiffness: 600, damping: 15 },
    slow: { mass: 1, stiffness: 80, damping: 20 }
  };

  function bezier(x1, y1, x2, y2) {
    function cx(s) { var u = 1 - s; return 3 * u * u * s * x1 + 3 * u * s * s * x2 + s * s * s; }
    function cy(s) { var u = 1 - s; return 3 * u * u * s * y1 + 3 * u * s * s * y2 + s * s * s; }
    function dx(s) { var u = 1 - s; return 3 * u * u * x1 + 6 * u * s * (x2 - x1) + 3 * s * s * (1 - x2); }
    return function (t) {
      if (t <= 0) return 0;
      if (t >= 1) return 1;
      var s = t, i, d, e;
      for (i = 0; i < 8; i++) {
        e = cx(s) - t;
        if (Math.abs(e) < 1e-7) return cy(s);
        d = dx(s);
        if (Math.abs(d) < 1e-6) break;
        s -= e / d;
      }
      var lo = 0, hi = 1;
      s = t;
      for (i = 0; i < 60; i++) {
        e = cx(s) - t;
        if (Math.abs(e) < 1e-7) break;
        if (e > 0) hi = s; else lo = s;
        s = (lo + hi) / 2;
      }
      return cy(s);
    };
  }

  function springFor(spec) {
    if (!spec) return null;
    if (spec.type === "customSpring") return spec.spring || null;
    return SPRING_PRESETS.hasOwnProperty(spec.type) ? SPRING_PRESETS[spec.type] : null;
  }

  // Integrate m x'' = -k(x-1) - c x' from x=0, v=0 with 1 ms steps until settled.
  function spring(p) {
    var m = p.mass || 1, k = p.stiffness, c = p.damping;
    var dt = 0.001, x = 0, v = 0, samples = [0], ms = 0, MAX = 20000;
    while (ms < MAX) {
      v += (-k * (x - 1) - c * v) / m * dt;
      x += v * dt;
      ms++;
      samples.push(x);
      if (Math.abs(x - 1) < 0.001 && Math.abs(v) < 0.001) break;
    }
    var duration = ms;
    return {
      duration: duration,
      at: function (t) {
        if (t <= 0) return 0;
        if (t >= duration) return 1;
        var i = Math.floor(t), f = t - i;
        return samples[i] + (samples[i + 1] - samples[i]) * f;
      }
    };
  }

  // easing(spec) -> (t 0..1) => number, for bezier kinds. Unknown/spring kinds fall back
  // to linear (springs are driven by FCP.spring over time, not by progress).
  function easing(spec) {
    var b = null;
    if (spec) {
      if (spec.type === "customBezier" && spec.bezier) b = spec.bezier;
      else if (BEZIER_PRESETS.hasOwnProperty(spec.type)) b = BEZIER_PRESETS[spec.type];
    }
    if (!b || b === BEZIER_PRESETS.linear) return function (t) { return t; };
    return bezier(b[0], b[1], b[2], b[3]);
  }

  FCP.easing = easing;
  FCP.spring = spring;
  FCP.springFor = springFor;
  FCP.EASING_TABLES = { bezier: BEZIER_PRESETS, spring: SPRING_PRESETS };
})();
