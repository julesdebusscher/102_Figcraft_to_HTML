from probe import *
import base64, io, zipfile, hashlib, subprocess
def filebytes():
    r=fc.execute('file.saveAs',{'data':True})
    z=zipfile.ZipFile(io.BytesIO(base64.b64decode(r['data'])))
    return {n: z.read(n) for n in z.namelist()}, r.get('name')
A,name=filebytes()
print('entries',{k:len(v) for k,v in A.items()}, name)
print('path still', fc.request('document.inspect',{'depth':0})['path'])
out=subprocess.run(['python3','q4.py','376','377'],capture_output=True,text=True).stdout
print([l for l in out.splitlines() if l.startswith(('identical','fuel'))])
B,_=filebytes()
for k in sorted(set(A)|set(B)):
    print(k, 'same' if A.get(k)==B.get(k) else 'DIFF', hashlib.sha256(A.get(k,b'')).hexdigest()[:12], hashlib.sha256(B.get(k,b'')).hexdigest()[:12])
    if A.get(k)!=B.get(k) and k.endswith('.json'):
        import difflib
        a=json.dumps(json.loads(A[k]),indent=1,sort_keys=True).splitlines(); b=json.dumps(json.loads(B[k]),indent=1,sort_keys=True).splitlines()
        for l in list(difflib.unified_diff(a,b,lineterm='',n=1))[:60]: print('   ',l)
