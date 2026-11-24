// Prototype state machine. Pure: no DOM. See the data.js contract in the plan.
FCP.createState = function (proto) {
  var nodes = proto.nodes || {}, screens = proto.screens || {};
  var colls = (proto.variables && proto.variables.collections) || {};
  var varDefs = (proto.variables && proto.variables.vars) || {};
  var parent = {};
  Object.keys(nodes).forEach(function (id) {
    var n = nodes[id];
    (n.children || []).forEach(function (c) { parent[c] = id; });
    if (n.instance && n.instance.variants) {
      Object.keys(n.instance.variants).forEach(function (k) {
        (n.instance.variants[k] || []).forEach(function (c) { parent[c] = id; });
      });
    }
  });

  var State = { screen: proto.start, overlays: [], vars: {}, modes: {}, variants: {} };
  var history = [];      // [{screen, transition}] screen we left + the transition used to leave it
  var ovTrans = [];      // parallel to State.overlays: transition used to open each overlay

  var overrides = {};    // setVariable writes apply in every mode
  function clearObj(o) { Object.keys(o).forEach(function (k) { delete o[k]; }); }
  function recompute() {
    Object.keys(varDefs).forEach(function (v) {
      if (Object.prototype.hasOwnProperty.call(overrides, v)) { State.vars[v] = overrides[v]; return; }
      var d = varDefs[v];
      State.vars[v] = d.valuesByMode ? d.valuesByMode[State.modes[d.collection]] : undefined;
    });
  }
  function resetVars() {
    overrides = {};
    clearObj(State.vars); clearObj(State.modes);
    Object.keys(colls).forEach(function (c) { State.modes[c] = colls[c].defaultMode; });
    recompute();
  }
  function overlayEntry(a, ctx) {
    return { id: a.dest, sourceNodeId: ctx && ctx.nodeId, position: a.position, anchor: a.anchor,
             offset: a.offset, closeOnClickOutside: a.closeOnClickOutside, background: a.background };
  }
  function overlayFx(kind, e, a) {
    return { kind: kind, id: e.id, transition: a.transition, position: e.position, anchor: e.anchor,
             offset: e.offset, closeOnClickOutside: e.closeOnClickOutside, background: e.background,
             sourceNodeId: e.sourceNodeId };
  }
  function getVar(id) { return State.vars[id]; }
  function hasScreen(id) { return Object.prototype.hasOwnProperty.call(screens, id); }
  function instanceFor(nodeId, variant) {
    var id = nodeId, guard = 0;
    while (id !== undefined && guard++ < 10000) {
      var n = nodes[id];
      if (!n) return null;
      if (n.instance && n.instance.variants && Object.prototype.hasOwnProperty.call(n.instance.variants, variant)) return id;
      id = parent[id];
    }
    return null;
  }
  function closeAll(fx) {
    while (State.overlays.length) {
      var o = State.overlays.pop(), t = ovTrans.pop();
      fx.push({ kind: "overlayClose", id: o.id, transition: t });
    }
  }

  function exec(a, ctx, fx) {
    if (!a) return;
    switch (a.type) {
      case "navigate":
        if (!hasScreen(a.dest)) return;
        closeAll(fx);
        history.push({ screen: State.screen, transition: a.transition });
        fx.push({ kind: "screen", from: State.screen, to: a.dest, transition: a.transition, preserveScroll: !!a.preserveScroll });
        State.screen = a.dest;
        return;
      case "back":
        if (State.overlays.length) {
          var o = State.overlays.pop(), t = ovTrans.pop();
          fx.push({ kind: "overlayClose", id: o.id, transition: t });
        } else if (history.length) {
          var h = history.pop();
          fx.push({ kind: "screen", from: State.screen, to: h.screen, transition: h.transition, reverse: true });
          State.screen = h.screen;
        }
        return;
      case "closeOverlay":
        if (State.overlays.length) {
          var c = State.overlays.pop(), ct = ovTrans.pop();
          fx.push({ kind: "overlayClose", id: c.id, transition: ct });
        }
        return;
      case "openOverlay":
        if (!hasScreen(a.dest)) return;
        var oe = overlayEntry(a, ctx);
        State.overlays.push(oe);
        ovTrans.push(a.transition);
        fx.push(overlayFx("overlayOpen", oe, a));
        return;
      case "swapOverlay":
        if (!hasScreen(a.dest)) return;
        if (State.overlays.length) {
          var se = overlayEntry(a, ctx);
          State.overlays[State.overlays.length - 1] = se;
          ovTrans[ovTrans.length - 1] = a.transition;
          fx.push(overlayFx("overlaySwap", se, a));
        } else {
          var ne = overlayEntry(a, ctx);
          State.overlays.push(ne);
          ovTrans.push(a.transition);
          fx.push(overlayFx("overlayOpen", ne, a));
        }
        return;
      case "scrollTo":
        if (!hasScreen(a.dest) && !nodes[a.dest]) return;
        fx.push({ kind: "scroll", target: a.dest, offset: a.offset, transition: a.transition });
        return;
      case "openUrl":
        fx.push({ kind: "url", url: a.url, newTab: !!a.newTab });
        return;
      case "changeTo":
        var inst = instanceFor(ctx && ctx.nodeId, a.variant);
        if (inst === null) return;
        var meta = nodes[inst].instance;
        var from = State.variants[inst] !== undefined ? State.variants[inst] : meta.variant;
        if (from === a.variant) return;
        State.variants[inst] = a.variant;
        fx.push({ kind: "variant", node: inst, from: from, to: a.variant, transition: a.transition });
        return;
      case "setVariable":
        if (!Object.prototype.hasOwnProperty.call(varDefs, a.variable)) return;
        overrides[a.variable] = a.expr !== undefined ? FCP.evalExpr(a.expr, getVar) : a.value;
        recompute();
        fx.push({ kind: "vars" });
        return;
      case "setVariableMode":
        if (!Object.prototype.hasOwnProperty.call(colls, a.collection)) return;
        if (!colls[a.collection].modes || !Object.prototype.hasOwnProperty.call(colls[a.collection].modes, a.mode)) return;
        State.modes[a.collection] = a.mode;
        recompute();
        fx.push({ kind: "vars" });
        return;
      case "conditional":
        var blocks = a.blocks || [];
        for (var i = 0; i < blocks.length; i++) {
          var b = blocks[i];
          if (!b.condition || FCP.evalExpr(b.condition, getVar)) {
            (b.actions || []).forEach(function (x) { exec(x, ctx, fx); });
            return;
          }
        }
        return;
    }
  }

  State.run = function (actions, ctx) {
    var fx = [];
    (actions || []).forEach(function (a) {
      try { exec(a, ctx || {}, fx); } catch (e) { /* never throw out of the player */ }
    });
    return fx;
  };
  State.restart = function () {
    State.screen = proto.start; State.overlays.length = 0; clearObj(State.variants);
    history = []; ovTrans = [];
    resetVars();
  };
  resetVars();
  return State;
};
