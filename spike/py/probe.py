import sys, json, os
ROOT = "/Users/jules/Documents/Agence Julos/01_PROJETS/102_Figcraft_to_HTML"
sys.path.insert(0, ROOT + "/tools")
from fcctl import Fc, FcError
fc = Fc(7979)
PID = "local.spike.probe"
def imp():
    return fc.execute("plugin.import", {"path": ROOT + "/spike/probe"})
def probe(steps, select=None, fuel=None):
    if select is not None:
        fc.execute("select.set", {"ids": select})
    p = {"id": PID, "command": "probe", "params": {"script": json.dumps(steps)}}
    if fuel: p["fuel"] = fuel
    return fc.execute("plugin.run", p, timeout_ms=300000)
def pp(x, n=4000):
    s = json.dumps(x, indent=1, ensure_ascii=False)
    print(s[:n] + ("\n…[%d chars]" % len(s) if len(s) > n else ""))
