// Top bar and collapsible side panel (mockup A). DOM only inside functions. UI text in French.
(function () {
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  // buildChrome(proto, {onJump(screenId), onRestart()}) -> {bar, panel, setCurrent(screenId)}
  FCP.buildChrome = function (proto, h) {
    var bar = el("header", "fcp-bar"), panel = el("nav", "fcp-panel"), items = {};
    var toggle = el("button", "fcp-btn fcp-toggle", "◧");
    toggle.type = "button"; toggle.title = "Afficher ou masquer la liste des écrans";
    toggle.setAttribute("aria-label", toggle.title);
    toggle.setAttribute("aria-expanded", "true");
    var title = el("span", "fcp-title", proto.title || "Prototype");
    var restart = el("button", "fcp-btn fcp-restart", "↺ Redémarrer");
    restart.type = "button"; restart.title = "Redémarrer : revenir au premier écran et tout remettre à zéro";
    restart.setAttribute("aria-label", "Redémarrer");
    bar.appendChild(toggle); bar.appendChild(title); bar.appendChild(el("span", "fcp-sp")); bar.appendChild(restart);
    panel.setAttribute("aria-label", "Écrans");

    (proto.panel || []).forEach(function (sec) {
      var head = proto.pageName || "";
      if (sec.section) head = head ? head + " · " + sec.section : sec.section;
      if (head) panel.appendChild(el("div", "fcp-sec", head));
      var list = el("ul", "fcp-list");
      (sec.screens || []).forEach(function (id) {
        var s = proto.screens[id];
        if (!s) return;
        var li = el("li"), b = el("button", "fcp-item", s.name);
        b.type = "button"; b.title = s.name;
        b.addEventListener("click", function () { b.blur(); h.onJump(id); });
        li.appendChild(b); list.appendChild(li); items[id] = b;
      });
      panel.appendChild(list);
    });

    toggle.addEventListener("click", function () {
      toggle.blur();
      var closed = document.body.classList.toggle("fcp-panel-closed");
      toggle.setAttribute("aria-expanded", closed ? "false" : "true");
    });
    restart.addEventListener("click", function () { restart.blur(); h.onRestart(); });

    return {
      bar: bar, panel: panel,
      setCurrent: function (id) {
        Object.keys(items).forEach(function (k) {
          var on = k === id;
          items[k].classList.toggle("on", on);
          if (on) items[k].setAttribute("aria-current", "page"); else items[k].removeAttribute("aria-current");
        });
      }
    };
  };
})();
