from probe import *
FX = ROOT + "/plugin/tests/fixtures/"
def ids_of(doc, root):
    n = fc.request('node.get', {'id': root, 'depth': 60, 'fields': [], 'document': doc})
    out = []
    def w(x):
        out.append(x['id']); [w(c) for c in x.get('children', [])]
    w(n); return out
def tree(doc_index, root):
    fc.execute('doc.switch', {'index': doc_index})
    ids = ids_of(doc_index + 1, root)
    r = probe([{'cmd': 'node.get', 'params': {'id': i}, 'trim': 10**8} for i in ids])
    return {str(s['result']['id']): s['result'] for s in r['output']['steps']}, r['fuel'], r['calls']
def dump(name, obj):
    with open(FX + name, 'w') as f: json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=True); f.write('\n')
    print(name, os.path.getsize(FX + name))
NOTE = "Raw engine `node.get` replies (one level of children), fetched from inside the spike plugin via the `call` import, FigCraft 0.18.1. Keyed by layer id; `root` is the frame."
for (di, root, name, extra) in [(0, 2, 'node_get_onboarding_welcome.json', 'examples/ridgeline-onboarding.figcraft, frame \"1 Welcome\"'),
                                 (0, 1, None, None),
                                 (1, 171, 'node_get_design_system_buttons.json', 'examples/ridgeline-design-system.figcraft, frame \"Buttons\" (component set with 9 variants)'),
                                 (1, 364, 'node_get_design_system_probe.json', 'SYNTHETIC: frame \"Probe screen\" added by the spike to ridgeline-design-system (never saved): instances, Theme variable modes, bound variables, blend, effects, mask group, overflow vertical, fixed header, sticky bar, interactions of every kind tried')]:
    if name is None: continue
    nodes, fuel, calls = tree(di, root)
    dump(name, {'_note': NOTE, 'source': extra, 'root': root, 'nodes': nodes})
# page nodes (flows) + component set w/ interaction variant
fc.execute('doc.switch', {'index': 0})
r = probe([{'cmd': 'node.get', 'params': {'id': 1}, 'trim': 10**8}, {'cmd': 'proto.settings', 'params': {}}, {'cmd': 'variable.list', 'params': {}}])
p1, ps1, v1 = [s['result'] for s in r['output']['steps']]
fc.execute('doc.switch', {'index': 1})
r = probe([{'cmd': 'node.get', 'params': {'id': 219}, 'trim': 10**8}, {'cmd': 'proto.settings', 'params': {}}, {'cmd': 'variable.list', 'params': {}},
           {'cmd': 'component.properties', 'params': {'id': 367}}, {'cmd': 'component.properties', 'params': {'id': 211}}, {'cmd': 'node.get', 'params': {'id': 1}, 'trim': 10**8}])
c219, ps2, v2, cp_inst, cp_set, p2 = [s['result'] for s in r['output']['steps']]
dump('node_get_pages.json', {'_note': NOTE, 'onboarding_page_1': p1, 'design_system_page_1_with_probe_flow': p2, 'design_system_variant_219_with_changeTo_spring': c219})
dump('component_properties.json', {'_note': 'Raw `component.properties` replies from inside the plugin.', 'instance_367': cp_inst, 'set_211': cp_set})
dump('variables.json', {'_note': 'Raw `variable.list {}` replies from inside the plugin. design_system includes the SYNTHETIC Theme collection (Light/Dark) added by the spike; both example files ship with 0 variables.', 'onboarding': v1, 'design_system_with_probe': v2})
dump('proto_settings.json', {'_note': 'Raw `proto.settings {}` replies from inside the plugin. design_system device was set to iPhone 16 by the spike (synthetic).', 'onboarding': ps1, 'design_system_with_probe': ps2})
# exports: control only (plugins are refused file.export)
fc.execute('doc.switch', {'index': 0})
for fmt, extra in [('svg', {}), ('png', {'scale': 1})]:
    rq = dict({'ids': [2], 'format': fmt}, **extra)
    rep = fc.execute('file.export', rq)
    dump('export_onboarding_welcome_%s.json' % fmt, {'_note': 'CONTROL CHANNEL reply (engine.execute file.export, no path). From a plugin the same call fails: "`file.export` isn\'t available to plugins".', 'request': {'command': 'file.export', 'params': rq}, 'reply': rep})
fc.execute('doc.switch', {'index': 1})
rq = {'ids': [364], 'format': 'svg'}
dump('export_design_system_probe_svg.json', {'_note': 'CONTROL CHANNEL reply (file.export, no path), synthetic probe frame.', 'request': {'command': 'file.export', 'params': rq}, 'reply': fc.execute('file.export', rq)})
