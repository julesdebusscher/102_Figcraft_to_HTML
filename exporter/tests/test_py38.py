import ast
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "figcraft_export"


class Py38Tests(unittest.TestCase):
    def test_all_sources_parse_as_python38(self):
        files = sorted(PKG.glob("*.py"))
        self.assertTrue(files)
        for f in files:
            src = f.read_text(encoding="utf-8")
            ast.parse(src, filename=str(f), feature_version=(3, 8))


if __name__ == "__main__":
    unittest.main()
