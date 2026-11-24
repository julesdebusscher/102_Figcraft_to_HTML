import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from figcraft_export import version_ok
from figcraft_export import launcher
from tests.test_control import free_port

ROOT = Path(__file__).resolve().parent.parent


class LauncherTests(unittest.TestCase):
    def test_find_figcraft_windows_localappdata(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "Programs" / "FigCraft" / "FigCraft.exe"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"")
            found = launcher.find_figcraft({}, env={"LOCALAPPDATA": tmp}, platform="win32")
            self.assertEqual(found, exe)

    def test_find_figcraft_falls_back_to_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "mon dossier" / "FigCraft.exe"
            exe.parent.mkdir()
            exe.write_bytes(b"")
            found = launcher.find_figcraft(
                {"figcraft_path": str(exe)}, env={}, platform="win32"
            )
            self.assertEqual(found, exe)
            self.assertIsNone(launcher.find_figcraft({}, env={}, platform="win32"))

    def test_config_roundtrip_utf8_path_with_accents(self):
        cfg = {"figcraft_path": "C:\\Users\\Élodie\\FigCraft\\FigCraft.exe"}
        with tempfile.TemporaryDirectory() as tmp:
            launcher.save_config(tmp, cfg)
            self.assertEqual(launcher.load_config(tmp), cfg)
            raw = (Path(tmp) / "config.json").read_bytes()
            self.assertIn("Élodie".encode("utf-8"), raw)

    def test_export_without_figcraft_prints_french_and_exits_1(self):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run(
            [sys.executable, "-m", "figcraft_export", "export", "--port", str(free_port())],
            cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        err = p.stderr.decode("utf-8")
        self.assertEqual(p.returncode, 1)
        self.assertIn("Impossible de joindre FigCraft. Ouvrez-le avec « Ouvrir FigCraft ».", err)
        self.assertNotIn("Traceback", err)

    def test_version_ok_table(self):
        for v, ok in (("0.18.0", False), ("0.18.1", True), ("0.19.0-alpha", True), ("1.0", True), ("garbage", False)):
            self.assertEqual(version_ok(v), ok, v)


if __name__ == "__main__":
    unittest.main()
