import base64
import hashlib
import io
import json
import unittest
import zipfile

from figcraft_export import docfile
from tests.fake_control import load_fixture


def _reply_with(doc):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("document.json", json.dumps(doc).encode("utf-8"))
    data = buf.getvalue()
    return {"bytes": len(data), "data": base64.b64encode(data).decode("ascii"), "name": "x.figcraft"}


class DocfileTests(unittest.TestCase):
    def setUp(self):
        self.fx = load_fixture("saveas_scenario")

    def test_overflow_position_and_var_modes_from_document_json(self):
        ex = docfile.extras(self.fx["reply"])
        self.assertEqual(ex["146"]["overflow"], "vertical")
        self.assertEqual(ex["146"]["position"], "scroll")
        self.assertEqual(ex["157"]["position"], "fixed")
        self.assertEqual(ex["157"]["overflow"], "none")
        self.assertEqual(ex["163"]["varModes"], {"VariableCollectionId:2": "VariableCollectionId:2/mode2"})
        self.assertEqual(ex["146"]["varModes"], {})
        self.assertNotIn("149", ex)  # nothing special on it

    def test_scrolls_and_sticky_values(self):
        doc = {"nodes": {"5": {"id": 5, "scroll_position": "sticky"}, "6": {"id": 6, "scroll_position": "scrolls", "overflow": "both"}}}
        ex = docfile.extras(_reply_with(doc))
        self.assertEqual(ex["5"]["position"], "sticky")
        self.assertEqual(ex["6"], {"overflow": "both", "position": "scroll", "varModes": {}})

    def test_digest_is_sha256_of_document_json(self):
        self.assertEqual(docfile.digest(self.fx["reply"]), self.fx["document_sha256"])
        raw = base64.b64decode(self.fx["reply"]["data"])
        doc = zipfile.ZipFile(io.BytesIO(raw)).read("document.json")
        self.assertEqual(docfile.digest(self.fx["reply"]), hashlib.sha256(doc).hexdigest())

    def test_unreadable_reply_raises_french_error(self):
        with self.assertRaises(docfile.DocFileError) as cm:
            docfile.extras({"data": base64.b64encode(b"not a zip").decode("ascii")})
        self.assertIn("document FigCraft", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
