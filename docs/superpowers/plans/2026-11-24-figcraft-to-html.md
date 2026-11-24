# FigCraft → HTML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Revision 2 (2026-11-24):** Task 1 proved a FigCraft plugin cannot render layers (`file.*` refused). The user chose an external **Python** tool driving FigCraft over its control channel, to run on a **Windows** machine that only has Python 3. Tasks 0–1 are done; Tasks 2–5 (player) are unchanged; Tasks 6–11 are rewritten. Findings: `docs/figcraft-api-notes.md`.

**Goal:** A stdlib-only Python tool that, with FigCraft open, exports the selected frames to a folder holding a standalone, file://-openable HTML/JS/CSS clickable prototype that replays every FigCraft prototype interaction, with a side panel to jump between frames.

**Architecture:** Two halves joined by one data contract. (1) A Python package `figcraft_export` talks to FigCraft (`--control <port>`, newline JSON on 127.0.0.1), walks the selection, reads `document.json` for what `node.get` omits, renders each layer's own paint with `file.export`, writes `data.js` (the contract below), the player and the assets into a folder. (2) A dependency-free JS player (classic scripts concatenated into `player.js`) rebuilds the layer tree as absolutely positioned DOM and runs triggers, actions, variables, transitions and Smart Animate.

**Tech Stack:** Python ≥ 3.8 standard library only (`socket`, `json`, `base64`, `subprocess`, `unittest`, optional `tkinter`); vanilla ES2020 JS + CSS (no modules, no fetch); JS logic tests with macOS `jsc` (dev only); end-to-end against `/Applications/FigCraft.app` 0.18.1 on this Mac; Windows launchers `.bat`.

**Spec:** `docs/superpowers/specs/2026-11-24-figcraft-to-html-design.md`

## Global Constraints

- Target machine: **Windows with Python 3 and FigCraft only.** Python ≥ 3.8, standard library only, no `pip install`; source must parse with `ast.parse(..., feature_version=(3, 8))` and avoid 3.9+ APIs (`str.removeprefix`, `list[int]` annotations, `zoneinfo`, …).
- All text files written/read with explicit `encoding="utf-8"`; console output survives cp1252/cp65001 consoles (`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` when available); paths via `pathlib`, never string concatenation; paths with spaces and accents must work.
- Control channel: `127.0.0.1:<port>`, default port **47917**, newline-delimited JSON `{id, method, params}`; renders via `engine.execute {command:"file.export", params:{ids:[id], format:"svg"|"png", scale}}` → `{format, data(base64)}`.
- Every temporary document edit is undone before the tool exits, on success **and** on error; at the end `document.json` (from `file.saveAs {data:true}`) must hash the same as at the start, else print a loud French warning.
- Export must open by double-click (`file://`) in Chrome, Edge and Firefox: no `type="module"`, no `fetch`, no XHR; data ships as `data.js` setting `window.FIGCRAFT_PROTOTYPE`.
- Output folder layout: `index.html`, `player.js`, `player.css`, `data.js`, `assets/`. Asset file names use sanitised layer ids only (`[A-Za-z0-9_~-]`).
- Export scope = current page's selected top-level frames; panel lists only those, grouped by section; transitive closure follows every link (navigate, overlays, change to) at any depth on any page, unselected targets exported but not listed; a missing link target is reported, never silently dropped.
- Start screen = page flow starting point if selected, else first selected frame in layer order; "Redémarrer" returns there and clears history and variables.
- Variables: visibility, string and number text live; bound colours and mode switches pre-rendered for reachable values (cap 32 alternatives per layer, beyond → reported as approximated).
- Backdrop blur, glass, blend modes, masks, non-rectangular clips → CSS approximation, listed in the end-of-export summary.
- Behaviour reference: FigCraft `docs/prototyping-parity.md` (the presenter's behaviour wins on any doubt).
- User-facing text (console summary, errors, launcher prompts, panel) in French.
- FigCraft version check: refuse versions < 0.18.1 with `FigCraft 0.18.1 ou plus récent est nécessaire (trouvé : X).`

## Review Focus

1. **FigCraft not started via the launcher** (no control port) → `Impossible de joindre FigCraft. Ouvrez-le avec « Ouvrir FigCraft ».` and exit code 1, no traceback. Test in Task 6.
2. **Bad selection** (nothing, non-frame, nested frame) → `Sélectionnez au moins une frame de premier niveau.` when nothing usable; skipped layers named in the summary. Test in Task 7.
3. **Windows paths and encoding** (destination `C:\Users\Élodie\Mes prototypes\`, frame named `Écran / 🚀 "test"`, cp1252 console) → folder written, names intact in `data.js`, no `UnicodeEncodeError`. Tests in Tasks 6 and 10.
4. **Crash mid-render** (FigCraft closes or an export fails halfway) → all temporary edits undone that can be, partial output folder removed, French error. Test in Task 9.
5. **Broken links** (destination deleted or hidden, a missing variant) → hotspot does nothing, export succeeds, link named in summary; player never throws. Tests in Tasks 3 and 7.

---

## Shared contract: `data.js`

Both halves code against this. The Python exporter (Tasks 7–10) emits it; the player reads it; `player/fixtures/demo.data.js` (Task 2) is its reference instance. Ids are strings (FigCraft layer ids stringified; instance-variant clones are `"<instanceId>~<variantId>~<childId>"`).

```text
window.FIGCRAFT_PROTOTYPE = {
  version: 1,
  title: string,                       // file name or first page name
  start: ScreenId,
  panel: [{ section: string|null, screens: [ScreenId] }],   // page name in `pageName`
  pageName: string,
  screens: { [ScreenId]: { name, width, height, background: css-color, root: NodeId,
                           overflow: "none"|"horizontal"|"vertical"|"both" } },
  nodes:   { [NodeId]: Node },
  variables: { collections: { [CollId]: { name, defaultMode: ModeId, modes: {[ModeId]: name} } },
               vars: { [VarId]: { name, collection: CollId, type: "number"|"string"|"boolean"|"color",
                                  valuesByMode: {[ModeId]: value} } } },
  report: { approximated: [string], skipped: [string] }
}
Node = { id, name, kind: "frame"|"group"|"instance"|"leaf"|"text",
  x, y, w, h, rotation, opacity, visible,                      // relative to parent box
  clip: bool, overflow: as screen, position: "scroll"|"fixed"|"sticky",
  paint: Paint|null,                                           // own paint only, never children
  alts: [{ when: { vars?: {[VarId]: value}, modes?: {[CollId]: ModeId} }, paint: Paint }],
  css: { backdropBlur?: px, layerBlur?: px, blend?: css-blend, radius?: [tl,tr,br,bl], clipPath?: svg-path, maskSrc?: path },
  liveText: { var: VarId, style: { fontFamily, fontSize, fontWeight, lineHeight, letterSpacing, color, align } } | null,
  bindings: { visible?: VarId },
  instance: { set: string, variant: VariantKey, variants: {[VariantKey]: [NodeId]} } | null, // children per variant
  children: [NodeId],
  interactions: [Interaction] }
Paint = { src: "assets/<file>", dx, dy, w, h }                 // offset/size vs node box (shadows overflow)
Interaction = { trigger: Trigger, actions: [Action] }
Trigger = { type: "click"|"hover"|"press"|"drag"|"mouseEnter"|"mouseLeave"|"mouseDown"|"mouseUp"|"afterDelay"|"key",
            delayMs?: number, key?: string }                   // key: "Shift+K", "Gamepad A"
Action = {type:"navigate", dest, preserveScroll?, transition}
       | {type:"back"} | {type:"closeOverlay"}
       | {type:"scrollTo", dest, offset?:[x,y], transition}
       | {type:"openOverlay"|"swapOverlay", dest, position, anchor?:"triggerInside"|"triggerOutside",
          offset?:[x,y], closeOnClickOutside: bool, background?: css-color, transition}
       | {type:"openUrl", url, newTab: bool}
       | {type:"changeTo", variant: VariantKey, transition}
       | {type:"setVariable", variable, value?: any, expr?: Expr}
       | {type:"setVariableMode", collection, mode}
       | {type:"conditional", blocks:[{condition?: Expr, actions:[Action]}]}
Transition = { type: "instant"|"dissolve"|"smartAnimate"|"moveIn"|"moveOut"|"push"|"slideIn"|"slideOut",
               direction?: "left"|"right"|"top"|"bottom", durationMs,
               easing: { type: string, bezier?: [x1,y1,x2,y2], spring?: {mass, stiffness, damping} } }
Expr = { value: { type, value } } | { op: { op, args: [Expr] } }  // FigCraft's own shape, passed through
```

Contract extension: `Node.instance` may carry optional `variantInteractions: {[VariantKey]: [Interaction]}` (the interactions of each variant's component); the player plays the shown variant's, overridden per trigger type by the instance's own `interactions`. `FCP.resolve`'s path is ordered top-most layer first (leaf → screen root).

`position` values for overlays are FigCraft's (`center`, `topLeft`, …, `manual`). Easing `type` names are FigCraft's 13 (record the exact ids in Task 1).

## File Structure

```
player/                         (Tasks 2–5, unchanged)
  src/ORDER  src/*.js  player.css  index.html
  test/harness.js  test/run.sh  test/*.test.js     (jsc, dev only)
  fixtures/demo.data.js  fixtures/assets/  dev/index.html
exporter/
  figcraft_export/
    __init__.py   __main__.py      CLI: python -m figcraft_export launch|export
    control.py    Control client (moved from tools/fcctl.py)
    launcher.py   find FigCraft.exe / app, config.json, start with --control
    docfile.py    document.json (from file.saveAs {data:true}) → per-node extras
    walk.py       selection → screens, panel, start, closure, nodes
    interactions.py  FigCraft interaction JSON → contract Interaction
    variables.py  variables, reachable values/modes, alternatives
    render.py     per-node paint, CSS effect extraction, temporary edits + undo
    writer.py     folder output, data.js, player assembly
    summary.py    French end-of-export summary
  tests/          unittest; fixtures/ (moved from plugin/tests/fixtures)
  Ouvrir FigCraft.bat   Exporter la sélection.bat   Ouvrir FigCraft.command   Exporter la sélection.command
tools/make_dist.py   builds dist/FigCraft Export HTML/ (launchers, figcraft_export/ with built player)
tools/e2e.py         launch FigCraft, open example, select, export, render references
docs/figcraft-api-notes.md
```

Run all Python tests: `cd exporter && python3 -m unittest discover -s tests -t .` (from `exporter/`).

### Task 0: Toolchain — DONE

Rust installed and user approved write access (now moot: no plugin).

### Task 1: Spike — DONE (gate failed → Revision 2)

Outputs: `tools/fcctl.py`, `docs/figcraft-api-notes.md`, `plugin/tests/fixtures/*.json`, `examples/*.figcraft`, `spike/` (kept as reference until Task 6, then deleted). Easing ids, interaction shapes and the restore mechanics are in the notes.

### Task 2: Player foundations — harness, expressions, easing, fixture

**Files:**
- Create: `player/src/ORDER`, `player/src/ns.js`, `player/src/expr.js`, `player/src/easing.js`, `player/test/harness.js`, `player/test/run.sh`, `player/test/expr.test.js`, `player/test/easing.test.js`, `player/fixtures/demo.data.js`

**Interfaces:**
- Produces: global namespace `FCP` (`var FCP = globalThis.FCP || {}` in `ns.js`); every player file attaches to it, no other globals.
- Produces: `FCP.evalExpr(expr, getVar: (id)=>value) -> value`; `FCP.easing(spec) -> (t:0..1)=>number` for bezier types and `FCP.spring({mass,stiffness,damping}) -> {duration: ms, at: (ms)=>number}`.
- Produces: `player/test/run.sh` — runs every `*.test.js` with `jsc` after loading `harness.js` and the files listed in `player/src/ORDER`; exits non-zero on any failure, prints `N passed, M failed`.

- [ ] **Step 1: Write failing tests** in `expr.test.js`: `add` of numbers = 3; `add` with a string joins (`"a"+1 = "a1"`); `divide` by 0 returns 0 (record FigCraft's actual result from Task 1 notes if it differs); `equals`, `less`, `greaterOrEqual`, `and`/`or`/`not` if present in notes; `alias` reads `getVar`; an unknown op returns `undefined` without throwing. In `easing.test.js`: `linear(0.5)=0.5`; `easeInAndOut` is symmetric (`f(0.25)+f(0.75)≈1`); bezier `[0.42,0,0.58,1]` hits 0 and 1 at the ends; a spring settles (`at(duration)` within 0.001 of 1) and overshoots for damping < critical.
- [ ] **Step 2:** `bash player/test/run.sh` → FAIL (functions undefined).
- [ ] **Step 3:** Implement `ns.js`, `expr.js`, `easing.js`; easing ids and bezier constants from Task 1 notes (FigCraft's 13 easings); spring by numeric integration of `m x'' = -k(x-1) - c x'` at 1 ms steps until |x-1| and |v| < 0.001.
- [ ] **Step 4:** `bash player/test/run.sh` → all pass.
- [ ] **Step 5:** Write `player/fixtures/demo.data.js`: 3 panel screens in 2 sections + 1 overlay screen; a button instance with variants Default/Hover/Pressed (hover + press + changeTo); a navigate with push; a smartAnimate between screens sharing a layer name; a number variable shown in liveText with `setVariable expr count+1`; a colour mode collection Light/Dark with `alts`; a scrolling screen with a fixed header; a backdropBlur layer. Paints are tiny inline SVG files under `player/fixtures/assets/`.
- [ ] **Step 6: Commit** `feat(player): namespace, expressions, easing, demo fixture`.

### Task 3: Player state machine — navigation, overlays, history, variables

**Files:**
- Create: `player/src/state.js`, `player/test/state.test.js`

**Interfaces:**
- Consumes: `FCP.evalExpr`.
- Produces: `FCP.createState(proto) -> State` with `State.screen`, `State.overlays: [{id, sourceNodeId}]`, `State.vars: {[VarId]: value}` (initialised from each collection's default mode), `State.modes: {[CollId]: ModeId}`, `State.variants: {[instanceNodeId]: VariantKey}`, and `State.run(actions, ctx:{nodeId}) -> [Effect]` where `Effect` is `{kind:"screen", from, to, transition, reverse?}`, `{kind:"overlayOpen"|"overlayClose"|"overlaySwap", id, transition}`, `{kind:"variant", node, from, to, transition}`, `{kind:"scroll", target, offset, transition}`, `{kind:"vars"}`, `{kind:"url", url, newTab}`. `State.restart()`. Pure: no DOM.

- [ ] **Step 1: Write failing tests** (names → assertions): `navigate_replaces_screen_and_pushes_history`; `navigate_from_overlay_closes_overlays`; `back_closes_top_overlay_first` then `back_returns_with_reverse_transition` (`reverse:true`, same transition); `back_on_first_screen_is_noop`; `swap_overlay_replaces_top`; `close_overlay_pops`; `restart_clears_history_overlays_and_vars`; `set_variable_expr_count_plus_one` (0 → 1 → 2); `set_variable_mode_changes_modes`; `conditional_runs_first_matching_block_else_last`; `change_to_records_variant`; `navigate_to_missing_screen_is_noop_no_throw` (Review Focus 5).
- [ ] **Step 2:** `bash player/test/run.sh` → the new tests FAIL.
- [ ] **Step 3:** Implement `state.js` (rules: FigCraft `prototyping-parity.md` rows Navigate, Back, overlays, Change to, variables).
- [ ] **Step 4:** Run → all pass. **Step 5: Commit** `feat(player): prototype state machine`.

### Task 4: Player hit-testing and trigger resolution

**Files:**
- Create: `player/src/hit.js`, `player/test/hit.test.js`

**Interfaces:**
- Consumes: `proto.nodes`, `State.variants`.
- Produces: `FCP.interactionsFor(proto, state, nodeId) -> [Interaction]` (instance: interactions of the shown variant's root, overridden per trigger type by the instance's own); `FCP.resolve(proto, state, pathTopDown: [NodeId], triggerType) -> {nodeId, interaction}|null` (top-most layer with that trigger wins, layers without it pass through, hidden layers ignored); `FCP.keyMatches(spec, {key, shift, ctrl, alt, meta}) -> bool` (exact modifier set).

- [ ] **Step 1: Write failing tests:** `topmost_trigger_wins`; `layer_without_trigger_passes_through`; `hidden_layer_ignored`; `instance_plays_shown_variant_interactions`; `instance_own_interaction_overrides_same_trigger`; `key_shift_k_does_not_fire_for_k` and vice versa; `gamepad_key_spec_parsed`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → pass. **Step 5: Commit** `feat(player): hit testing and trigger resolution`.

### Task 5: Player DOM — scene, transitions, Smart Animate, panel, boot

**Files:**
- Create: `player/src/scene.js`, `player/src/smart.js`, `player/src/transitions.js`, `player/src/triggers.js`, `player/src/panel.js`, `player/src/boot.js`, `player/player.css`, `player/index.html`, `player/dev/index.html`, `player/test/smart.test.js`

**Interfaces:**
- Consumes: everything above; contract `data.js`.
- Produces: `FCP.buildScreen(proto, state, screenId) -> HTMLElement` (nested absolute `div`s, `paint` as `<img>` offset by `dx/dy`, `alts` chosen from `state.vars`/`state.modes`, `liveText` as text node, `bindings.visible`, `css.*` mapped to `backdrop-filter`, `filter: blur()`, `mix-blend-mode`, `border-radius`, `clip-path`, `mask-image`; `overflow` → scroll containers; `position: fixed|sticky` kept on top inside the screen viewport).
- Produces: `FCP.matchLayers(fromRootId, toRootId, proto) -> [[fromId, toId]]` (pure: same name and same name-path from the root; FigCraft's rule from notes) and `FCP.animate(effect, els) -> Promise` using the Web Animations API with `FCP.easing`/`FCP.spring` sampled into keyframes.
- Produces: `FCP.boot(proto)` called by `index.html` on `DOMContentLoaded`: stage scaled to fit the window (contain, like the presenter), tall frames scroll; pointer, hover (enter/leave with revert), press (revert on release), drag (directional for move/push/slide, follows pointer then finishes), mouse down/up/enter/leave with `delayMs`, afterDelay (from screen show / overlay open, re-armed each open), keyboard, Gamepad API polling only while a key trigger with `Gamepad` exists; overlay positions incl. `anchor` and `offset`, dimmed background, click-outside close; side panel (collapsible, sections, current screen highlighted, restart button `Redémarrer`) per mockup A.

- [ ] **Step 1: Write failing tests** `smart.test.js`: `matches_by_name_path`; `unmatched_layers_excluded`; `duplicate_names_match_in_order`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement `smart.js`; run → pass.
- [ ] **Step 4:** Implement the DOM files; `player/index.html` loads `player.css`, `data.js`, `player.js` with classic `<script>` tags; `player/dev/index.html` loads `../fixtures/demo.data.js` then each file of `src/ORDER`.
- [ ] **Step 5: Verify in the built-in browser** on `file://…/player/dev/index.html`: every fixture interaction from Task 2 Step 5 behaves as described there (hover/press revert, push, smart animate moves the shared layer, counter increments, Dark mode swaps paints, header stays fixed while scrolling, overlay closes on outside click, Back plays reversed, panel jumps and highlights, Redémarrer resets the counter); console has no errors; a screen name `Écran / 🚀 "test"` renders literally in the panel (Review Focus 3).
- [ ] **Step 6: Commit** `feat(player): DOM scene, transitions, smart animate, triggers, panel`.

### Task 6: Exporter package — control client, launcher, CLI skeleton

**Files:**
- Create: `exporter/figcraft_export/{__init__,__main__,control,launcher}.py`, `exporter/tests/test_control.py`, `exporter/tests/test_launcher.py`, `exporter/tests/test_py38.py`, `exporter/tests/fake_control.py`, the four launchers
- Move: `tools/fcctl.py` → `exporter/figcraft_export/control.py` (adapt), `plugin/tests/fixtures/` → `exporter/tests/fixtures/`; Delete: `spike/`, `plugin/`
- Modify: `docs/figcraft-api-notes.md` (add "Control-only facts")

**Interfaces:**
- Produces: `class Control: __init__(self, port=47917, host="127.0.0.1")`, `request(method, params=None, timeout_ms=60000) -> object` (raises `ControlError(message)` on `ok:false`), `execute(command, params=None) -> object`, `close()`; `class Unreachable(Exception)`.
- Produces: `class FakeControl` (tests) with `replies: dict[(method_or_command, canonical_params_json)] -> object | Exception`, `calls: list`, same `request/execute` API; loads fixtures by name.
- Produces: `launcher.find_figcraft(config: dict, env=os.environ, platform=sys.platform) -> Path | None` (Windows candidates: `%LOCALAPPDATA%\Programs\FigCraft\FigCraft.exe`, `%ProgramFiles%\FigCraft\FigCraft.exe`, `%ProgramFiles(x86)%\FigCraft\FigCraft.exe`; macOS: `/Applications/FigCraft.app/Contents/MacOS/FigCraft`; then `config["figcraft_path"]`), `load_config(dir) / save_config(dir, cfg)` (`config.json` next to the package), `launch(path, port) -> subprocess.Popen`.
- Produces: `python -m figcraft_export launch [--port]` (asks for the exe path once if not found, saves it) and `python -m figcraft_export export [--port] [--out DIR] [--scale 2] [--no-open]` (Tasks 7–10 fill it in); exit codes 0 ok, 1 handled error (French message, no traceback), 2 usage.
- Produces: `figcraft_export.version_ok(version_str) -> bool` (≥ 0.18.1).
- Launchers: `.bat` = `@echo off`, `chcp 65001 >nul`, `cd /d "%~dp0"`, run `py -3 -m figcraft_export <cmd>` falling back to `python -m figcraft_export <cmd>`, then `pause`; if neither exists print `Python 3 est introuvable.`; `.command` = same with `python3`.

- [ ] **Step 1:** Over control on this Mac, find and record in the notes: how to read the **current selection** and **current page** (try `ui.inspect`, `document.inspect`, `select.*`, `page.list`), how to read the **app version**, whether `file.saveAs {data:true}` leaves the document's path/dirty state unchanged, and whether `edit.undo` over control reverts `node.set` / `instance.setProperties` / `variable.setMode` one step each. Use `spike/py/*.py` as reference for calling conventions.
- [ ] **Step 2: Write failing tests:** `unreachable_port_raises_unreachable` (nothing listens on a free port); `error_reply_raises_control_error_with_message`; `request_ids_increment_and_replies_match`; `find_figcraft_windows_localappdata` (fake env + a temp file at the candidate path, `platform="win32"`); `find_figcraft_falls_back_to_config`; `config_roundtrip_utf8_path_with_accents` (`C:\Users\Élodie\FigCraft\FigCraft.exe`); `export_without_figcraft_prints_french_and_exits_1` (Review Focus 1: runs `python -m figcraft_export export --port <free>` in a subprocess, stderr contains `Impossible de joindre FigCraft.`, no `Traceback`); `version_ok` table (`0.18.0` false, `0.18.1` true, `0.19.0-alpha` true, `1.0` true); `all_sources_parse_as_python38` (walks `figcraft_export/*.py` with `ast.parse(src, feature_version=(3, 8))`).
- [ ] **Step 3:** Run `cd exporter && python3 -m unittest discover -s tests -t .` → FAIL. **Step 4:** Implement. **Step 5:** Run → pass.
- [ ] **Step 6: Commit** `feat(exporter): control client, launcher, CLI skeleton, Windows launchers`.

### Task 7: Walk — selection, panel, start, closure, interactions, document extras

**Files:**
- Create: `exporter/figcraft_export/{walk,interactions,docfile}.py`, `exporter/tests/test_walk.py`, `exporter/tests/test_interactions.py`, `exporter/tests/test_docfile.py`; new fixtures recorded over control as needed (selection, `file.saveAs {data:true}`, `node.get` with depth)

**Interfaces:**
- Consumes: `Control`/`FakeControl`, notes.
- Produces: `docfile.extras(saveas_reply) -> dict[str, {"overflow", "position", "varModes"}]` (keys = layer ids as strings; from `document.json`'s `overflow`, `scroll_position`, `var_modes`) and `docfile.digest(saveas_reply) -> str` (sha256 of `document.json` bytes).
- Produces: `walk.walk(ctl, extras) -> Walked`; `Walked = {"proto": dict (contract, paints empty), "jobs": [RenderJob], "warnings": [str], "page_id": str}`; `RenderJob = {"node": str, "fc_id": int, "kind": "own"|"variant"|"mode"|"varValue", "hide_children": bool, "strip_effects": [str], "instance"?: str, "variant"?: str, "collection"?: str, "mode"?: str, "var"?: str, "value"?: any}`.
- Produces: `interactions.convert(raw: dict) -> dict` (contract `Interaction`; maps `onClick→click`, `onHover→hover`, `onPress→press`, `onDrag→drag`, `keyPress→key`, `afterDelay.ms→delayMs`, interaction-level `delay_ms→trigger.delayMs`, `close_on_outside→closeOnClickOutside`, `background {r,g,b,a}→css rgba()`, `duration_ms→durationMs`, easing string/`customBezier`/`customSpring` → contract `easing`; `changeTo.dest` → `variant` key); raises `ValueError` on an unknown kind (walk catches, reports, skips).

- [ ] **Step 1: Write failing tests** with `FakeControl` + fixtures: `empty_selection_errors_in_french` (`Sélectionnez au moins une frame de premier niveau.`); `non_frame_and_nested_skipped_and_reported`; `panel_groups_by_section_in_layer_order`; `start_is_flow_start_when_selected_else_first`; `closure_follows_navigate_overlay_changeto_across_pages_not_listed_in_panel`; `closure_terminates_on_cycles`; `missing_destination_reported_not_fatal` (Review Focus 5); `every_trigger_and_action_kind_converts` (one fixture interaction per kind from notes §2); `custom_bezier_and_spring_convert`; `variant_interactions_read_from_component_node`; `instance_lists_reachable_variants_only`; `text_bound_to_string_or_number_var_becomes_live_text_with_style`; `visible_bound_to_boolean_var_sets_bindings_visible`; `overflow_position_from_docfile_extras`; `container_job_hides_children`; `backdrop_blur_blend_mask_jobs_strip_effects_and_set_css`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (breadth-first `node.get` with a visited set; depth as allowed over control). **Step 4:** Run → pass. **Step 5: Commit** `feat(exporter): document walk and interaction conversion`.

### Task 8: Variables — reachable values and modes

**Files:**
- Create: `exporter/figcraft_export/variables.py`, `exporter/tests/test_variables.py`

**Interfaces:**
- Produces: `variables.read(ctl) -> dict` (contract `variables` from `variable.list`; colour values → css `rgba()`); `reachable(variables, actions: list) -> {"modes": {coll: [mode]}, "values": {var: [value]}, "open": [var]}`; `alternatives(bound_vars: dict, modes_used: list, reach, cap=32) -> (list[When], capped: bool)`; walk adds `mode`/`varValue` jobs from these.

- [ ] **Step 1: Write failing tests:** `defaults_always_reachable`; `set_variable_literal_adds_value`; `set_mode_adds_mode`; `expr_driven_colour_marked_open`; `cartesian_product_capped_at_32_and_flagged`; `colour_values_become_css_rgba`.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(exporter): variable reachability`.

### Task 9: Render — paints with undone temporary edits

**Files:**
- Create: `exporter/figcraft_export/render.py`, `exporter/tests/test_render.py`

**Interfaces:**
- Consumes: `Walked`, `RenderJob`, notes (edit/undo mechanics from Task 6 Step 1).
- Produces: `render.render_all(ctl, walked, scale=2) -> list[Asset]`, `Asset = {"path": "assets/<sanitised id>[__<suffix>].svg|png", "data": bytes}`; fills `paint`, `alts`, `css` in `walked["proto"]["nodes"]`; `class EditSession` context manager: records each successful edit, on exit (normal or exception) undoes them all in reverse (`edit.undo` per edit if the notes confirm it, else inverse `node.set`/`instance.setProperties`/`variable.setMode` with the original values, Auto mode restored as `mode: null`).

Decisions: SVG for vectors/shapes/text; PNG at `scale` for image fills, noise, layer blur; containers rendered with children hidden; CSS-handled effects stripped before render; `Paint.dx/dy/w/h` from the exported image size vs node box (`absoluteBounds`); identical bytes share one asset.

- [ ] **Step 1: Write failing tests:** `container_paint_excludes_children` (FakeControl records hide-before/undo-after around `file.export`); `edits_undone_after_error` (export raises mid-way → every edit undone in reverse, exception re-raised); `asset_name_uses_sanitised_id_not_layer_name`; `duplicate_bytes_share_one_asset`; `mode_alt_renders_with_mode_then_restores`; `variant_render_switches_then_restores`; `paint_offsets_account_for_shadow_bounds`.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(exporter): layer rendering with undone temporary edits`.

### Task 10: Writer, summary, export command, distribution

**Files:**
- Create: `exporter/figcraft_export/{writer,summary}.py`, `exporter/tests/test_writer.py`, `exporter/tests/test_export.py`, `tools/make_dist.py`; Modify: `exporter/figcraft_export/__main__.py`, `.gitignore` (`dist/`)

**Interfaces:**
- Produces: `writer.to_data_js(proto) -> str` (`window.FIGCRAFT_PROTOTYPE = <json>;\n`, `ensure_ascii=False`, `</` escaped as `<\/`); `writer.player_js(player_root: Path) -> str` (prebuilt `player.js` if present, else concatenation of `src/` in `ORDER`); `writer.write(out_dir: Path, proto, assets, player_root) -> Path` (writes into `out_dir/<slug>/`; refuses a non-empty existing target unless it holds a previous export (has `data.js`), which it replaces); `summary.text(proto, assets, warnings, digest_ok) -> str` in French (`N écrans exportés (X Mo) dans « path ».`, approximated / skipped lists: first 5 then `… et K autres`, the digest warning `Attention : le document FigCraft a peut-être été modifié…` when `digest_ok` is false).
- Produces: `export` command flow: connect (Review Focus 1) → version → digest before → walk → variables → render (inside EditSession) → digest after → choose folder (`--out`, else `tkinter.filedialog.askdirectory`, else `input()`) → write → summary → `webbrowser.open(index.html.as_uri())` unless `--no-open`. On error after writing started, remove the partial `<slug>/` folder (Review Focus 4).
- Produces: `python3 tools/make_dist.py` → `dist/FigCraft Export HTML/` with the four launchers, `figcraft_export/` (no tests), `figcraft_export/player/{index.html,player.js,player.css}` prebuilt, and `LISEZMOI.txt` (French: install Python, double-click order, troubleshooting).

- [ ] **Step 1: Write failing tests:** `data_js_escapes_script_close`; `data_js_keeps_unicode_names` (`Écran / 🚀 "test"`, read back with utf-8); `layout_has_index_player_css_data_assets`; `write_into_path_with_spaces_and_accents` (temp dir `Mes prototypes/Élodie`); `refuses_non_empty_foreign_folder`; `replaces_previous_export`; `partial_folder_removed_on_error`; `summary_in_french_with_truncation`; `slug_from_title_safe` (`"Mon proto / v2"` → `mon-proto-v2`, empty → `prototype`); `export_end_to_end_with_fake_control` (FakeControl fixtures → folder with N screens, exit 0); `make_dist_contains_launchers_and_built_player`.
- [ ] **Step 2–4:** fail → implement → pass (full suite).
- [ ] **Step 5: Commit** `feat(exporter): folder writer, French summary, export command, dist`.

### Task 11: End-to-end on the FigCraft examples + Windows checklist

**Files:**
- Create: `tools/e2e.py`, `README.md` (French), `docs/windows-checklist.md` (French)

**Interfaces:**
- Consumes: the package, `examples/*.figcraft`, the app at `/Applications/FigCraft.app`.
- Produces: `python3 tools/e2e.py examples/<file>.figcraft --frames "<name>,<name>" --out out/<name>/` → launches FigCraft with control, opens the file, selects the frames (`select.set`), runs `python -m figcraft_export export --out … --no-open`, renders each selected frame with `file.export png` to `out/<name>/_reference/<frame>.png`, checks the before/after digest is equal, quits FigCraft.

- [ ] **Step 1:** Run e2e on `ridgeline-onboarding` (all onboarding frames) and on `ridgeline-design-system` (a frame using the Button variants). Expected: exit 0, `index.html` exists, digest unchanged.
- [ ] **Step 2 (controller): Verify in the built-in browser** (`file://`): each screen beside its `_reference` PNG shows no visible difference except listed CSS approximations; click through the onboarding flow incl. Back; hover/press the Button variants; console clean.
- [ ] **Step 3:** `python3 tools/make_dist.py`; from `dist/FigCraft Export HTML/`, double-click `Ouvrir FigCraft.command`, open an example, select frames, double-click `Exporter la sélection.command`, pick a folder. Expected: summary in French, browser opens the prototype.
- [ ] **Step 4:** Write `docs/windows-checklist.md`: the exact steps and expected results for the user on the Windows machine (Python check `py -3 --version`, copy the dist folder, first launch asks for `FigCraft.exe` if not found, export to a path with spaces/accents, open in Edge and Chrome, accents in console).
- [ ] **Step 5: Commit** `test: end-to-end export of FigCraft examples; README; Windows checklist`.
