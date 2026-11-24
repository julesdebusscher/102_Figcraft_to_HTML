// Player boot: page skeleton, scaling, effect application, overlays, timers.
// Runs by itself on DOMContentLoaded in a browser; does nothing under jsc (no document).
(function () {
  function div(cls) { var d = document.createElement("div"); d.className = cls; return d; }
  var PAD = 24;

  FCP.boot = function (proto) {
    if (FCP._player) return FCP._player;
    var app = div("fcp-app");
    document.body.appendChild(app);
    if (!proto || !proto.screens || !proto.screens[proto.start]) {
      app.appendChild(div("fcp-error")).textContent = "Impossible de lire le prototype : le fichier data.js est absent ou incomplet.";
      return null;
    }
    document.title = proto.title || document.title;
    var state = FCP.createState(proto), parents = FCP.parentMap(proto);
    var body = div("fcp-body"), stage = div("fcp-stage"), device = div("fcp-device");
    var scaler = div("fcp-scaler"), screenLayer = div("fcp-layer"), overlayLayer = div("fcp-layer fcp-overlays");
    var chrome = FCP.buildChrome(proto, { onJump: jump, onRestart: restart });
    app.appendChild(chrome.bar); app.appendChild(body);
    body.appendChild(chrome.panel); body.appendChild(stage);
    stage.appendChild(device); device.appendChild(scaler);
    scaler.appendChild(screenLayer); scaler.appendChild(overlayLayer);

    var view = { scale: 1, w: 0, h: 0, tall: false };
    var screen = null, overlays = [];   // layers: {el, id, alive, timers: {nodeId: [t]}}

    function hasGamepad() {
      var found = false;
      function scan(list) { (list || []).forEach(function (i) { if (i.trigger && /^gamepad/i.test(i.trigger.key || "")) found = true; }); }
      Object.keys(proto.nodes).forEach(function (id) {
        var n = proto.nodes[id];
        scan(n.interactions);
        var vi = n.instance && n.instance.variantInteractions;
        if (vi) Object.keys(vi).forEach(function (k) { scan(vi[k]); });
      });
      return found;
    }

    // Contain the screen in the stage; a frame taller than 1.5x the window fits its width
    // and scrolls in a window-high viewport (fixed layers stay at the window's top).
    function measure(id) {
      var s = proto.screens[id];
      var aw = Math.max(50, stage.clientWidth - 2 * PAD), ah = Math.max(50, stage.clientHeight - 2 * PAD);
      var v = FCP.viewFor(s.width, s.height, aw, ah);
      return { scale: v.scale, w: s.width, h: v.tall ? Math.min(s.height, ah / v.scale) : s.height, tall: v.tall };
    }
    function applyView(v) {
      view = v;
      device.style.width = v.w * v.scale + "px"; device.style.height = v.h * v.scale + "px";
      scaler.style.width = v.w + "px"; scaler.style.height = v.h + "px";
      scaler.style.transform = "scale(" + v.scale + ")";
    }
    window.addEventListener("resize", function () {
      if (!screen) return;
      var v = measure(screen.id);
      if (v.tall !== view.tall) { applyView(v); rebuild(); return; }
      applyView(v);
      screen.el.style.height = v.h + "px";
    });

    // --- layers and timers ---------------------------------------------------------
    function layers() { return overlays.slice().reverse().concat(screen ? [screen] : []); }
    function layerOf(nodeId) {
      var ls = layers();
      for (var i = 0; i < ls.length; i++) if (ls[i].el._fcp.reg.byId[nodeId]) return ls[i];
      return null;
    }
    function kill(layer) {
      layer.alive = false;
      Object.keys(layer.timers).forEach(function (k) { layer.timers[k].forEach(clearTimeout); });
      layer.timers = {};
    }
    function later(nodeId, ms, fn, layer) {
      layer = layer || layerOf(nodeId);
      if (!layer) return;
      var t = setTimeout(function () {
        var e = layer.el._fcp.reg.byId[nodeId];
        if (layer.alive && e && e.el.isConnected && !hiddenUp(nodeId)) fn();
      }, ms);
      (layer.timers[nodeId] = layer.timers[nodeId] || []).push(t);
    }
    function hiddenUp(id) {
      for (var g = 0; id !== undefined && g < 10000; g++, id = parents[id]) if (FCP.isHidden(state, proto.nodes[id])) return true;
      return false;
    }
    // After delay: timed from when the layer (or, for an instance, its variant) appears,
    // armed again on every entry; it fires only in the visit it was armed in (no instance
    // around it changed variant since), so loops cycle and stale timers stay silent.
    var visits = FCP.createVisits();
    function instancesUp(id) {
      var out = [];
      for (var g = 0; id !== undefined && g < 10000; g++, id = parents[id]) if (proto.nodes[id] && proto.nodes[id].instance) out.push(id);
      return out;
    }
    function armDelays(layer, ids) {
      ids.forEach(function (id) {
        FCP.interactionsFor(proto, state, id).forEach(function (it) {
          if (it.trigger.type !== "afterDelay") return;
          var snap = visits.snap(instancesUp(id));
          later(id, +it.trigger.delayMs || 0, function () { if (visits.valid(snap)) exec(it.actions, id); }, layer);
        });
      });
    }
    function idsIn(layer, el) {
      return layer.el._fcp.reg.list.filter(function (e) { return el.contains(e.el); }).map(function (e) { return e.id; });
    }
    function newLayer(el, id) {
      var l = { el: el, id: id, alive: true, timers: {} };
      return l;
    }
    function logicalPath(id) {
      var out = [];
      for (var g = 0; id !== undefined && g < 10000; g++, id = parents[id]) out.push(id);
      return out;
    }
    // forHover: a pointer over an overlay that a hover or press opened is still over the
    // layer that opened it (a tooltip doesn't close itself by being pointed at).
    function pathAt(target, forHover) {
      if (!target || !target.closest || !device.contains(target)) return [];
      var hit = target.closest("[data-fcp-id]");
      var path = hit ? logicalPath(hit.getAttribute("data-fcp-id")) : [];
      if (forHover && hit) {
        for (var i = overlays.length - 1; i >= 0; i--) {
          if (overlays[i].owner !== undefined && overlays[i].el.contains(hit)) return path.concat(logicalPath(overlays[i].owner));
        }
      }
      return path;
    }
    function kidsFn(over) {
      return function (id, side) {
        if (over && id === over.id) return proto.nodes[id].instance.variants[side === "from" ? over.from : over.to] || [];
        return FCP.kidsOf(proto, state, id);
      };
    }

    // --- effects ------------------------------------------------------------------
    function exec(actions, nodeId, opts) {
      var fx = state.run(actions, { nodeId: nodeId });
      apply(fx, opts || {});
      return fx;
    }
    function apply(fx, opts) {
      var ctl = opts.ctl;
      fx.forEach(function (e) {
        var c = ctl && (e.kind === "screen" || e.kind === "variant") ? ctl : null;
        if (c) ctl = null;
        try { APPLY[e.kind](e, c, opts); } catch (err) { if (window.console) console.error(err); }
      });
    }
    function revert(fx) {
      for (var i = fx.length - 1; i >= 0; i--) {
        var e = fx[i];
        if (e.kind === "variant" && state.variants[e.node] === e.to) {
          state.variants[e.node] = e.from;
          APPLY.variant({ kind: "variant", node: e.node, from: e.to, to: e.from, transition: e.transition });
        } else if (e.kind === "overlayOpen" && e.layer) {
          var at = overlays.indexOf(e.layer);   // that overlay, top of the stack or not
          if (at >= 0) apply(state.closeOverlayAt(at), {});
        }
      }
    }

    function showScreen(id, e, ctl) {
      FCP.finishRunning();
      var old = screen, v = measure(id);
      if (old) kill(old);
      trig.reset();
      applyView(v);
      var el = FCP.buildScreen(proto, state, id, { viewH: v.h, scroll: v.tall });
      screenLayer.appendChild(el);
      screen = newLayer(el, id);
      var sc = el._fcp.area.scroller;
      if (old && e && e.preserveScroll) {
        sc.scrollLeft = old.el._fcp.area.scroller.scrollLeft; sc.scrollTop = old.el._fcp.area.scroller.scrollTop;
        FCP.updateSticky(el._fcp.area);
      }
      chrome.setCurrent(id);
      armDelays(screen, el._fcp.reg.list.map(function (x) { return x.id; }));
      if (!old) return;
      var rootImg = el._fcp.reg.byId[el._fcp.root].img;
      FCP.animate(e || {}, { from: old.el, to: el, w: v.w, h: v.h, smart: {
        proto: proto, fromRoot: old.el._fcp.root, toRoot: el._fcp.root, kids: kidsFn(null),
        fromEls: FCP.elsOfScreen(old.el), toEls: FCP.elsOfScreen(el),
        extra: [{ el: el._fcp.bg, from: { o: 0 }, to: { o: 1 } }, { el: rootImg, from: { o: 0 }, to: { o: 1 } }]
      } }, ctl || {}).then(function () { if (old.el.parentNode) old.el.parentNode.removeChild(old.el); });
    }

    function overlayRect(e, ow, oh) {
      var vw = view.w, vh = view.h, F = { x: 0, y: 0, w: vw, h: vh }, src = null;
      var se = e.sourceNodeId !== undefined && layerOf(e.sourceNodeId);
      if (se) {
        var r = se.el._fcp.reg.byId[e.sourceNodeId].el.getBoundingClientRect(), b = scaler.getBoundingClientRect();
        src = { x: (r.left - b.left) / view.scale, y: (r.top - b.top) / view.scale, w: r.width / view.scale, h: r.height / view.scale };
      }
      var pos = e.position || "center", off = e.offset;
      if (pos === "manual") {
        var s = src || F;
        return off ? { x: s.x + off[0], y: s.y + off[1] } : { x: s.x, y: s.y + (src ? s.h : 0) };
      }
      var anchor = src && e.anchor ? e.anchor : null;
      if (anchor) F = src;
      var L = /Left$/.test(pos), R = /Right$/.test(pos), T = /^top/.test(pos), B = /^bottom/.test(pos);
      var x = L ? F.x : R ? F.x + F.w - ow : F.x + (F.w - ow) / 2;
      var y = T ? F.y : B ? F.y + F.h - oh : F.y + (F.h - oh) / 2;
      if (anchor === "triggerOutside") y = T ? F.y - oh : B ? F.y + F.h : y;
      return { x: x, y: y };
    }

    function openOverlay(e, opts, p) {
      var s = proto.screens[e.id], wrap = div("fcp-ovwrap"), back = div("fcp-backdrop");
      var el = FCP.buildScreen(proto, state, e.id);
      back.style.background = e.background || "transparent";
      p = p || overlayRect(e, s.width, s.height);
      var transient = opts && opts.transient !== undefined;
      if (transient) wrap.classList.add("fcp-ovwrap-through");
      el.style.left = p.x + "px"; el.style.top = p.y + "px";
      el.classList.add("fcp-overlay");
      wrap.appendChild(back); wrap.appendChild(el); overlayLayer.appendChild(wrap);
      var layer = newLayer(el, e.id);
      layer.wrap = wrap; layer.back = back; layer.transition = e.transition;
      if (transient) layer.owner = opts.transient;
      layer.backColor = e.background || "";
      back.addEventListener("pointerdown", function (ev) {
        ev.stopPropagation();
        if (overlays[overlays.length - 1] === layer && e.closeOnClickOutside !== false) exec([{ type: "closeOverlay" }]);
      });
      overlays.push(layer);
      armDelays(layer, el._fcp.reg.list.map(function (x) { return x.id; }));
      return layer;
    }
    function closeOverlay(layer, tr, instant) {
      kill(layer);
      overlays.splice(overlays.indexOf(layer), 1);
      var done = function () { if (layer.wrap.parentNode) layer.wrap.parentNode.removeChild(layer.wrap); };
      if (instant) return done();
      FCP.animate({ transition: tr, reverse: true }, { from: layer.el, to: null, w: view.w, h: view.h, also: [layer.back] }).then(done);
    }

    function scrollTo(e) {
      var layer = layerOf(e.target), off = e.offset || [0, 0], tr = FCP.timing(e.transition);
      var target = layer ? layer.el._fcp.reg.byId[e.target].el : null, scs = [];
      if (!target) { if (proto.screens[e.target] && screen) scs.push([screen.el._fcp.area.scroller, 0, 0]); }
      else {
        for (var p = target.parentNode, first = true; p && p !== scaler; p = p.parentNode) {
          if (!p.classList || !p.classList.contains("fcp-scroll")) continue;
          var r = target.getBoundingClientRect(), b = p.getBoundingClientRect();
          var x = (r.left - b.left) / view.scale + p.scrollLeft - (first ? off[0] : 0);
          var y = (r.top - b.top) / view.scale + p.scrollTop - (first ? off[1] : 0);
          scs.push([p, x, y]); first = false;
        }
      }
      scs.forEach(function (s) {
        var sc = s[0], x0 = sc.scrollLeft, y0 = sc.scrollTop, start = null;
        if (tr.duration <= 0) { sc.scrollLeft = s[1]; sc.scrollTop = s[2]; return; }
        (function step(now) {
          if (start === null) start = now;
          var k = Math.min(1, (now - start) / tr.duration), smp = tr.samples, i = Math.min(smp.length - 1, Math.floor(k * (smp.length - 1)));
          var a = smp[i], nb = smp[Math.min(smp.length - 1, i + 1)], f = nb.offset === a.offset ? 1 : (k - a.offset) / (nb.offset - a.offset);
          var q = a.p + (nb.p - a.p) * f;
          sc.scrollLeft = x0 + (s[1] - x0) * q; sc.scrollTop = y0 + (s[2] - y0) * q;
          if (k < 1) requestAnimationFrame(step);
        })(performance.now());
      });
    }

    var APPLY = {
      screen: function (e, ctl) { showScreen(e.to, e, ctl); },
      overlayOpen: function (e, ctl, opts) {
        var l = openOverlay(e, opts);
        e.layer = l;   // lets a hover/press revert close this very overlay
        FCP.animate(e, { from: null, to: l.el, w: view.w, h: view.h, also: [l.back] });
      },
      overlaySwap: function (e, ctl, opts) {
        var top = overlays[overlays.length - 1], s = proto.screens[e.id];
        var pos = overlayRect(e, s.width, s.height);   // the source may sit in the overlay it replaces
        var sameBack = !!top && top.backColor === (e.background || "");   // no flash between equal dims
        if (top) closeOverlay(top, null, true);
        var l = openOverlay(e, opts, pos);
        e.layer = l;
        FCP.animate(e, { from: null, to: l.el, w: view.w, h: view.h, also: sameBack ? [] : [l.back] });
      },
      overlayClose: function (e) {
        if (e.index !== undefined) return overlays[e.index] && closeOverlay(overlays[e.index], e.transition);
        for (var i = overlays.length - 1; i >= 0; i--) if (overlays[i].id === e.id) return closeOverlay(overlays[i], e.transition);
      },
      variant: function (e, ctl) {
        var layer = layerOf(e.node);
        if (!layer) return;
        var r = FCP.swapVariantDom(layer.el, e.node), n = proto.nodes[e.node];
        if (!r) return;
        visits.bump(e.node);   // timers of the variant it leaves (and of its old subtree) go stale
        FCP.animate(e, { from: r.oldWrap, to: r.newWrap, w: n.w, h: n.h, smart: {
          proto: proto, fromRoot: e.node, toRoot: e.node, kids: kidsFn({ id: e.node, from: e.from, to: e.to }),
          fromEls: r.fromEls, toEls: r.toEls
        } }, ctl || {}).then(function () { FCP.dropDom(layer.el, r.oldWrap); });
        armDelays(layer, [e.node].concat(idsIn(layer, r.newWrap)));
      },
      scroll: scrollTo,
      vars: function () { layers().forEach(function (l) { FCP.refreshScreen(l.el); }); },
      url: function (e) {
        if (!/^(https?|mailto):/i.test(String(e.url || "").trim())) return;   // no javascript:, data:, file:
        if (e.newTab) window.open(e.url, "_blank", "noopener");
        else window.location.href = e.url;
      }
    };

    function rebuild() {
      FCP.finishRunning();
      if (screen) { kill(screen); if (screen.el.parentNode) screen.el.parentNode.removeChild(screen.el); screen = null; }
      showScreen(state.screen, null, null);
    }
    function restart() {
      overlays.slice().forEach(function (l) { closeOverlay(l, null, true); });
      state.restart();
      rebuild();
    }
    function jump(id) { exec([{ type: "navigate", dest: id, transition: { type: "instant" } }]); }

    var P = {
      proto: proto, state: state, device: device, exec: exec, revert: revert, later: later,
      pathAt: pathAt, logicalPath: logicalPath, hasGamepadTriggers: hasGamepad(),
      scale: function () { return view.scale; },
      viewSize: function () { return { w: view.w, h: view.h }; },
      keyLayers: function () {
        return layers().map(function (l) { return l.el._fcp.reg.list.map(function (x) { return x.id; }); });
      },
      restart: restart
    };
    var trig = FCP.wireTriggers(P);
    showScreen(state.screen, null, null);
    FCP._player = P;
    return P;
  };

  if (typeof document !== "undefined" && typeof window !== "undefined") {
    var go = function () { FCP.boot(window.FIGCRAFT_PROTOTYPE); };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go);
    else go();
  }
})();
