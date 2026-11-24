// Transitions between two layers (screens, overlays, variant subtrees) with the Web
// Animations API. DOM only inside functions.
(function () {
  var DIR = { left: [-1, 0], right: [1, 0], top: [0, -1], bottom: [0, 1] };
  FCP.DIRECTIONAL = { moveIn: 1, moveOut: 1, push: 1, slideIn: 1, slideOut: 1 };

  // animate(effect, els, ctl?) -> Promise.
  // effect: {transition, reverse?}; els: {from, to, w, h, also?: [el], smart?: {...}}.
  // from leaves, to arrives. reverse plays the way in backwards (Back, closing an overlay).
  // also: elements that fade with the arrival (an overlay's dimmed background).
  // smart: arguments of FCP.smartAnimate (proto, fromRoot, toRoot, fromEls, toEls, kids, extra).
  FCP.animate = function (effect, els, ctl) {
    var tr = effect.transition || { type: "instant" }, type = tr.type;
    ctl = ctl || {};
    if (type === "smartAnimate" && els.smart) {
      var o = {}; Object.keys(els.smart).forEach(function (k) { o[k] = els.smart[k]; });
      o.transition = tr; o.ctl = ctl;
      return FCP.smartAnimate(o);
    }
    if (type === "smartAnimate") type = "dissolve";
    var rev = !!effect.reverse, A = rev ? els.to : els.from, B = rev ? els.from : els.to;
    var d = DIR[tr.direction] || DIR.left, sx = d[0] * (els.w || 0), sy = d[1] * (els.h || 0);
    var specs = [], top = B;
    function mv(el, f, t) { if (el) specs.push({ el: el, from: { tx: f * sx, ty: f * sy }, to: { tx: t * sx, ty: t * sy } }); }
    switch (type) {
      case "dissolve": if (B) specs.push({ el: B, from: { o: 0 }, to: { o: 1 } }); break;
      case "moveIn": mv(B, -1, 0); break;
      case "moveOut": mv(A, 0, 1); top = A; break;
      case "push": mv(B, -1, 0); mv(A, 0, 1); break;
      case "slideIn": mv(B, -1, 0); mv(A, 0, 0.3); break;
      case "slideOut": mv(A, 0, 1); mv(B, -0.3, 0); top = A; break;
    }
    (els.also || []).forEach(function (el) { if (el) specs.push({ el: el, from: { o: 0 }, to: { o: 1 } }); });
    var under = top === A ? B : A;
    if (top) top.style.zIndex = 2;
    if (under) under.style.zIndex = 1;
    ctl.reverse = rev;
    return FCP.play(specs, FCP.timing(type === "instant" ? null : tr), ctl).then(function () {
      if (A) A.style.zIndex = "";
      if (B) B.style.zIndex = "";
    });
  };

  // The drag direction a directional transition answers to, or null.
  FCP.dragDirection = function (actions) {
    var found = null;
    (actions || []).some(function (a) {
      var t = a && a.transition;
      if (t && FCP.DIRECTIONAL[t.type] && DIR[t.direction]) { found = t.direction; return true; }
      return false;
    });
    return found;
  };
  // Does a drag of (dx, dy) go `dir`? Exactly diagonal counts for both axes.
  FCP.dragGoes = function (dir, dx, dy) {
    var v = DIR[dir];
    if (!v) return false;
    if (v[0]) return Math.abs(dx) >= Math.abs(dy) && dx * v[0] > 0;
    return Math.abs(dy) >= Math.abs(dx) && dy * v[1] > 0;
  };
})();
