from probe import *
import hashlib
def x(c,p):
    try: r=fc.execute(c,p); print('OK',c,json.dumps(r)[:150]); return r
    except Exception as e: print('ERR',c,str(e)[:300])
def snap():
    d=fc.request('document.inspect',{'depth':60,'allPages':True})
    hist=d.pop('history'); dirty=d.pop('dirty')
    v=fc.execute('variable.list',{}); ps=fc.execute('proto.settings',{})
    blob=json.dumps([d,v,ps],sort_keys=True)
    return blob, hist, dirty
if '--setup' in sys.argv:
    x('text.set',{'ids':[370],'text':'Go now'}) or x('node.set',{'ids':[370],'props':{'characters':'Go now'}})
    x('node.set',{'ids':[367],'props':{'opacity':0.8}})
    # frame with Auto mode (no explicit mode)
    f2=x('node.create',{'type':'frame','x':3500,'y':0,'width':200,'height':200,'name':'Auto-mode frame','props':{'fill':{'$var':'Theme/surface'}}})
    x('instance.create',{'component':231,'parent':f2['id']})
    print('f2',f2)
    sys.exit()
F2=int(sys.argv[1]); TG=int(sys.argv[2])
fc.execute('select.none',{})
b,h0,d0=snap()
kids=[c['id'] for c in fc.request('node.get',{'id':364,'depth':1})['children']]
steps=[
 {'cmd':'component.properties','params':{'id':367}},
 {'cmd':'instance.setProperties','params':{'ids':[367],'properties':{'Style':'Tonal','State':'Hover'}}},
 {'cmd':'node.get','params':{'id':367},'trim':200},
 {'cmd':'instance.setProperties','params':{'ids':[TG],'properties':{'Level':'Hard'}}},
 {'cmd':'variable.setMode','params':{'ids':[364],'collection':'Theme','mode':'Dark'}},
 {'cmd':'variable.setMode','params':{'ids':[F2],'collection':'Theme','mode':'Dark'}},
 {'cmd':'proto.evaluate','params':{'expression':'mode(Theme)','id':kids[0]}},
]+[{'cmd':'node.set','params':{'ids':[k],'props':{'visible':False}}} for k in kids]+[
 {'cmd':'inspect.code','params':{'id':364,'language':'html'},'trim':300},
]+[{'cmd':'node.set','params':{'ids':[k],'props':{'visible':True}}} for k in kids]+[
 {'cmd':'instance.setProperties','params':{'ids':[367],'properties':{'Style':'Primary','State':'Default'}}},
 {'cmd':'instance.setProperties','params':{'ids':[TG],'properties':{'Level':'Easy'}}},
 {'cmd':'variable.setMode','params':{'ids':[364],'collection':'Theme','mode':'Light'}},
 {'cmd':'variable.setMode','params':{'ids':[F2],'collection':'Theme','mode':None}},
 {'cmd':'node.get','params':{'id':370}},
 {'op':'save_file','name':'after-edits.zip','mime':'application/zip','bytes':1000},
]
r=probe(steps)
json.dump(r,open('/private/tmp/claude-501/-Users-jules-Documents-Agence-Julos-01-PROJETS-102-Figcraft-to-HTML/20055277-4aa0-4f3e-bab5-4bc769610fb4/scratchpad/q4.json','w'),indent=1)
for s in r['output']['steps']:
    print(s.get('cmd',s.get('op')), s.get('ok'), (s.get('error') or json.dumps(s.get('result'))[:160]))
print('fuel',r['fuel'],'calls',r['calls'])
a,h1,d1=snap()
print('identical:',a==b, hashlib.sha256(b.encode()).hexdigest()[:16], hashlib.sha256(a.encode()).hexdigest()[:16])
print('history before',h0,'dirty',d0); print('history after',h1,'dirty',d1)
if a!=b:
    import difflib
    for l in list(difflib.unified_diff(json.dumps(json.loads(b),indent=1,sort_keys=True).splitlines(),json.dumps(json.loads(a),indent=1,sort_keys=True).splitlines(),lineterm='',n=2))[:80]: print(l)
