// Scene: builds a screen's layer tree as nested absolute divs (DOM only inside functions).
// Geometry: x,y,w,h is the node's unrotated box in its parent; rotation (degrees,
// counter-clockwise as in FigCraft) turns it about its top-left corner.
(function () {
  var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };

  FCP.parentMap = function (proto) {
    var parent = {}, nodes = proto.nodes || {};
    Object.keys(nodes).forEach(function (id) {
      var n = nodes[id];
      (n.children || []).forEach(function (c) { parent[c] = id; });
      if (n.instance && n.instance.variants) Object.keys(n.instance.variants).forEach(function (k) {
        (n.instance.variants[k] || []).forEach(function (c) { parent[c] = id; });
      });
    });
    return parent;
  };

  // Children shown for a node: an instance shows the children of its current variant.
  FCP.kidsOf = function (proto, state, id) {
    var n = (proto.nodes || {})[id];
    if (!n) return [];
    if (n.instance && n.instance.variants) {
      var v = state.variants && state.variants[id] !== undefined ? state.variants[id] : n.instance.variant;
      if (has(n.instance.variants, v)) return n.instance.variants[v] || [];
    }
    return n.children || [];
  };

  // Box size of a node: an instance takes its current variant's size (its "~self" layer),
  // as FigCraft resizes an instance when it switches to a variant of another size.
  FCP.boxOf = function (proto, state, id) {
    var n = (proto.nodes || {})[id];
    if (!n) return { w: 0, h: 0 };
    if (n.instance) {
      var first = FCP.kidsOf(proto, state, id)[0], self = first && proto.nodes[first];
      if (self && /~self$/.test(first)) return { w: self.w, h: self.h };
    }
    return { w: n.w, h: n.h };
  };

  FCP.isHidden = function (state, n) {
    if (!n || n.visible === false) return true;
    var b = n.bindings && n.bindings.visible;
    return b !== undefined && b !== null && !state.vars[b];
  };

  function choosePaint(state, n) {
    var alts = n.alts || [];
    for (var i = 0; i < alts.length; i++) {
      var w = alts[i].when || {}, ok = true;
      Object.keys(w.vars || {}).forEach(function (k) { if (state.vars[k] !== w.vars[k]) ok = false; });
      Object.keys(w.modes || {}).forEach(function (k) { if (state.modes[k] !== w.modes[k]) ok = false; });
      if (ok) return alts[i].paint;
    }
    return n.paint;
  }

  function fmt(v) {
    if (v === undefined || v === null) return "";
    if (typeof v === "number" && !isFinite(v)) return String(v);
    if (typeof v === "number" && Math.round(v) !== v) return String(+v.toFixed(4));
    return String(v);
  }

  function hasDrag(n) {
    var lists = [n.interactions || []], vi = n.instance && n.instance.variantInteractions;
    if (vi) Object.keys(vi).forEach(function (k) { lists.push(vi[k] || []); });
    return lists.some(function (l) { return l.some(function (i) { return i.trigger && i.trigger.type === "drag"; }); });
  }
  function div(cls) { var d = document.createElement("div"); d.className = cls; return d; }
  function px(v) { return (+v || 0) + "px"; }
  function pct(a, b) { return b ? (a / b * 100) + "%" : px(a); }

  // Re-applies everything that depends on variables/modes: paint alts, live text, visibility.
  function refreshEntry(c, e) {
    var n = e.node, st = c.state;
    e.el.style.display = FCP.isHidden(st, n) ? "none" : "";
    if (e.img) {
      var p = choosePaint(st, n);
      if (!p) { e.img.style.display = "none"; }
      else {
        e.img.style.display = "";
        if (e.img.getAttribute("src") !== p.src) e.img.setAttribute("src", p.src);
        e.img.style.left = pct(p.dx, n.w); e.img.style.top = pct(p.dy, n.h);
        e.img.style.width = pct(p.w, n.w); e.img.style.height = pct(p.h, n.h);
      }
    }
    if (e.txt) {
      e.txt.textContent = fmt(st.vars[n.liveText.var]);
      e.txt.style.color = FCP.liveTextColor(st, n.liveText);
    }
  }

  // liveText colour: its bound colour variable's current value (liveText.colorVar), else style.color.
  FCP.liveTextColor = function (state, lt) {
    var v = lt && lt.colorVar !== undefined && state && state.vars ? state.vars[lt.colorVar] : undefined;
    if (typeof v === "string" && v) return v;
    return (lt && lt.style && lt.style.color) || "";
  };

  // css.maskSrc (a data: URI) placed at css.maskBox [x, y, w, h] in the layer's box (px);
  // without a box the mask covers the layer. null when there is no mask.
  FCP.maskCss = function (css) {
    if (!css || !css.maskSrc) return null;
    var b = css.maskBox;
    return { image: "url(\"" + String(css.maskSrc).replace(/"/g, "%22") + "\")",
             position: b ? px(b[0]) + " " + px(b[1]) : "0px 0px",
             size: b ? px(b[2]) + " " + px(b[3]) : "100% 100%" };
  };

  function applyCss(el, n) {
    var c = n.css || {}, s = el.style;
    if (c.radius) s.borderRadius = c.radius.map(px).join(" ");
    if (c.backdropBlur) { s.backdropFilter = "blur(" + px(c.backdropBlur) + ")"; s.webkitBackdropFilter = s.backdropFilter; }
    if (c.layerBlur) s.filter = "blur(" + px(c.layerBlur) + ")";
    if (c.blend) s.mixBlendMode = c.blend;
    var m = FCP.maskCss(c);
    if (m) {
      s.maskImage = s.webkitMaskImage = m.image;
      s.maskPosition = s.webkitMaskPosition = m.position;
      s.maskSize = s.webkitMaskSize = m.size;
      s.maskRepeat = s.webkitMaskRepeat = "no-repeat";
    }
  }

  function extent(c, ids) {
    var w = 0, h = 0;
    ids.forEach(function (id) {
      var n = c.proto.nodes[id];
      if (!n || n.position === "fixed" || n.position === "sticky") return;
      w = Math.max(w, n.x + n.w); h = Math.max(h, n.y + n.h);
    });
    return { w: w, h: h };
  }

  // Scroll area inside host (box bw x bh): returns {scroller, pinned}; kids are added later.
  function scrollArea(c, host, ovf, ids, bw, bh) {
    var sc = div("fcp-scroll"), pin = div("fcp-pinned"), ex = extent(c, ids), sp = div("fcp-spacer");
    sc.style.overflowX = ovf === "horizontal" || ovf === "both" ? "auto" : "hidden";
    sc.style.overflowY = ovf === "vertical" || ovf === "both" ? "auto" : "hidden";
    sp.style.left = px(Math.max(bw, ex.w) - 1); sp.style.top = px(Math.max(bh, ex.h) - 1);
    sc.appendChild(sp);
    host.appendChild(sc); host.appendChild(pin);
    var area = { scroller: sc, pinned: pin, sticky: [] };
    sc.addEventListener("scroll", function () { FCP.updateSticky(area); });
    c.areas.push(area);
    return area;
  }
  FCP.updateSticky = function (area) {
    var sc = area.scroller;
    area.sticky.forEach(function (s) {
      var x = s.node.x - sc.scrollLeft, y = s.node.y - sc.scrollTop;   // stops at the edge
      s.el.style.left = px(s.node.x >= 0 ? Math.max(x, 0) : x);
      s.el.style.top = px(s.node.y >= 0 ? Math.max(y, 0) : y);
    });
  };

  function addKids(c, ids, into, area) {
    ids.forEach(function (id) {
      var n = c.proto.nodes[id];
      if (!n) return;
      var pinned = area && (n.position === "fixed" || n.position === "sticky");
      var el = buildNode(c, id);
      (pinned ? area.pinned : into).appendChild(el);
      if (pinned && n.position === "sticky") area.sticky.push({ el: el, node: n });
    });
  }

  function variantWrap(c, instId) {
    var w = div("fcp-var");
    addKids(c, FCP.kidsOf(c.proto, c.state, instId), w, null);
    return w;
  }

  function buildNode(c, id, isRoot) {
    var n = c.proto.nodes[id], el = div("fcp-node"), s = el.style;
    el.setAttribute("data-fcp-id", id);
    var box = isRoot ? { w: n.w, h: n.h } : FCP.boxOf(c.proto, c.state, id);
    s.left = px(isRoot ? 0 : n.x); s.top = px(isRoot ? 0 : n.y); s.width = px(box.w); s.height = px(box.h);
    if (n.rotation) s.transform = "rotate(" + (-n.rotation) + "deg)";
    if (n.opacity !== undefined && n.opacity < 1) s.opacity = n.opacity;
    s.pointerEvents = n.kind === "group" ? "none" : "auto";
    if (hasDrag(n)) s.touchAction = "none";   // a touch drag reaches the drag trigger, not scrolling
    applyCss(el, n);
    var e = { id: id, node: n, el: el, img: null, txt: null };
    if (n.paint || (n.alts && n.alts.length)) {
      e.img = document.createElement("img");
      e.img.className = "fcp-paint"; e.img.alt = ""; e.img.draggable = false;
      el.appendChild(e.img);
    }
    if (n.liveText) {
      var st = n.liveText.style || {}, t = div("fcp-text");
      t.style.fontFamily = st.fontFamily || ""; t.style.fontSize = px(st.fontSize || 14);
      t.style.fontWeight = st.fontWeight || ""; t.style.lineHeight = st.lineHeight ? px(st.lineHeight) : "normal";
      t.style.letterSpacing = px(st.letterSpacing); t.style.color = st.color || "";
      t.style.textAlign = st.align || "left";
      el.appendChild(t); e.txt = t;
    }
    c.reg.byId[id] = e; c.reg.list.push(e);
    refreshEntry(c, e);
    if (isRoot) return el;
    var ids = FCP.kidsOf(c.proto, c.state, id), host = el, area = null;
    var ovf = n.overflow && n.overflow !== "none" ? n.overflow : null;
    if (ovf) { area = scrollArea(c, el, ovf, ids, n.w, n.h); host = area.scroller; }
    else if (n.clip) { host = div("fcp-clip"); if (s.borderRadius) host.style.borderRadius = s.borderRadius; el.appendChild(host); }
    if (n.instance) { e.varWrap = variantWrap(c, id); host.appendChild(e.varWrap); }
    else addKids(c, ids, host, area);
    return el;
  }

  // buildScreen(proto, state, screenId, opts?) -> .fcp-screen element; opts.viewH overrides
  // the viewport height (tall frames) and opts.scroll forces the root to scroll vertically.
  FCP.buildScreen = function (proto, state, screenId, opts) {
    opts = opts || {};
    var scr = proto.screens[screenId], rootId = scr.root, root = proto.nodes[rootId];
    var viewH = opts.viewH || scr.height;
    var c = { proto: proto, state: state, reg: { byId: {}, list: [] }, areas: [] };
    var el = div("fcp-screen"), bg = div("fcp-bg");
    el.style.width = px(scr.width); el.style.height = px(viewH);
    bg.style.background = scr.background || "transparent";
    el.appendChild(bg);
    var ovf = scr.overflow && scr.overflow !== "none" ? scr.overflow : "none";
    if (opts.scroll) ovf = ovf === "horizontal" || ovf === "both" ? "both" : "vertical";
    var ids = FCP.kidsOf(proto, state, rootId);
    var area = scrollArea(c, el, ovf, ids, scr.width, Math.max(viewH, root.h));
    var rootEl = buildNode(c, rootId, true);
    if (root.clip && ovf === "none") rootEl.style.overflow = "hidden";
    area.scroller.insertBefore(rootEl, area.scroller.firstChild);
    var e = c.reg.byId[rootId];
    if (root.instance) { e.varWrap = variantWrap(c, rootId); rootEl.appendChild(e.varWrap); }
    else addKids(c, ids, rootEl, area);
    c.areas.forEach(FCP.updateSticky);
    el._fcp = { screen: screenId, root: rootId, bg: bg, rootEl: rootEl, area: area, ctx: c, reg: c.reg };
    return el;
  };

  FCP.refreshScreen = function (screenEl) {
    var c = screenEl._fcp.ctx;
    c.reg.list.forEach(function (e) { refreshEntry(c, e); });
  };

  // Builds the instance's current-variant children in a new wrapper next to the old one.
  FCP.swapVariantDom = function (screenEl, instId) {
    var c = screenEl._fcp.ctx, e = c.reg.byId[instId];
    if (!e || !e.varWrap) return null;
    var before = {}, oldWrap = e.varWrap;
    Object.keys(c.reg.byId).forEach(function (k) { before[k] = c.reg.byId[k].el; });
    var nw = variantWrap(c, instId);
    oldWrap.parentNode.appendChild(nw);
    if (e.el !== screenEl._fcp.rootEl) {
      var box = FCP.boxOf(c.proto, c.state, instId);
      e.el.style.width = px(box.w); e.el.style.height = px(box.h);
    }
    e.varWrap = nw;
    return { oldWrap: oldWrap, newWrap: nw, fromEls: before, toEls: elsOf(c) };
  };
  function elsOf(c) { var o = {}; Object.keys(c.reg.byId).forEach(function (k) { o[k] = c.reg.byId[k].el; }); return o; }

  // Removes a subtree element and its registry entries.
  FCP.dropDom = function (screenEl, el) {
    var c = screenEl._fcp.ctx;
    c.reg.list = c.reg.list.filter(function (e) {
      if (!el.contains(e.el)) return true;
      if (c.reg.byId[e.id] === e) delete c.reg.byId[e.id];
      return false;
    });
    if (el.parentNode) el.parentNode.removeChild(el);
  };
  FCP.elsOfScreen = function (screenEl) { return elsOf(screenEl._fcp.ctx); };
})();
