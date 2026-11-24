// Hit-testing and trigger resolution. Pure: no DOM. See the data.js contract in the plan.
// Instances play the interactions of the variant they show, taken from
// node.instance.variantInteractions[variantKey] (contract extension); the instance's own
// interactions win per trigger type.
(function () {
  var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };

  FCP.interactionsFor = function (proto, state, nodeId) {
    var n = (proto.nodes || {})[nodeId];
    if (!n) return [];
    var own = n.interactions || [];
    var vi = n.instance && n.variantInteractions;
    if (!n.instance || !vi) return own.slice();
    var shown = state && state.variants && state.variants[nodeId] !== undefined ? state.variants[nodeId] : n.instance.variant;
    var fromVariant = has(vi, shown) ? vi[shown] || [] : [];
    var ownTypes = {};
    own.forEach(function (i) { ownTypes[i.trigger.type] = true; });
    return own.concat(fromVariant.filter(function (i) { return !ownTypes[i.trigger.type]; }));
  };

  function hidden(proto, state, n) {
    if (!n) return false;
    if (n.visible === false) return true;
    var b = n.bindings && n.bindings.visible;
    return b !== undefined && b !== null && !(state && state.vars && state.vars[b]);
  }

  var MODS = { shift: "shift", ctrl: "ctrl", control: "ctrl", alt: "alt", option: "alt", meta: "meta", cmd: "meta", command: "meta" };
  function normKey(k) {
    k = String(k);
    if (k === " ") return "space";
    return k.toLowerCase();
  }
  FCP.keyMatches = function (spec, ev) {
    if (typeof spec !== "string" || !ev) return false;
    var g = /^gamepad\s+(.+)$/i.exec(spec);
    if (g) return ev.gamepad !== undefined && String(ev.gamepad).toLowerCase() === g[1].trim().toLowerCase();
    if (ev.gamepad !== undefined || ev.key === undefined) return false;
    var parts = spec.split("+").map(function (s) { return s.trim(); });
    var key = parts.pop();
    if (key === "" && parts.length && parts[parts.length - 1] === "") { parts.pop(); key = "+"; }
    var want = { shift: false, ctrl: false, alt: false, meta: false };
    for (var i = 0; i < parts.length; i++) {
      var m = MODS[parts[i].toLowerCase()];
      if (!m) return false;
      want[m] = true;
    }
    if (want.shift !== !!ev.shift || want.ctrl !== !!ev.ctrl || want.alt !== !!ev.alt || want.meta !== !!ev.meta) return false;
    return normKey(key) === normKey(ev.key);
  };

  // pathTopDown: layers under the pointer, top-most layer first, down to the screen root.
  // A hidden layer hides everything beneath it in the tree, i.e. itself and all earlier
  // entries (its descendants).
  FCP.resolve = function (proto, state, pathTopDown, triggerType, keyEvent) {
    var nodes = proto.nodes || {}, path = pathTopDown || [], firstVisible = 0;
    for (var h = path.length - 1; h >= 0; h--) {
      if (hidden(proto, state, nodes[path[h]])) { firstVisible = h + 1; break; }
    }
    for (var i = firstVisible; i < path.length; i++) {
      var list = FCP.interactionsFor(proto, state, path[i]);
      for (var j = 0; j < list.length; j++) {
        var it = list[j];
        if (it.trigger.type !== triggerType) continue;
        if (triggerType === "key" && !FCP.keyMatches(it.trigger.key, keyEvent)) continue;
        return { nodeId: path[i], interaction: it };
      }
    }
    return null;
  };
})();
