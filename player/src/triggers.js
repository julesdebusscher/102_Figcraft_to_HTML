// Pointer, keyboard, gamepad and timer triggers. DOM only inside functions.
// P (from boot): {proto, state, device, pathAt(target), exec(actions, nodeId, opts) -> fx,
// revert(fx), later(nodeId, ms, fn), keyLayers() -> [[nodeId]] top-most first,
// logicalPath(id), scale(), viewSize() -> {w, h}}.
(function () {
  // Standard Gamepad API layout, by button index (face buttons by position).
  // Names as FigCraft's docs list them ("Gamepad A" … "Gamepad Home").
  FCP.GAMEPAD_BUTTONS = ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "View", "Menu",
                         "LS", "RS", "Up", "Down", "Left", "Right", "Home"];
  var MOD_KEYS = { Shift: 1, Control: 1, Alt: 1, Meta: 1, AltGraph: 1, CapsLock: 1 };
  var DRAG_MIN = 5;

  // While hovering: the layer that owns the hover keeps it as long as the pointer stays
  // inside it, even when what it shows no longer has a hover trigger (an interactive
  // component's Hover variant). Only a pointer that left it resolves anew.
  // -> {keep: true} or {r: resolve result | null}
  FCP.hoverStep = function (proto, state, path, owner) {
    if (owner !== null && owner !== undefined && path.indexOf(owner) >= 0) return { keep: true };
    return { r: FCP.resolve(proto, state, path, "hover") };
  };

  FCP.wireTriggers = function (P) {
    var hoverOwner = null, hoverFx = null, prevPath = [], press = null, gen = 0;
    function resolve(path, type, kev) { return FCP.resolve(P.proto, P.state, path, type, kev); }
    function fire(r, opts) {
      if (!r) return null;
      var d = +r.interaction.trigger.delayMs || 0;
      if (d > 0) { P.later(r.nodeId, d, function () { P.exec(r.interaction.actions, r.nodeId); }); return null; }
      return P.exec(r.interaction.actions, r.nodeId, opts);
    }
    function inPath(path, id) { return path.indexOf(id) >= 0; }

    function updateHover(path) {
      var step = FCP.hoverStep(P.proto, P.state, path, hoverOwner);
      if (!step.keep) {
        var h = step.r, old = hoverFx;
        hoverOwner = h ? h.nodeId : null; hoverFx = null;
        if (old) P.revert(old);
        if (h) {
          var g = gen, fx = fire(h, { transient: h.nodeId });
          if (g === gen) hoverFx = fx;   // a screen change in between already ended the hover
          else return;
        }
      }
      var lv = resolve(prevPath, "mouseLeave");
      if (lv && !inPath(path, lv.nodeId)) fire(lv);
      var en = resolve(path, "mouseEnter");
      if (en && !inPath(prevPath, en.nodeId)) fire(en);
      prevPath = path;
    }

    function onMove(ev) {
      if (ev.pointerType !== "touch" || press) updateHover(P.pathAt(ev.target, true));
      if (!press || ev.pointerId !== press.id) return;
      var s = P.scale(), dx = (ev.clientX - press.x) / s, dy = (ev.clientY - press.y) / s;
      if (!press.moved && Math.sqrt(dx * dx + dy * dy) > DRAG_MIN) {
        press.moved = true;
        var dr = press.drag;
        if (dr) {
          var dir = FCP.dragDirection(dr.interaction.actions);
          if (!dir) P.exec(dr.interaction.actions, dr.nodeId);
          else if (FCP.dragGoes(dir, dx, dy)) {
            press.scrub = { ctl: { scrub: true }, dir: dir };
            P.exec(dr.interaction.actions, dr.nodeId, { ctl: press.scrub.ctl });
          }
        }
      }
      if (press && press.scrub && press.scrub.ctl.seek) {
        var v = P.viewSize(), d = press.scrub.dir;
        var p = d === "left" ? -dx / v.w : d === "right" ? dx / v.w : d === "top" ? -dy / v.h : dy / v.h;
        press.scrub.ctl.seek(Math.max(0, Math.min(1, p)));
      }
    }

    function onDown(ev) {
      if (ev.button !== 0 || press) return;
      var path = P.pathAt(ev.target);
      if (!path.length) return;
      if (ev.pointerType === "touch") updateHover(path);
      var pr = { id: ev.pointerId, path: path, x: ev.clientX, y: ev.clientY, moved: false };
      press = pr;
      fire(resolve(path, "mouseDown"));
      if (press !== pr) return;                 // it changed the screen: the press is over
      var r = resolve(path, "press"), fx = fire(r, r ? { transient: r.nodeId } : null);
      if (press !== pr) return;
      pr.fx = fx;
      pr.drag = resolve(path, "drag");
    }

    function endPress(ev, cancelled) {
      if (!press || ev.pointerId !== press.id) return;
      var pr = press;
      press = null;
      if (pr.fx) P.revert(pr.fx);
      if (pr.scrub && pr.scrub.ctl.play) pr.scrub.ctl.play();
      if (cancelled) return;
      var up = P.pathAt(ev.target);
      fire(resolve(up, "mouseUp"));
      if (!pr.moved) {
        var c = resolve(pr.path, "click");
        if (c && inPath(up, c.nodeId)) fire(c);
      }
      if (ev.pointerType === "touch") updateHover([]);
    }

    function fireKey(kev) {
      var layers = P.keyLayers();
      for (var i = 0; i < layers.length; i++) {
        for (var j = layers[i].length - 1; j >= 0; j--) {
          var id = layers[i][j], r = resolve(P.logicalPath(id), "key", kev);
          if (r && r.nodeId === id) { fire(r); return true; }
        }
      }
      return false;
    }

    function onKey(ev) {
      if (ev.repeat || MOD_KEYS[ev.key]) return;
      if (fireKey({ key: ev.key, shift: ev.shiftKey, ctrl: ev.ctrlKey, alt: ev.altKey, meta: ev.metaKey })) ev.preventDefault();
    }

    // Gamepad polling only while a key trigger names a controller button and the window has focus.
    var pads = {}, polling = false;
    function poll() {
      if (!document.hasFocus()) { polling = false; return; }
      var list = navigator.getGamepads ? navigator.getGamepads() : [];
      for (var i = 0; i < list.length; i++) {
        var g = list[i];
        if (!g || g.mapping !== "standard") continue;
        var was = pads[g.index] || [];
        g.buttons.forEach(function (b, k) {
          if (b.pressed && !was[k] && FCP.GAMEPAD_BUTTONS[k]) fireKey({ gamepad: FCP.GAMEPAD_BUTTONS[k] });
          was[k] = b.pressed;
        });
        pads[g.index] = was;
      }
      requestAnimationFrame(poll);
    }
    function startPoll() { if (!polling && P.hasGamepadTriggers) { polling = true; requestAnimationFrame(poll); } }

    P.device.addEventListener("pointerdown", onDown);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", function (ev) { endPress(ev, false); });
    window.addEventListener("pointercancel", function (ev) { endPress(ev, true); });
    P.device.addEventListener("pointerleave", function (ev) { if (ev.pointerType !== "touch") updateHover([]); });
    P.device.addEventListener("dragstart", function (ev) { ev.preventDefault(); });
    window.addEventListener("keydown", onKey);
    window.addEventListener("focus", startPoll);
    startPoll();

    return {
      // The layers under the pointer change (new screen, overlay): hover and press end, so
      // their variant changes revert (a button left while hovered shows its default again).
      reset: function () {
        gen++;
        var fx = (hoverFx || []).concat(press && press.fx || []).filter(function (e) { return e.kind === "variant"; });
        hoverOwner = null; hoverFx = null; prevPath = [];
        // A drag that started this change keeps driving its transition until release.
        if (press && press.scrub) press.fx = null; else press = null;
        if (fx.length) P.revert(fx);
      }
    };
  };
})();
