//! Spike probe: runs a JSON script of steps through the plugin `call` import and returns every reply.
//! Step kinds:
//!   {"cmd": "...", "params": {...}, "trim": N?}         -> host call; strings longer than N (default 400) trimmed
//!   {"op": "selection"}                                   -> selection()
//!   {"op": "save_file", "name": "...", "mime": "...", "bytes": N}  -> save_file with N bytes
//!   {"op": "blob", "bytes": N}                            -> put an N-char base64-ish string in the output
//!   {"op": "walk", "roots": [ids], "export": {...}?}      -> node.get depth-first over roots, export each root
//!   {"op": "fail"}                                        -> return Err (rollback test)
use figcraft_plugin_sdk::{Input, Result, Value, call, entry, json, save_file, selection};

fn trim(v: &Value, n: usize) -> Value {
    match v {
        Value::String(s) if s.len() > n => {
            let mut cut = n;
            while !s.is_char_boundary(cut) { cut -= 1; }
            json!(format!("{}…[{} bytes]", &s[..cut], s.len()))
        }
        Value::Array(a) => Value::Array(a.iter().map(|x| trim(x, n)).collect()),
        Value::Object(o) => Value::Object(o.iter().map(|(k, x)| (k.clone(), trim(x, n))).collect()),
        _ => v.clone(),
    }
}

fn walk(roots: &[u64], export: Option<&Value>) -> Value {
    let mut nodes = 0u64;
    let mut bytes = 0u64;
    let mut errors = Vec::new();
    for &root in roots {
        let mut stack = vec![root];
        while let Some(id) = stack.pop() {
            match call("node.get", &json!({"id": id})) {
                Ok(n) => {
                    nodes += 1;
                    if let Some(ch) = n["children"].as_array() {
                        stack.extend(ch.iter().filter_map(|c| c["id"].as_u64()));
                    }
                }
                Err(e) => errors.push(json!({"id": id, "error": e})),
            }
        }
        if let Some(ex) = export {
            let mut p = ex.clone();
            p["ids"] = json!([root]);
            match call(ex["_cmd"].as_str().unwrap_or("export"), &{ let mut q = p.clone(); q.as_object_mut().map(|o| o.remove("_cmd")); q }) {
                Ok(r) => bytes += serde_json::to_string(&r).map(|s| s.len() as u64).unwrap_or(0),
                Err(e) => errors.push(json!({"export": root, "error": e})),
            }
        }
    }
    json!({"nodes": nodes, "exportReplyBytes": bytes, "errors": errors})
}

fn run(input: Input) -> Result<Value> {
    let script: Value = serde_json::from_str(input.str("script").unwrap_or("[]")).map_err(|e| format!("script: {e}"))?;
    let steps = script.as_array().cloned().unwrap_or_default();
    let mut out = Vec::new();
    for step in steps {
        let n = step["trim"].as_u64().unwrap_or(400) as usize;
        let r = if let Some(cmd) = step["cmd"].as_str() {
            match call(cmd, &step.get("params").cloned().unwrap_or(json!({}))) {
                Ok(v) => json!({"cmd": cmd, "ok": true, "result": trim(&v, n)}),
                Err(e) => json!({"cmd": cmd, "ok": false, "error": e}),
            }
        } else {
            match step["op"].as_str().unwrap_or("") {
                "selection" => json!({"op": "selection", "result": selection()}),
                "save_file" => {
                    let len = step["bytes"].as_u64().unwrap_or(10) as usize;
                    let data = vec![b'x'; len];
                    match save_file(step["name"].as_str().unwrap_or("probe.txt"), step["mime"].as_str().unwrap_or("text/plain"), &data) {
                        Ok(()) => json!({"op": "save_file", "ok": true}),
                        Err(e) => json!({"op": "save_file", "ok": false, "error": e}),
                    }
                }
                "blob" => {
                    let len = step["bytes"].as_u64().unwrap_or(10) as usize;
                    json!({"op": "blob", "data": "A".repeat(len)})
                }
                "walk" => {
                    let roots: Vec<u64> = step["roots"].as_array().map(|a| a.iter().filter_map(Value::as_u64).collect()).unwrap_or_else(|| input.selection.clone());
                    json!({"op": "walk", "result": walk(&roots, step.get("export"))})
                }
                "fail" => return Err("probe asked to fail".into()),
                other => json!({"op": other, "error": "unknown op"}),
            }
        };
        out.push(r);
    }
    Ok(json!({"selection": input.selection, "steps": out}))
}

entry!(run);
