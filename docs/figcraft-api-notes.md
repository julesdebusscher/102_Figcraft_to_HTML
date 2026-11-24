# FigCraft plugin API — spike notes

Measured on **FigCraft 0.18.1** (`/Applications/FigCraft.app`), plugin `api: 4`, `access: "write"`,
`saveFile: true`, SDK `figcraft-plugin-sdk` from storytold/figcraft @ `c01d391` (2026-11-23).
Every probe below ran **inside a plugin** through the `call` import (control was only used to
import/run the plugin, switch documents, build test scaffolding and inspect the document).

Raw replies: `exporter/tests/fixtures/` (see the list at the end).

## Gate summary

| # | Question | Result |
|---|---|---|
| 1 | Rendered bytes for a layer from a plugin | **FAIL** — no command available to plugins returns rendered bytes |
| 2 | `node.get` fields | Mostly there; **overflow, fixed/sticky and `variableModes` are not readable** |
| 3 | Render a container without its children | **FAIL inside a plugin** (follows from 1). Hide/restore children works and restores exactly; over control the render of a hidden-children frame is correct |
| 4 | Temp variant/mode switch, restore, byte-identical, save_file after | **PASS** (document.json byte-identical; save_file accepted) |
| 5 | Variables listing, flows | `variable.list {}`; flows on the page node (`node.get {id: <page>}` → `flows`); `proto.settings {}` |
| 6 | save_file from `plugin.run` over control | Returns at once, no dialog seen; set_output carries 12 MB fine, 16 MB crashes |
| 7 | Fuel / calls, whole onboarding file | 142 `node.get` → 429 calls, ~74 M fuel (7 % of the 1 G budget) |

## 1. Rendering a layer (FAIL)

Tried from the plugin (`plugin.run`, every call made with `call`):

| Command | Params | Reply |
|---|---|---|
| `export` | `{ids:[21], format:"svg"}` | `unknown command \`export\`` (the MCP `export` tool is not an engine command) |
| `node.export` | same | `unknown command \`node.export\`` |
| `export.render` | `{ids:[21]}` | `unknown command \`export.render\`` |
| `file.export` | `{ids:[21], format:"svg"}` / `{…, format:"png", scale:2}` | ``\`file.export\` isn't available to plugins`` |
| `file.exportSvg` | `{ids:[21]}` | ``\`file.exportSvg\` isn't available to plugins`` |
| `file.exportLayers` | `{ids:[21]}` | ``\`file.exportLayers\` isn't available to plugins`` |
| `engine.commands` | `{}` | `unknown command \`engine.commands\`` (control method, not a command) |
| `component.playground` | `{id:211, path:"/tmp/x.png"}` | `plugins can't write files: leave out \`path\` to get the result back` — without `path` it returns `{code, width, height, properties…}`, **no image** |
| `object.rasterize` | `{ids:[175]}` | `{ids:[364]}` — makes an image layer, but `node.get` only gives the image **hash** (`fills[0].image: "98d0e5…"`); no command reads image bytes |
| `dev.compare` | `{id:2}` | needs a ready-for-dev frame; returns a change list, no pixels |

I scanned all 645 ids from `engine.commands` (over control) for svg/png/base64/render/raster/
thumbnail/clipboard. Every command that returns image bytes is `file.*` (`file.export`,
`file.exportSvg`, `file.exportLayers`, `file.exportFramesPdf`, `file.saveAs {data:true}`), and
the plugin sandbox refuses all `file.*` calls. `ui.render` / `ui.screenshot` are control methods,
not commands.

What a plugin can get instead: `inspect.code {id, language: html|css|react|tailwind|…}` →
`{code, language, connected}` (HTML+CSS of the whole tree, bound variables as CSS custom
properties, `mix-blend-mode`, `box-shadow`; **no** images or vector paths, no overflow/sticky).

Over the **control channel** the same command works and is the render path if needed:

```json
{"method":"engine.execute","params":{"command":"file.export","params":{"ids":[2],"format":"svg"}}}
→ {"format":"svg","data":"PHN2ZyB3aWR0aD0iMzkwIiBoZWlnaHQ9Ijg0NCIg…"}      (base64 SVG text)
{"method":"engine.execute","params":{"command":"file.export","params":{"ids":[2],"format":"png","scale":1}}}
→ {"format":"png","data":"iVBORw0KGgoAAAANSUhEUgAA…"}                       (base64 PNG)
```

Encoding: always `{format, data}` with `data` base64 (SVG too). Fixtures:
`export_onboarding_welcome_{svg,png}.json`, `export_design_system_probe_svg.json`.

## 2. `node.get` (engine command, one level of children)

Call: `call("node.get", {"id": N})` → the layer plus one level of `children` (each child is a full
node object without its own children; `childCount` past the depth). Output is **sparse**: a key
appears only when it differs from the default. `fields: [...]` filters; an unknown field errors
with the valid-key list. Valid keys in 0.18.1:

`absolute, absoluteBounds, annotations, arc, background, blend, board, booleanOperation,
boundVariables, brush, characters, childCount, children, clip, codeLinks, componentProperties,
componentPropertyDefinitions, constraints, cornerRadius, cornerSmoothing, dashes, description,
devChanged, devNote, devResources, devStatus, effects, exports, fills, flows, fontFamily, fontSize,
fontStyle, fontVariations, gridCell, grids, hangingList, hangingPunctuation, height, id,
innerRadius, interactions, isMask, layout, leadingTrim, letterSpacing, lineDirections, lineHeight,
lineIndentations, lineTypes, listSpacing, listStartOffsets, listStyle, locked, mainComponent,
mainComponentName, maskType, maxHeight, maxLines, maxWidth, measurements, minHeight, minWidth,
miterAngle, name, opacity, operandOperation, overrides, pluginData, pointCount, rotation,
sectionContentsHidden, segments, sizing, slot, strokeAlign, strokeJoin, strokeSides, strokeWeight,
strokes, styledRuns, styles, textAlign, textAutoResize, textDecoration, textDecorationColor,
textDecorationOffset, textDecorationSkipInk, textDecorationStyle, textDecorationThickness,
textDirection, textPath, textStyleRanges, type, vertices, visible, width, widthProfile, wrapStyle, x, y`

Types seen: `PAGE, FRAME, GROUP, TEXT, VECTOR, RECTANGLE, ELLIPSE, COMPONENT, COMPONENT_SET,
INSTANCE, SLICE`.

### Interactions (`interactions`, array on the layer)

Shape (note **snake_case** `duration_ms`, `delay_ms`, `close_on_outside` in the reply, while the
setters take `durationMs`/`delayMs`):

```json
{"trigger": {"type": "onClick"},
 "actions": [{"type": "navigate", "dest": 24}],
 "transition": {"type": "push", "direction": "left"},
 "duration_ms": 400, "easing": "easeOut"}
```

Seen in replies:

- trigger: `{type:"onClick"}`, `{type:"onHover"}`, `{type:"mouseEnter"}` (+ `delay_ms` on the
  interaction), `{type:"afterDelay", ms:800}`, `{type:"keyPress", key:"Shift+K"}`. The setter also
  takes `onPress, onDrag, mouseLeave, mouseDown, mouseUp`.
- actions: `{type:"navigate", dest}`, `{type:"back"}`, `{type:"changeTo", dest:<variant id>}`,
  `{type:"openOverlay", dest, position:"center", background:{r,g,b,a}, close_on_outside:true}`,
  `{type:"scrollTo", dest, offset:[0,44]}`, `{type:"openUrl", url}`,
  `{type:"setVariableMode", collection:"VariableCollectionId:1", mode:"VariableCollectionId:1/mode2"}`.
  Setter also: `swapOverlay, closeOverlay, setVariable, conditional`.
- transition: `{type:"instant"}`, `{type:"push", direction:"left"}`,
  `{type:"moveIn", direction:"bottom"}`, `{type:"smartAnimate"}`. Setter also: `dissolve, moveOut,
  slideIn, slideOut`; directions `left|right|top|bottom`.
- easing: string `easeOut`, `bouncy` (presets `linear|easeIn|easeOut|easeInOut|easeInBack|
  easeOutBack|easeInOutBack|gentle|quick|bouncy|slow`), or
  `{"customBezier":{"x1":0.2,"y1":0,"x2":0,"y2":1}}`, `{"customSpring":{"mass":1,"stiffness":300,"damping":20}}`.
  Defaults written when not given: `duration_ms: 300`, `easing: "easeOut"`, `transition: instant`.
- Interactions on a **variant** (component 219, `changeTo` 217) are on the COMPONENT node; an
  instance only lists interactions of its own.

### Other fields

| Need | Field / way | Sample |
|---|---|---|
| boundVariables | `boundVariables` | `{"fill":"VariableID:1","gap":"VariableID:2"}` (field → variable id) |
| clip | `clip` | `true` / `false` (frames) |
| overflow / scroll | **not readable.** Settable: `node.set {props:{overflow: none\|horizontal\|vertical\|both}}` | nothing in node.get, document.inspect, inspect.code/properties |
| fixed / sticky | **not readable.** Settable (undocumented): `node.set {props:{scrollPosition: scrolls\|fixed\|sticky}}` | stored in the file as `scroll_position` |
| variableModes | **not readable** in 0.18.1 (`fields:["variableModes"]` → unknown field; not in output even when set). Workaround: `proto.evaluate {expression:"mode(Theme)", id:<layer>}` → `{value:{type:"string",value:"Dark"}}` gives the *effective* mode at a layer (not whether it is explicit or Auto) | |
| instance → component / set / variant | `mainComponent` (variant id), `mainComponentName` (`"Style=Primary, State=Default"`); `component.properties {id:<instance>}` → `{component, set, properties:[{name,type:"variant",options,default,value}]}` | `component_properties.json` |
| overrides | `overrides` | `["opacity"]`, `["characters"]` |
| effects | `effects` | `[{"type":"dropShadow","color":{r,g,b,a},"offset":[0,2],"radius":4,"spread":0,"blend":"normal","showBehind":false,"visible":true}]` |
| blend | `blend` | `"multiply"` (only when not normal); `opacity` 0..1 |
| masks | the mask group is `type:"GROUP"` named "Mask group"; the mask layer has `isMask:true, maskType:"alpha"` and comes first | |
| flows | on the page node: `flows: [{name, start, description}]` | `{"name":"Onboarding","start":2,"description":""}` |

Note: the file format on disk (`document.json`) does hold `overflow`, `scroll_position` and
`var_modes`; `file.saveAs {data:true}` over control returns it (refused to plugins as `file.*`).

## 3. Container without children (FAIL in plugin)

- No plugin render (see 1), so nothing to pass `contentsOnly` to. `contentsOnly` (control-side
  `file.export`, default `true`) only decides whether *other* layers in the area are drawn; it
  does not drop children.
- Hiding children from the plugin works: `node.set {ids:[k], props:{visible:false}}` for each
  child, then `{visible:true}`: part of the Q4 run, document byte-identical afterwards.
- Over control, `file.export {ids:[364], format:"svg"}` with its 5 children hidden → 279-byte SVG
  holding only the frame background (7077 bytes with children). So the "hide, render, restore"
  trick works, but only where rendering exists (control).

## 4. Temporary variant / mode switch (PASS)

One `plugin.run` on the design-system file (with spike scaffolding: instance 367 of Button with
a text override "Go now" and an opacity override, instance 377 of Difficulty, frame 364 with an
explicit Theme mode Light, frame 376 on Auto):

1. `instance.setProperties {ids:[367], properties:{Style:"Tonal", State:"Hover"}}` → `{ok:true}`
2. `instance.setProperties {ids:[377], properties:{Level:"Hard"}}`
3. `variable.setMode {ids:[364], collection:"Theme", mode:"Dark"}`, same on 376
4. `proto.evaluate {expression:"mode(Theme)", id:365}` → `"Dark"`
5. hide the 5 children of 364, `inspect.code` (stand-in for a render: shows `--surface: #111111`, `--gap: 16px`)
6. restore: children visible, `Style:"Primary", State:"Default"`, `Level:"Easy"`,
   `variable.setMode … mode:"Light"` on 364, `mode: null` (Auto) on 376
7. `save_file("after-edits.zip", "application/zip", 1000 bytes)` → ok

Results:
- `document.inspect {depth:60, allPages:true}` + `variable.list` + `proto.settings` before/after
  (minus `history`, `dirty`): **identical** (sha256 prefix `7c739f30d04ba973` both).
- `file.saveAs {data:true}` before/after: **`document.json` byte-identical** (sha `6f8184d005b4`),
  thumbnail too. This covers overflow/scrollPosition/var_modes as well.
- The text override "Go now" and the opacity override survived the variant round-trip.
- The run still adds one undo step named after the plugin ("Spike probe") and the doc stays
  dirty: the plugin can't avoid that.
- `save_file` after such edits in the same run: accepted (`ok`).
- **Caveat:** to restore a mode the plugin must know if it was explicit or Auto, and
  `variableModes` is not readable (see 2). Alternative: a plugin run that returns an error is
  rolled back entirely (document, selection, page) — but then `save_file` doesn't happen and only
  the error text comes back.

## 5. Variables and flows

- `variable.list {}` →
  `{collections:[{id:"VariableCollectionId:1", name:"Theme", modes:[{id:"VariableCollectionId:1/mode1", name:"Light"},…]}],
    variables:[{id:"VariableID:1", name:"surface", collection, resolvedType:"color", description,
                values:{"VariableCollectionId:1/mode1":{type:"color", value:{r,g,b,a}}, …}}]}`.
  Both example files have **0 variables**; the fixture uses spike-made ones.
- Flow starting points: `node.get {id:<page id>}` → `flows:[{name:"Onboarding", start:2, description:""}]`.
  `page.list {}` → `[{id, name, current, children, divider}]`.
- `proto.settings {}` (reads; also undoable when given params) →
  `{device:"iPhone 16", rotation:"portrait", color:"Black", background:"#1E1E1E",
    screen:{width:393,height:852}, customSize:{width:1280,height:720}, responsive:false, ok:true}`.
  The onboarding file has `device:"None"` (see `proto_settings.json`).

## 6. save_file over control / set_output size

- `plugin.run` sent over control with a `save_file` call: returns in **6 ms** with
  `{output, logs, calls:4, fuel:523106, panel:null}`; no Save dialog in the app window
  (`ui.screenshot` after it, `ui.inspect` has no dialog). I couldn't check for a native macOS
  sheet (osascript lacks accessibility permission), and no file was written anywhere I could find.
  Treat it as: not blocking, but also not producing a file in e2e. Use `set_output` for e2e.
- `set_output` size (returned as `output` over control): 1 MB ok (35 M fuel), **12 MB ok**
  (422 M fuel, 0.4 s, naive serde impl), **16 MB: the plugin crashes** (`wasm unreachable`: the
  16 MB string limit / memory). So a ≤12 MB base64 zip in `set_output` works, but costs ~40 % of
  the fuel budget with serde_json; write the output string directly to keep it cheap.

## 7. Fuel and host calls (onboarding, 4 top-level frames, 142 layers)

- Depth-first `node.get` on every layer: **429 calls, 73,968,793 fuel**, 0.04 s.
- Same plus `inspect.code {language:"html"}` per frame: 441 calls, 77,163,033 fuel.
- Budget: 1,000,000,000 fuel, 100,000 calls per run. Each call costs 10,000 fuel + 1 per byte
  copied. (`file.export` per frame couldn't be measured: refused.)

## Building and running the plugin (practical)

- `cargo build --release --target wasm32-unknown-unknown` failed on this Mac: the host build
  scripts (serde) don't link against the CommandLineTools `MacOSX27.0.sdk` (`ld: tapi error …
  unknown architecture arm64e.x1-macos`). Workaround: `SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk`.
- The SDK works as a path dependency to `plugins/sdk`; `serde_json` with `default-features = false, features = ["alloc"]`.
- `plugin.import {path: <folder>}` then `plugin.run {id, command, params, fuel?}` → `{plugin, command, output, logs, calls, fuel, panel}`; a plugin error comes back as control error `"<Plugin name>: <message>"`.
- `select.set {ids}` over control sets `input.selection` for the next run.
- A plugin runs on the **active** tab (`doc.switch {index}` over control).
- The spike client was replaced by `exporter/figcraft_export/control.py`.

## Fixtures (`exporter/tests/fixtures/`)

| File | Content |
|---|---|
| `node_get_onboarding_welcome.json` | plugin `node.get` for every layer of "1 Welcome" (id 2) |
| `node_get_design_system_buttons.json` | plugin `node.get` for "Buttons" (171): component set, 9 variants |
| `node_get_design_system_probe.json` | **synthetic** probe frame 364: instances, bound vars, blend, effects, mask, every interaction kind tried |
| `node_get_pages.json` | page nodes with `flows`; variant 219 with a `changeTo` + spring |
| `component_properties.json` | `component.properties` for an instance and a set |
| `variables.json` | `variable.list` (onboarding: empty; design system + synthetic Theme) |
| `proto_settings.json` | `proto.settings {}` for both |
| `export_*.json` | **control-channel** `file.export` replies (plugins are refused) |

## Control-only facts (measured on FigCraft 0.18.1, macOS, task 6)

- **Selection**: `document.inspect {depth:0}` -> `selection: [ids]` (also `ui.inspect` -> `status.selection`). Set with `engine.execute select.set {ids}` -> `{selection}`. There is no `select.get`.
- **Current page**: `document.inspect` -> `currentPage` (page id); `engine.execute page.list {}` -> `[{id, name, children, current, divider}]`. Switch with `doc.switch {index}` (documents) / page commands.
- **App version**: not exposed over control (no `app.version`/`app.info`; `ui.inspect` has no version; `help.about` returns `{ok:true}` only). Use the executable: `FigCraft --version` prints `FigCraft 0.18.1 (<git hash>)` (macOS verified). The exporter reads it from the executable it finds and skips the check if unreadable.
- **`file.saveAs {data:true}`** returns `{bytes, data (base64 .figcraft zip), name}` and leaves `path`, `dirty` (clean or dirty) and `history` unchanged, and writes nothing on disk.
- **`edit.undo` / `edit.redo`** (`{}` -> `{undone:true}` / `{redone:true}`; `{undone:false}` when nothing to undo): every `node.set`, `instance.setProperties` and `variable.setMode` call adds exactly one history entry ("Set properties", "Set instance properties", "Set variable mode"; `document.inspect.history.undo` lists newest first) and one `edit.undo` reverts exactly that step (verified for node.set name/opacity and instance variant property; setMode's undo step verified by history, the mode itself is not readable). After undoing everything `dirty` stays `true`.
- `node.get` cannot read `variableModes` (unknown field). `variable.list {}` -> `{collections:[{id,name,modes}], variables:[...]}`; `variable.bind` takes the variable id (`VariableID:1`), a `Collection/name` path was refused here.
- `FigCraft.exe --version` on Windows is **unverified** (the exporter passes `CREATE_NO_WINDOW` and skips the version check if nothing is printed).
