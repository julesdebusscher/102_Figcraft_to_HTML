import base64
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import figcraft_export.__main__ as cli
from figcraft_export import writer
from figcraft_export.control import ControlError
from tests.fake_control import load_fixture
from tests.test_control import free_port

ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIO = load_fixture("walk_scenario")
SAVEAS = load_fixture("saveas_scenario")["reply"]
NAME = 'Écran / 🚀 "test"'
SVG = '<svg width="20" height="10"><g><path transform="matrix(1 0 0 1 0 0)" d="M0 0"/></g></svg>'


def changed_saveas():
    raw = base64.b64decode(SAVEAS["data"])
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        doc = z.read("document.json")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("document.json", doc + b" ")
    return dict(SAVEAS, data=base64.b64encode(buf.getvalue()).decode("ascii"))


class Doc(object):
    """FigCraft over the recorded walk scenario, plus what the renderer needs: labelled undo
    history, node.get fields/outline, file.export (tiny SVG/PNG), file.saveAs (digest changes
    while any step is in the history)."""

    def __init__(self, on_export=None):
        self.byid = {}
        for cmd, params, reply in copy.deepcopy(SCENARIO["calls"]):
            self.byid[(cmd, params.get("id"))] = reply
        self.byid[("node.get", 146)]["name"] = NAME   # the first screen, Accueil
        self.history, self.exports, self.calls = [], 0, []
        self.on_export = on_export

    def close(self):
        pass

    def request(self, method, params=None, timeout_ms=60000):
        self.calls.append((method, params))
        if method == "document.inspect":
            r = copy.deepcopy(self.byid[("document.inspect", None)])
            r["history"] = {"undo": list(reversed(self.history)), "redo": 0}
            return r
        raise AssertionError(method)

    def execute(self, command, params=None, timeout_ms=60000):
        params = params or {}
        self.calls.append((command, params))
        if command == "file.saveAs":
            return copy.deepcopy(SAVEAS) if not self.history else changed_saveas()
        if command == "command.batch":
            self.history.append(params["label"])
            return [{"ok": True}] * len(params["commands"])
        if command == "edit.undo":
            if not self.history:
                return {"undone": False}
            self.history.pop()
            return {"undone": True}
        if command == "file.export":
            self.exports += 1
            if self.on_export:
                self.on_export(self)
            if params["format"] == "png":
                return {"data": base64.b64encode(b"\x89PNG fake").decode("ascii")}
            return {"data": base64.b64encode(SVG.encode("utf-8")).decode("ascii")}
        key = (command, params.get("id"))
        if key not in self.byid:
            if command == "node.get" and ("fields" in params or "outline" in params):
                return {"id": params["id"], "type": "RECTANGLE"}
            raise ControlError("unknown %s %s" % key)
        reply = copy.deepcopy(self.byid[key])
        if command == "node.get" and "fields" in params:
            return dict({k: reply[k] for k in params["fields"] if k in reply}, id=params["id"])
        if command == "node.get" and params.get("outline"):
            return {"id": params["id"], "children": [{"id": c["id"], "visible": c.get("visible", True)}
                                                     for c in reply.get("children") or []]}
        return reply


def run(doc, *argv, **patches):
    out, err = io.BytesIO(), io.BytesIO()
    sout = io.TextIOWrapper(out, encoding="cp1252", errors="strict")     # a cp1252 console
    serr = io.TextIOWrapper(err, encoding="cp1252", errors="strict")
    opened = []
    with mock.patch.object(cli, "Control", lambda port: doc), \
            mock.patch.object(cli.launcher, "find_figcraft", lambda cfg: None), \
            mock.patch.object(cli.webbrowser, "open", lambda url: opened.append(url)), \
            mock.patch.object(sys, "stdout", sout), mock.patch.object(sys, "stderr", serr):
        with redirect_stdout(sout), redirect_stderr(serr):
            rc = cli.main(["export", "--port", "1"] + list(argv))
        sout.flush()
        serr.flush()
    return rc, out.getvalue().decode("utf-8"), err.getvalue().decode("utf-8"), opened


def data_of(folder):
    text = (folder / "data.js").read_text(encoding="utf-8")
    return json.loads(text[len(writer.DATA_PREFIX):-2])


class ExportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / "Élodie" / "Mes prototypes"
        self.out.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_export_end_to_end_with_fake_control(self):
        doc = Doc()
        rc, out, err, opened = run(doc, "--out", str(self.out), "--no-open")
        self.assertEqual(rc, 0, err)
        folder = self.out / "ridgeline-onboarding"
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         ["assets", "data.js", "index.html", "player.css", "player.js"])
        data = data_of(folder)
        self.assertEqual(data["title"], "Ridgeline onboarding")
        self.assertEqual(data["screens"]["146"]["name"], NAME)
        n = len(data["screens"])
        self.assertGreaterEqual(n, 4)
        self.assertIn("%d écrans exportés (" % n, out)
        self.assertIn("dans « %s »" % folder, out)
        self.assertLess(out.index("Ne modifiez pas le document dans FigCraft pendant l'export."),
                        out.index("écrans exportés"))
        self.assertNotIn("Attention", out + err)
        self.assertEqual(doc.history, [])
        self.assertEqual(opened, [])
        srcs = set()
        for node in data["nodes"].values():
            for p in [node.get("paint")] + [a.get("paint") for a in node.get("alts") or []]:
                if p:
                    srcs.add(p["src"])
        self.assertTrue(srcs)
        for s in srcs:
            self.assertTrue((folder / s).is_file(), s)

    def test_opens_index_in_browser_unless_no_open(self):
        rc, out, err, opened = run(Doc(), "--out", str(self.out))
        self.assertEqual(rc, 0, err)
        self.assertEqual(opened, [(self.out / "ridgeline-onboarding" / "index.html").resolve().as_uri()])

    def test_title_option_names_the_folder(self):
        rc, out, err, _ = run(Doc(), "--out", str(self.out), "--no-open", "--title", "Mon proto / v2")
        self.assertEqual(rc, 0, err)
        self.assertEqual(data_of(self.out / "mon-proto-v2")["title"], "Mon proto / v2")

    def test_render_crash_leaves_no_folder_and_french_error(self):
        def crash(doc):
            if doc.exports == 7:
                raise ControlError("export impossible")
        doc = Doc(on_export=crash)
        rc, out, err, _ = run(doc, "--out", str(self.out), "--no-open")
        self.assertEqual(rc, 1)
        self.assertIn("FigCraft a refusé la commande : export impossible", err)
        self.assertIn("Aucun fichier n'a été écrit.", err)
        self.assertIn("Le document FigCraft est inchangé (vérifié).", err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(list(self.out.iterdir()), [])
        self.assertEqual(doc.history, [])

    def test_user_step_during_render_reports_steps_left(self):
        def user(doc):
            if doc.exports == 5:
                doc.history.append("Set properties")
        doc = Doc(on_export=user)
        rc, out, err, _ = run(doc, "--out", str(self.out), "--no-open")
        self.assertEqual(rc, 1)
        left = len([h for h in doc.history if h.startswith("Export HTML")])
        self.assertGreaterEqual(left, 1)
        self.assertIn("Impossible d'annuler toutes les modifications temporaires", err)
        self.assertIn("%d modification" % left, err)
        self.assertIn("Cmd/Ctrl+Z", err)
        self.assertIn("Attention : le document FigCraft a peut-être été modifié", err)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_write_error_removes_partial_folder(self):
        with mock.patch.object(writer, "_write_bytes", side_effect=OSError("disque plein")):
            rc, out, err, _ = run(Doc(), "--out", str(self.out), "--no-open")
        self.assertEqual(rc, 1)
        self.assertIn("disque plein", err)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_foreign_folder_refused_in_french(self):
        (self.out / "ridgeline-onboarding").mkdir()
        (self.out / "ridgeline-onboarding" / "a.txt").write_text("x", encoding="utf-8")
        rc, out, err, _ = run(Doc(), "--out", str(self.out), "--no-open")
        self.assertEqual(rc, 1)
        self.assertIn("ne contient pas un export", err)

    def test_empty_selection_french_error(self):
        doc = Doc()
        doc.byid[("document.inspect", None)]["selection"] = []
        rc, out, err, _ = run(doc, "--out", str(self.out), "--no-open")
        self.assertEqual(rc, 1)
        self.assertIn("Sélectionnez au moins une frame de premier niveau.", err)

    def test_folder_asked_when_no_out(self):
        with mock.patch.object(cli, "_ask_folder", lambda: str(self.out)):
            rc, out, err, _ = run(Doc(), "--no-open")
        self.assertEqual(rc, 0, err)
        self.assertTrue((self.out / "ridgeline-onboarding" / "index.html").is_file())

    def test_cancelled_folder_choice_writes_nothing(self):
        with mock.patch.object(cli, "_ask_folder", lambda: None):
            rc, out, err, _ = run(Doc(), "--no-open")
        self.assertEqual(rc, 1)
        self.assertIn("export annulé", err)
        self.assertEqual(list(self.out.iterdir()), [])


class DistTests(unittest.TestCase):
    def test_make_dist_contains_launchers_and_built_player(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.run([sys.executable, str(ROOT / "tools" / "make_dist.py"), "--out", tmp],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
            d = Path(tmp) / "FigCraft Export HTML"
            for name in ("Ouvrir FigCraft.bat", "Exporter la sélection.bat", "Ouvrir FigCraft.command",
                         "Exporter la sélection.command", "LISEZMOI.txt", "figcraft_export/__main__.py",
                         "figcraft_export/writer.py", "figcraft_export/player/index.html",
                         "figcraft_export/player/player.js", "figcraft_export/player/player.css"):
                self.assertTrue((d / name).is_file(), name)
            self.assertFalse((d / "tests").exists())
            self.assertFalse((d / "config.json").exists())
            self.assertEqual(list(d.rglob("__pycache__")), [])
            self.assertEqual(writer.player_js(d / "figcraft_export" / "player"), writer.player_js(ROOT / "player"))
            raw = (d / "LISEZMOI.txt").read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            text = raw.decode("utf-8-sig")
            self.assertIn("ne touchez pas à FigCraft pendant l'export", text)
            self.assertIn("Python", text)
            self.assertIn(b"\r\n", raw)   # Notepad line ends
            # the dist runs on its own: French message when FigCraft is not there
            r = subprocess.run([sys.executable, "-m", "figcraft_export", "export", "--port", str(free_port())],
                               cwd=str(d), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(r.returncode, 1)
            self.assertIn("Impossible de joindre FigCraft", r.stderr.decode("utf-8"))
            self.assertEqual(cli.player_root(d / "figcraft_export"), d / "figcraft_export" / "player")


if __name__ == "__main__":
    unittest.main()
