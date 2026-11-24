import unittest

from figcraft_export import edits
from figcraft_export.control import ControlError
from tests.sim_doc import SimDoc


def rect(name):
    return {"type": "RECTANGLE", "name": name, "width": 100, "height": 60, "x": 0, "y": 0,
            "fills": [{"type": "solid", "color": "#00AAFF"}]}


def calls(doc, name):
    return [p for c, p in doc.calls if c == name]


class EditSessionTests(unittest.TestCase):
    def test_edit_session_labels_every_edit_and_undoes_in_reverse(self):
        doc = SimDoc({1: rect("a"), 2: rect("b")})
        start = doc.snapshot()
        with self.assertRaises(KeyError):
            with edits.EditSession(doc) as s:
                s.apply("node.set", {"ids": [1], "props": {"opacity": 0.5}})
                s.batch([("node.set", {"ids": [2], "props": {"opacity": 0.2}})])
                with self.assertRaises(ControlError):
                    s.apply("node.set", {"ids": [99], "props": {"opacity": 0.2}})  # failed: not recorded
                labels = [h[0] for h in doc.history]
                raise KeyError("boom")
        self.assertEqual(len(labels), 2)
        for label in labels:
            self.assertRegex(label, r"^Export HTML \(temporaire\) #\d+$")
        self.assertEqual([c for c, p in doc.calls if c in ("node.set", "instance.setProperties")], [])
        self.assertEqual(len(calls(doc, "edit.undo")), 2)
        self.assertEqual(doc.snapshot(), start)

    def test_failed_undo_retried_once_then_french_error_and_nothing_skipped(self):
        doc = SimDoc({1: rect("a"), 2: rect("b")}, fail_undo=1)
        with edits.EditSession(doc) as s:
            s.apply("node.set", {"ids": [1], "props": {"opacity": 0.5}})
        self.assertEqual(doc.history, [])                     # the retry worked
        doc = SimDoc({1: rect("a"), 2: rect("b")}, fail_undo=2)
        with self.assertRaises(edits.RenderError) as cm:
            with edits.EditSession(doc) as s:
                s.apply("node.set", {"ids": [1], "props": {"opacity": 0.5}})
                s.apply("node.set", {"ids": [2], "props": {"opacity": 0.2}})
        self.assertEqual(str(cm.exception),
                         "Impossible d'annuler toutes les modifications temporaires : vérifiez le document.")
        self.assertEqual(len(calls(doc, "edit.undo")), 2)
        self.assertEqual(len(doc.history), 2)                 # never undo past a step still on top

    def test_undo_that_errors_after_undoing_is_not_repeated(self):
        doc = SimDoc({1: rect("a"), 2: rect("b")}, undo_script=["raise_after"])
        start = doc.snapshot()
        with edits.EditSession(doc) as s:
            s.apply("node.set", {"ids": [1], "props": {"opacity": 0.5}})
            s.apply("node.set", {"ids": [2], "props": {"opacity": 0.2}})
        self.assertEqual(len(calls(doc, "edit.undo")), 2)
        self.assertEqual(doc.snapshot(), start)

    def test_ctrl_c_during_the_undos_finishes_them_then_reraises(self):
        doc = SimDoc({1: rect("a"), 2: rect("b")}, undo_script=["interrupt"])
        start = doc.snapshot()
        with self.assertRaises(KeyboardInterrupt):
            with edits.EditSession(doc) as s:
                s.apply("node.set", {"ids": [1], "props": {"opacity": 0.5}})
                s.apply("node.set", {"ids": [2], "props": {"opacity": 0.2}})
        self.assertEqual(doc.snapshot(), start)
        self.assertEqual(doc.history, [])


if __name__ == "__main__":
    unittest.main()
