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
            self.assertRegex(label, r"^Export HTML \(temporaire\) [0-9a-f]{4}#\d+$")
        self.assertEqual(labels[0].split("#")[0], labels[1].split("#")[0])   # one nonce per run
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

    def test_single_edit_undo_that_errors_after_undoing_is_no_failure(self):
        doc = SimDoc({1: rect("a")}, undo_script=["raise_after"])
        doc.user_edit(1, {"name": "earlier user step"})     # baseline top is the user's own step
        start = doc.snapshot()
        with edits.EditSession(doc) as s:
            s.apply("node.set", {"ids": [1], "props": {"opacity": 0.5}})
        self.assertEqual(doc.snapshot(), start)
        self.assertEqual(len(doc.history), 1)

    def test_render_error_lists_the_steps_left_in_the_document(self):
        doc = SimDoc({1: rect("a"), 2: rect("b")})
        with self.assertRaises(edits.RenderError) as cm:
            with edits.EditSession(doc) as s:
                s.apply("node.set", {"ids": [1], "props": {"opacity": 0.5}})
                s.apply("node.set", {"ids": [2], "props": {"opacity": 0.2}})
                labels = [h[0] for h in doc.history]
                doc.user_edit(1, {"name": "user"})
        self.assertEqual(cm.exception.remaining, labels)
        self.assertEqual(str(cm.exception), edits.UNDO_FAILED)

    def test_user_step_landing_just_before_an_undo_is_redone_and_reported(self):
        doc = SimDoc({1: rect("a"), 2: rect("b")}, undo_script=["user_first"])
        with self.assertRaises(edits.RenderError) as cm:
            with edits.EditSession(doc) as s:
                s.apply("node.set", {"ids": [2], "props": {"opacity": 0.5}})
                label = doc.history[-1][0]
        self.assertEqual(doc.state["nodes"][1]["name"], "racing user step")   # the user's step is back
        self.assertEqual([h[0] for h in doc.history], [label, "Set properties"])
        self.assertEqual(cm.exception.remaining, [label])
        self.assertEqual(len(calls(doc, "edit.redo")), 1)

    def test_failed_redo_says_the_user_step_was_undone(self):
        doc = SimDoc({1: rect("a"), 2: rect("b")}, undo_script=["user_first"], redo_fails=True)
        with self.assertRaises(edits.RenderError) as cm:
            with edits.EditSession(doc) as s:
                s.apply("node.set", {"ids": [2], "props": {"opacity": 0.5}})
                label = doc.history[-1][0]
        self.assertEqual(str(cm.exception), edits.USER_UNDONE)
        self.assertIn("Cmd/Ctrl+Maj+Z", str(cm.exception))
        self.assertTrue(cm.exception.user_undone)
        self.assertEqual(cm.exception.remaining, [label])
        self.assertEqual([h[0] for h in doc.history], [label])      # the user's step sits in redo
        self.assertEqual(len(calls(doc, "edit.undo")), 1)

    def test_undo_that_raises_after_reverting_a_user_step_is_redone_and_reported(self):
        doc = SimDoc({1: rect("a"), 2: rect("b")}, undo_script=["user_first_raise"])
        with self.assertRaises(edits.RenderError) as cm:
            with edits.EditSession(doc) as s:
                s.apply("node.set", {"ids": [2], "props": {"opacity": 0.5}})
                label = doc.history[-1][0]
        self.assertEqual(doc.state["nodes"][1]["name"], "racing user step")
        self.assertEqual([h[0] for h in doc.history], [label, "Set properties"])
        self.assertEqual(cm.exception.remaining, [label])
        self.assertFalse(cm.exception.user_undone)
        self.assertEqual(len(calls(doc, "edit.undo")), 1)

    def test_inconclusive_check_after_undo_keeps_the_label_until_proven_undone(self):
        doc = SimDoc({1: rect("a"), 2: rect("b")}, inspect_fail_after_undo=1)
        start = doc.snapshot()
        with edits.EditSession(doc) as s:
            s.apply("node.set", {"ids": [1], "props": {"opacity": 0.5}})
            s.apply("node.set", {"ids": [2], "props": {"opacity": 0.2}})
        self.assertEqual(doc.snapshot(), start)
        self.assertEqual(len(calls(doc, "edit.undo")), 2)        # never undone twice
        # the check keeps failing: the label stays in `remaining`, though it may be undone
        doc = SimDoc({1: rect("a"), 2: rect("b")}, inspect_fail_after_undo=5)
        with self.assertRaises(edits.RenderError) as cm:
            with edits.EditSession(doc) as s:
                s.apply("node.set", {"ids": [1], "props": {"opacity": 0.5}})
                label = doc.history[-1][0]
        self.assertEqual(cm.exception.remaining, [label])

    def test_failed_undo_then_user_step_keeps_our_label_in_remaining(self):
        doc = SimDoc({1: rect("a"), 2: rect("b")}, undo_script=["raise_then_user"])
        with self.assertRaises(edits.RenderError) as cm:
            with edits.EditSession(doc) as s:
                s.apply("node.set", {"ids": [1], "props": {"opacity": 0.5}})
                s.apply("node.set", {"ids": [2], "props": {"opacity": 0.2}})
                labels = [h[0] for h in doc.history]
        self.assertEqual(cm.exception.remaining, labels)          # both still in the document
        self.assertEqual([h[0] for h in doc.history], labels + ["Set properties"])
        self.assertEqual(doc.state["nodes"][1]["name"], "user step after a failed undo")
        self.assertEqual(len(calls(doc, "edit.undo")), 1)


if __name__ == "__main__":
    unittest.main()
