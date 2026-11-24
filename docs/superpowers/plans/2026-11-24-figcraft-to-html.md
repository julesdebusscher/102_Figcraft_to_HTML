# FigCraft → HTML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A FigCraft plugin that exports the selected frames as a `.zip` holding a standalone, file://-openable HTML/JS/CSS clickable prototype that replays every FigCraft prototype interaction, with a side panel to jump between frames.

**Architecture:** Two halves joined by one data contract. (1) A Rust → wasm32 plugin walks the selection through FigCraft commands, renders every layer's own paint with FigCraft's exporter, writes `data.js` (the contract below) and zips it with an embedded player. (2) A dependency-free JS player (classic scripts, concatenated into `player.js` at Rust build time) rebuilds the layer tree as absolutely positioned DOM and runs triggers, actions, variables, transitions and Smart Animate.

**Tech Stack:** Rust 2024 + `figcraft-plugin-sdk` (git, `storytold/figcraft`, `plugins/sdk`), target `wasm32-unknown-unknown`; vanilla ES2020 JS + CSS (no modules, no fetch); JS logic tests run with macOS's built-in `jsc`; end-to-end driven from Python 3 (stdlib only) over FigCraft's `--control` loopback channel against `/Applications/FigCraft.app` 0.18.1.

**Spec:** `docs/superpowers/specs/2026-11-24-figcraft-to-html-design.md`

## Global Constraints

- Plugin manifest `api: 4`, `permissions.saveFile: true`; one `save_file` per run, ≤ 16 MB; no file/network/clock/random in wasm.
- Per run: 1 000 000 000 fuel, 64 MB memory, 100 000 host calls, 16 MB per string.
- Export must open by double-click (`file://`) in Chrome, Safari and Firefox: no `type="module"`, no `fetch`, no XHR; data ships as `data.js` setting `window.FIGCRAFT_PROTOTYPE`.
- Output folder layout: `index.html`, `player.js`, `player.css`, `data.js`, `assets/`.
- Export scope = current page's selected top-level frames; panel lists only those, grouped by section; transitive closure follows every link (navigate, overlays, change to) at any depth on any page, unselected targets exported but not listed.
- Start screen = page flow starting point if selected, else first selected frame in layer order; "redémarrer" returns there and clears history.
- > 16 MB → run fails with total size and the heaviest contributors; never silently drop a link.
- Variables: visibility, string and number text live; bound colours and mode switches pre-rendered for reachable values (cap 32 alternatives per layer, beyond → reported as approximated).
- Backdrop blur, glass, blend modes, masks, non-rectangular clips → CSS approximation, listed in the end-of-export `notify`.
- Behaviour reference: FigCraft `docs/prototyping-parity.md` (the presenter's behaviour wins on any doubt).
- User-facing text (menu labels, notify messages, panel) in French.
- Nothing to install beyond Rust (`rustup`, target `wasm32-unknown-unknown`); Node is not required.

**Deviation from the spec, to confirm with the user in Task 0:** the spec says `permissions.access: "read"`. Rendering a container without its children, a layer without a CSS-handled effect, other variants of an instance and other variable modes all need temporary edits restored before the run ends, so the plan uses `access: "write"` with every edit undone in the same run (verified by the spike, Task 1).

## Review Focus

1. **Bad selection** (nothing selected, a non-frame layer, a frame nested in another) → French error `Sélectionnez au moins une frame de premier niveau.` for nothing usable; nested or non-frame layers skipped and named in the notify. Test in Task 7.
2. **Awkward names** (duplicate frame names, `/`, emoji, empty name) → panel shows them as typed, escaped; asset files are named by layer id only. Tests in Tasks 6 and 9.
3. **Oversized export** → run fails before `save_file` with `L'archive ferait N Mo (limite 16 Mo). Le plus lourd : …` listing the 5 largest assets. Test in Task 10.
4. **Opened from `file://` in Safari/Firefox** → loads with no console error. Check in Task 11.
5. **Broken links** (destination deleted, hidden, or a component set missing a variant) → hotspot does nothing, export still succeeds, link named in notify; player never throws. Tests in Tasks 4 and 7.

---

## Shared contract: `data.js`

Both halves code against this. The Rust structs (Task 6) serialize to it; the player reads it; `player/fixtures/demo.data.js` (Task 2) is its reference instance. Ids are strings (FigCraft layer ids stringified; instance-variant clones are `"<instanceId>~<variantId>~<childId>"`).

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

`position` values for overlays are FigCraft's (`center`, `topLeft`, …, `manual`). Easing `type` names are FigCraft's 13 (record the exact ids in Task 1).

## File Structure

```
plugin/                         Rust crate `figcraft-to-html` (cdylib)
  Cargo.toml  figcraft-plugin.json  build.rs (concatenates player sources → OUT_DIR/player.js)
  src/lib.rs        entry point: picks command, calls export::run
  src/host.rs       trait Host (the only place touching the SDK) + FakeHost for tests
  src/model.rs      serde structs = the contract
  src/walk.rs       selection → screens, panel, start, closure, nodes
  src/interactions.rs  FigCraft interaction JSON → contract Interaction
  src/vars.rs       variables, reachable values/modes
  src/render.rs     per-node paint, CSS effect extraction, temporary edits + restore, alts
  src/zip.rs        stored zip + crc32
  src/export.rs     orchestration, size check, report → notify, save_file
  tests/fixtures/   node.get / export replies recorded in Task 1
player/
  src/ORDER         file order for concatenation
  src/*.js          one concern each (see Tasks 2–5)
  player.css  index.html
  test/harness.js  test/run.sh  test/*.test.js     (jsc)
  fixtures/demo.data.js  dev/index.html            (open in a browser, loads src/*.js one by one)
tools/fcctl.py      control-channel client
tools/e2e.py        launch FigCraft, open example, select, run plugin, unzip
docs/figcraft-api-notes.md   spike findings (Task 1)
spike/              throwaway, deleted at the end of Task 1
```

---

### Task 0: Toolchain (with the user)

**Files:** none.

- [ ] **Step 1:** Tell the user the plan switches the plugin to `access: "write"` with every edit restored in the same run (see Global Constraints) and get a yes; tell them Rust must be installed. Install only on their yes: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y` then `~/.cargo/bin/rustup target add wasm32-unknown-unknown`.
- [ ] **Step 2:** Verify: `~/.cargo/bin/cargo --version` prints a version; `~/.cargo/bin/rustup target list --installed` lists `wasm32-unknown-unknown`.

### Task 1: Spike — verify the FigCraft plugin API (throwaway, gate)

**Files:**
- Create: `tools/fcctl.py` (kept), `spike/` (deleted at the end), `docs/figcraft-api-notes.md` (kept), `plugin/tests/fixtures/*.json` (kept), `examples/ridgeline-onboarding.figcraft`, `examples/ridgeline-design-system.figcraft` (downloaded from `https://raw.githubusercontent.com/storytold/figcraft/main/examples/`).

**Interfaces:**
- Produces: `tools/fcctl.py` — `class Fc(port=7979)` with `request(method, params, timeout_ms=60000) -> result` (raises on `ok:false`), `execute(command, params) -> result` (wraps `engine.execute`), `launch(file) -> Fc` (starts `/Applications/FigCraft.app/Contents/MacOS/FigCraft --control <port> <file>`, waits until a request succeeds).
- Produces: `docs/figcraft-api-notes.md` answering each question below with the exact command id, params and a trimmed sample reply.

- [ ] **Step 1:** Write `tools/fcctl.py` (newline-delimited JSON over `127.0.0.1:<port>`, see FigCraft `docs/control-protocol.md`); smoke test: `python3 tools/fcctl.py smoke examples/ridgeline-onboarding.figcraft` prints the page names from `document.inspect {depth:1, outline:true}`.
- [ ] **Step 2:** Build a minimal plugin in `spike/` (SDK, `api: 4`, `access: "write"`, `saveFile: true`) whose single command logs to `set_output` the JSON of whatever probe the params name; import it with `plugin.import {path}` and call it with `plugin.run`.
- [ ] **Step 3:** Answer, from inside the plugin (not via control), and record in the notes:
  1. Which command returns rendered bytes for a layer id (try `export`, `node.export`, `export.render`; scan the command list `engine.execute` may expose) and in what encoding (SVG text, base64 PNG).
  2. `node.get` (engine, one level) fields for: interactions (exact trigger/action/transition/easing ids), `boundVariables`, `clip`, overflow/scroll, fixed/sticky, `variableModes`, instance → component set/variant, `effects`, `blend`, mask layers.
  3. Rendering a container **without children**: `contentsOnly`? If not, hiding children with `node.set {visible:false}` then restoring.
  4. Switching an instance's variant and a frame's variable mode temporarily, rendering, restoring; does the document end byte-identical (`document.inspect` before/after) and does `save_file` still work after such edits in the same run?
  5. Variables & collections listing command; page flow starting point (`proto.settings {}` / flows).
  6. Does `save_file` from a `plugin.run` sent over control open a Save dialog (blocking e2e)? Can `set_output` carry a base64 zip (≤ 12 MB) instead?
  7. Fuel and host-call counts for exporting all of `ridgeline-onboarding` (`plugin.run` returns `fuel`, `calls`).
- [ ] **Step 4:** Save raw replies for one frame tree of each example as `plugin/tests/fixtures/{node_get_*,export_*,variables,proto_settings}.json`.
- [ ] **Step 5: Gate.** If (1) or (3) or (4) fails, stop and bring the user the fallback (whole-frame renders, Smart Animate precision lost). Otherwise delete `spike/`, commit `tools/ docs/figcraft-api-notes.md plugin/tests/fixtures examples/` with `chore: spike findings on the FigCraft plugin API`.

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
- [ ] **Step 5: Verify in the built-in browser** on `file://…/player/dev/index.html`: every fixture interaction from Task 2 Step 5 behaves as described there (hover/press revert, push, smart animate moves the shared layer, counter increments, Dark mode swaps paints, header stays fixed while scrolling, overlay closes on outside click, Back plays reversed, panel jumps and highlights, Redémarrer resets the counter); console has no errors; a screen name `Écran / 🚀 "test"` renders literally in the panel (Review Focus 2).
- [ ] **Step 6: Commit** `feat(player): DOM scene, transitions, smart animate, triggers, panel`.

### Task 6: Plugin crate — host seam, contract structs, build embedding

**Files:**
- Create: `plugin/Cargo.toml`, `plugin/figcraft-plugin.json`, `plugin/build.rs`, `plugin/src/lib.rs`, `plugin/src/host.rs`, `plugin/src/model.rs`, `.gitignore` entry `plugin/target/`

**Interfaces:**
- Produces: `trait Host { fn call(&mut self, cmd: &str, params: &Value) -> Result<Value, String>; fn selection(&mut self) -> Vec<u64>; fn notify(&mut self, msg: &str); fn save_file(&mut self, name: &str, mime: &str, bytes: &[u8]) -> Result<(), String>; }`; `SdkHost` (wasm only) and `FakeHost { replies: HashMap<(String, String), Value>, calls: Vec<(String, Value)>, saved: Option<(String, Vec<u8>)>, notes: Vec<String> }` keyed by `(cmd, canonical params JSON)`, loading Task 1 fixtures.
- Produces: `model.rs` structs mirroring the contract (`Proto`, `Screen`, `PanelSection`, `Node`, `Paint`, `Alt`, `When`, `Css`, `LiveText`, `Instance`, `Interaction`, `Trigger`, `Action` as `#[serde(tag="type")]` enum, `Transition`, `Easing`, `Variables`, `Report`), `#[serde(rename_all="camelCase")]`, optional fields skipped when `None`; `fn to_data_js(&Proto) -> String` → `window.FIGCRAFT_PROTOTYPE = <json>;\n` with `</` escaped as `<\/`.
- Produces: `build.rs` concatenates `../player/src/` files in `ORDER` into `$OUT_DIR/player.js`; `lib.rs` exposes `PLAYER_JS`, `PLAYER_CSS`, `INDEX_HTML` via `include_str!`.
- Manifest: id `fr.julos.figcraft-to-html`, name `Export HTML`, `api: 4`, `permissions: {access: "write", saveFile: true}`, commands `[{id:"export", label:"Exporter en site HTML…", params:[{name:"title", label:"Titre du site", type:"text", default:""}, {name:"pngScale", label:"Échelle des images", type:"select", options:["1","2","3"], default:"2"}]}, {id:"exportRaw", label:"Exporter en site HTML (test)"}]` (`exportRaw` returns the zip as base64 via `set_output`, for e2e).

- [ ] **Step 1: Write failing tests** (`cargo test` in `plugin/`): `data_js_escapes_script_close` (a node name `</script>` stays inside the string); `optional_fields_omitted`; `action_serializes_with_type_tag` (`{"type":"navigate","dest":"12",…}`); `player_js_embedded_in_order` (contains `var FCP` before `FCP.boot`).
- [ ] **Step 2:** `cd plugin && cargo test` → FAIL. **Step 3:** Implement. **Step 4:** `cargo test` → pass; `cargo build --release --target wasm32-unknown-unknown` succeeds.
- [ ] **Step 5: Commit** `feat(plugin): crate, host seam, data contract`.

### Task 7: Plugin walk — selection, panel, start, closure, interactions

**Files:**
- Create: `plugin/src/walk.rs`, `plugin/src/interactions.rs`, `plugin/tests/walk.rs`

**Interfaces:**
- Consumes: `Host`, model structs, Task 1 notes for exact field names.
- Produces: `fn walk(host: &mut dyn Host, selection: &[u64]) -> Result<Walked, String>`; `struct Walked { proto: Proto /* paints empty */, render_jobs: Vec<RenderJob>, warnings: Vec<String> }`; `struct RenderJob { node: String, figcraft_id: u64, kind: JobKind /* Own | OwnWithoutEffects(Vec<String>) | Variant{instance, variant} | Mode{collection, mode} | VarValue{var, value} */ }`; `fn convert_interaction(raw: &Value) -> Result<Interaction, String>`.

- [ ] **Step 1: Write failing tests** with `FakeHost` + fixtures: `empty_selection_errors_in_french` (`Sélectionnez au moins une frame de premier niveau.`); `non_frame_and_nested_skipped_and_reported`; `panel_groups_by_section_in_layer_order`; `start_is_flow_start_when_selected_else_first`; `closure_follows_navigate_overlay_changeto_across_pages_not_listed_in_panel`; `closure_terminates_on_cycles`; `missing_destination_reported_not_fatal` (Review Focus 5); `every_trigger_and_action_kind_converts` (one fixture interaction per kind from notes); `instance_lists_reachable_variants_only`; `text_bound_to_string_or_number_var_becomes_live_text_with_style`; `visible_bound_to_boolean_var_sets_bindings_visible`; `overflow_fixed_sticky_and_clip_copied`.
- [ ] **Step 2:** `cargo test` → FAIL. **Step 3:** Implement (engine `node.get` returns one level: breadth-first with a visited set). **Step 4:** pass. **Step 5: Commit** `feat(plugin): document walk and interaction conversion`.

### Task 8: Plugin variables — reachable values and modes

**Files:**
- Create: `plugin/src/vars.rs`, `plugin/tests/vars.rs`

**Interfaces:**
- Produces: `fn variables(host) -> Result<Variables, String>`; `fn reachable(vars: &Variables, actions: &[&Action]) -> Reach`; `struct Reach { modes: HashMap<CollId, Vec<ModeId>>, values: HashMap<VarId, Vec<Value>>, open: Vec<VarId> /* expr-driven, not enumerable */ }`; `fn alternatives(node_bindings, reach, cap: usize /*32*/) -> (Vec<When>, bool /*capped*/)`.

- [ ] **Step 1: Write failing tests:** `defaults_always_reachable`; `set_variable_literal_adds_value`; `set_mode_adds_mode`; `expr_driven_colour_marked_open`; `cartesian_product_capped_at_32_and_flagged`.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(plugin): variable reachability`.

### Task 9: Plugin render — paints, CSS effects, temporary edits

**Files:**
- Create: `plugin/src/render.rs`, `plugin/tests/render.rs`

**Interfaces:**
- Consumes: `RenderJob`, Task 1 notes (export command, hide/restore mechanics).
- Produces: `fn render_all(host, walked: &mut Walked, png_scale: u8) -> Result<Vec<Asset>, String>`; `struct Asset { path: String /* "assets/<nodeId>[__<suffix>].svg|png" , ids sanitised to [A-Za-z0-9_~-] */, bytes: Vec<u8> }`; fills `Node.paint`/`alts`/`css`; returns every temporary edit to its original value before returning, on success **and** on error (a guard that restores in reverse order).

Decisions: SVG for vectors/shapes/text (outlined); PNG at `png_scale` for image fills, noise, layer blur and anything the notes show the SVG exporter approximates; containers rendered with children hidden; backdrop blur/glass/blend/mask/non-rect clip removed before render and emitted in `css` + `report.approximated`; identical bytes deduplicated (same path reused).

- [ ] **Step 1: Write failing tests:** `container_paint_excludes_children` (FakeHost records hide-before/restore-after around the export call); `edits_restored_after_error` (export fails mid-way → every `node.set` undone, in reverse order); `backdrop_blur_moves_to_css_and_reported`; `asset_name_uses_sanitised_id_not_layer_name` (Review Focus 2); `duplicate_bytes_share_one_asset`; `mode_alt_renders_with_mode_then_restores`.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(plugin): layer rendering with restored temporary edits`.

### Task 10: Plugin export — zip, size check, report, save

**Files:**
- Create: `plugin/src/zip.rs`, `plugin/src/export.rs`, `plugin/tests/export.rs`; Modify: `plugin/src/lib.rs` (dispatch `export` / `exportRaw`)

**Interfaces:**
- Produces: `fn zip_store(files: &[(String, &[u8])]) -> Vec<u8>` (stored, CRC-32, DOS date 1980-01-01, folder prefix `<slug>/`); `fn run(host, params) -> Result<Value, String>`: walk → vars → render → `data.js` + player files → zip → size check (16 × 1024 × 1024) → `save_file("<slug>.zip", "application/zip", …)` or base64 output for `exportRaw` → `notify` summary in French: `N écrans exportés (X Mo).` plus approximated / skipped lists (first 5, then `… et K autres`).

- [ ] **Step 1: Write failing tests:** `zip_roundtrips_with_system_unzip` (write to a temp file, `unzip -t` exits 0); `layout_has_index_player_css_data_assets`; `oversize_fails_before_save_with_top5` (Review Focus 3: message starts `L'archive ferait` and `saved` is `None`); `notify_summarises_in_french`; `slug_from_title_safe` (`"Mon proto / v2"` → `mon-proto-v2`).
- [ ] **Step 2–4:** fail → implement → pass; `cargo build --release --target wasm32-unknown-unknown` succeeds.
- [ ] **Step 5: Commit** `feat(plugin): archive, size guard, report, save`.

### Task 11: End-to-end on the FigCraft examples

**Files:**
- Create: `tools/e2e.py`, `README.md` (French: build, import via Plugins ▸ Development ▸ Import plugin from manifest…, use, limits)

**Interfaces:**
- Consumes: `tools/fcctl.py`, `plugin/figcraft-plugin.json` + built wasm.
- Produces: `python3 tools/e2e.py examples/<file>.figcraft --frames "<name>,<name>" --out out/<name>/` → launches FigCraft with control, imports the plugin, selects frames, runs `exportRaw`, unzips into `out/`, renders each selected frame with `ui.render` to `out/<name>/_reference/<frame>.png` for comparison.

- [ ] **Step 1:** Run e2e on `ridgeline-onboarding` (all onboarding frames) and on `ridgeline-design-system` (a frame using the Button variants). Expected: exit 0, `out/*/index.html` exists.
- [ ] **Step 2: Verify in the built-in browser** (`file://`): each screen side by side with its `_reference` PNG shows no visible difference except listed CSS approximations; every interaction from the FigCraft presenter on these files behaves the same (click through the onboarding flow incl. Back; hover/press the Button variants); console clean. Repeat the opening check in Safari and Firefox if installed, else say so (Review Focus 4).
- [ ] **Step 3:** In the real app: import the manifest, select frames, Plugins ▸ Export HTML ▸ Exporter en site HTML…, save, unzip, double-click `index.html`. Expected: same result; the notify toast is in French.
- [ ] **Step 4: Commit** `test: end-to-end export of FigCraft examples; README`.
