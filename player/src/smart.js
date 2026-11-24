// Timing samples, Web Animations playback and Smart Animate. Pure parts (timing, matchLayers)
// run under jsc; DOM is only touched inside FCP.play / FCP.smartAnimate.
(function () {
  var MOTION = { instant: 0 };

  // timing(transition) -> {duration ms, samples: [{offset 0..1, p eased progress}]}.
  // Springs play until they settle (their own duration); other easings use durationMs.
  FCP.timing = function (tr) {
    if (!tr || MOTION[tr.type] === 0) return { duration: 0, samples: [{ offset: 0, p: 1 }, { offset: 1, p: 1 }] };
    var sp = FCP.springFor(tr.easing), duration, f;
    if (sp) {
      var s = FCP.spring(sp);
      duration = s.duration;
      f = function (t) { return s.at(t * duration); };
    } else {
      duration = Math.max(0, +tr.durationMs || 0);
      f = FCP.easing(tr.easing);
    }
    var n = Math.max(2, Math.min(60, Math.ceil(duration / 16))), samples = [];
    for (var i = 0; i <= n; i++) samples.push({ offset: i / n, p: i === n ? 1 : f(i / n) });
    return { duration: duration, samples: samples };
  };

  // matchLayers: pairs of [fromId, toId] whose layer names are equal along the whole
  // name-path from the roots (roots excluded). Duplicate names pair up in document order.
  // kids(id, side) gives the children to walk ("from" | "to"); default node.children.
  FCP.matchLayers = function (fromRootId, toRootId, proto, kids) {
    var nodes = proto.nodes || {}, out = [];
    kids = kids || function (id) { return (nodes[id] && nodes[id].children) || []; };
    function walk(a, b) {
      var bs = kids(b, "to") || [], used = {}, i, j;
      (kids(a, "from") || []).forEach(function (fa) {
        var na = nodes[fa];
        if (!na) return;
        for (j = 0; j < bs.length; j++) {
          var nb = nodes[bs[j]];
          if (!used[j] && nb && nb.name === na.name) { used[j] = true; out.push([fa, bs[j]]); walk(fa, bs[j]); return; }
        }
      });
    }
    walk(fromRootId, toRootId);
    return out;
  };

  // --- Web Animations ---------------------------------------------------------------
  var running = [];
  FCP.finishRunning = function () {
    running.slice().forEach(function (c) { c.anims.forEach(function (a) { try { a.finish(); } catch (e) {} }); });
  };

  function frame(from, to, p) {
    function l(k) { return from[k] + (to[k] - from[k]) * p; }
    var f = {}, tf = "";
    if ("x" in from) f.left = l("x") + "px";
    if ("y" in from) f.top = l("y") + "px";
    if ("w" in from) f.width = Math.max(0, l("w")) + "px";
    if ("h" in from) f.height = Math.max(0, l("h")) + "px";
    if ("tx" in from) tf += "translate(" + l("tx") + "px," + l("ty") + "px) ";
    if ("r" in from) tf += "rotate(" + (-l("r")) + "deg)";
    if (tf) f.transform = tf;
    if ("o" in from) f.opacity = Math.max(0, Math.min(1, l("o")));
    return f;
  }

  // play(specs [{el, from, to}], timing, ctl?) -> Promise. ctl (optional) receives
  // {anims, seek(p), play(), finish()}; ctl.scrub starts paused at 0 (drag follows pointer).
  // ctl.reverse plays the time-reversed animation. Animations are cancelled when done, so
  // every element falls back to its own inline style (the end state).
  FCP.play = function (specs, timing, ctl) {
    ctl = ctl || {};
    specs = specs.filter(function (s) { return s.el && typeof s.el.animate === "function"; });
    if (!specs.length || timing.duration <= 0) { if (ctl.onStart) ctl.onStart(); return Promise.resolve(); }
    var anims = specs.map(function (s) {
      var kf = timing.samples.map(function (smp) {
        var f = frame(s.from, s.to, smp.p); f.offset = smp.offset; return f;
      });
      return s.el.animate(kf, { duration: timing.duration, fill: "both", easing: "linear",
                                direction: ctl.reverse ? "reverse" : "normal" });
    });
    ctl.anims = anims;
    ctl.seek = function (p) {
      var smp = timing.samples, t = 1, i;
      if (ctl.reverse) p = 1 - p;
      for (i = 1; i < smp.length; i++) {
        if (smp[i].p >= p) {
          var a = smp[i - 1], b = smp[i], k = b.p === a.p ? 1 : (p - a.p) / (b.p - a.p);
          t = a.offset + (b.offset - a.offset) * Math.max(0, Math.min(1, k)); break;
        }
      }
      if (ctl.reverse) t = 1 - t;
      anims.forEach(function (a) { a.currentTime = t * timing.duration; });
    };
    ctl.play = function () { anims.forEach(function (a) { a.play(); }); };
    ctl.finish = function () { anims.forEach(function (a) { try { a.finish(); } catch (e) {} }); };
    if (ctl.scrub) anims.forEach(function (a) { a.pause(); a.currentTime = 0; });
    running.push(ctl);
    if (ctl.onStart) ctl.onStart();
    return Promise.all(anims.map(function (a) { return a.finished.catch(function () {}); })).then(function () {
      var i = running.indexOf(ctl);
      if (i >= 0) running.splice(i, 1);
      anims.forEach(function (a) { try { a.cancel(); } catch (e) {} });
    });
  };

  // smartAnimate(o): o = {proto, fromRoot, toRoot, fromEls, toEls ({id: element}), kids,
  // transition, ctl, extra: [spec]}. Matched layers move/resize/rotate/fade from the
  // source's values to their own; unmatched source layers fade out, unmatched
  // destination layers fade in. The destination shows its own content (images, text).
  FCP.smartAnimate = function (o) {
    var nodes = o.proto.nodes, kids = o.kids;
    var pairs = FCP.matchLayers(o.fromRoot, o.toRoot, o.proto, kids);
    var mf = {}, mt = {}, specs = (o.extra || []).slice(), hidden = [];
    pairs.forEach(function (p) { mf[p[0]] = p[1]; mt[p[1]] = p[0]; });
    function geom(n) {
      return { x: n.x, y: n.y, w: n.w, h: n.h, r: n.rotation || 0, o: n.opacity === undefined ? 1 : n.opacity };
    }
    function walk(root, side, fn) {
      (kids(root, side) || []).forEach(function (id) { if (fn(id) !== false) walk(id, side, fn); });
    }
    walk(o.fromRoot, "from", function (id) {
      var el = o.fromEls[id], n = nodes[id];
      if (!el || !n) return false;
      if (mf[id] !== undefined) { el.style.visibility = "hidden"; hidden.push(el); return true; }
      el.style.visibility = "visible"; hidden.push(el);
      specs.push({ el: el, from: { o: geom(n).o }, to: { o: 0 } });
      return false;
    });
    walk(o.toRoot, "to", function (id) {
      var el = o.toEls[id], n = nodes[id];
      if (!el || !n) return false;
      if (mt[id] !== undefined) {
        var a = nodes[mt[id]];
        if (n.position === "sticky" || !a) return true;
        specs.push({ el: el, from: geom(a), to: geom(n) });
        return true;
      }
      specs.push({ el: el, from: { o: 0 }, to: { o: geom(n).o } });
      return false;
    });
    return FCP.play(specs, FCP.timing(o.transition), o.ctl).then(function () {
      hidden.forEach(function (el) { el.style.visibility = ""; });
    });
  };
})();
