"""Temporary document edits over control, always undone (see EditSession)."""
import binascii
import os

UNDO_FAILED = "Impossible d'annuler toutes les modifications temporaires : vérifiez le document."
BATCH_LABEL = "Export HTML (temporaire)"


_NONCE = binascii.hexlify(os.urandom(2)).decode("ascii")  # one per run: labels never match an older run's


class RenderError(Exception):
    """French message, shown as is. `remaining`: labels of our steps still in the document
    (newest last), when undoing could not finish."""

    def __init__(self, message, remaining=()):
        Exception.__init__(self, message)
        self.remaining = list(remaining)


class EditSession(object):
    """Temporary edits, all undone on exit (normal exit or any exception, Ctrl-C included).

    Every edit is sent as a `command.batch` (one undo step) with its own label
    "Export HTML (temporaire) <nonce>#<n>" (nonce: 4 hex digits per run), and recorded when it landed: on success, and also when
    the call failed or was interrupted but the top of FigCraft's undo history carries that
    label (a timed-out call may still have been applied). `edit.undo` is global, so before
    each undo the top of the history must be our label; otherwise (the user changed the
    document meanwhile) undoing stops and RenderError(UNDO_FAILED) is raised, leaving the
    user's step alone (RenderError.remaining lists our steps left). The history top and depth
    seen before the session's first edit are its baseline: back there, everything is undone
    (an undo that errored after working is no failure). A failed undo is retried once. When our
    label is still on top after an undo, a user step made in between was reverted instead: it is
    redone (`edit.redo`) and RenderError is raised. A KeyboardInterrupt during the undos
    is held until they are done, then re-raised."""

    _count = [0]

    def __init__(self, ctl):
        self.ctl, self.edits, self.baseline = ctl, [], None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.undo_all()
        return False

    def _state(self):
        """(top label of the undo history or None, its depth)."""
        undo = ((self.ctl.request("document.inspect", {"depth": 0}) or {}).get("history") or {}).get("undo") or []
        return (undo[0] if undo else None, len(undo))

    def _top(self):
        return self._state()[0]

    def apply(self, command, params):
        return self.batch([(command, params)])

    def batch(self, commands):
        """[(command, params)] as one labelled undo step."""
        if not commands:
            return None
        EditSession._count[0] += 1
        label = "%s %s#%d" % (BATCH_LABEL, _NONCE, EditSession._count[0])
        if self.baseline is None:
            self.baseline = self._state()
        try:
            result = self.ctl.execute("command.batch", {"label": label, "commands": [
                {"command": c, "params": p} for c, p in commands]})
        except BaseException:
            try:
                if self._top() == label:   # applied although the call failed (timeout, Ctrl-C)
                    self.edits.append(label)
            except Exception:
                pass
            raise
        self.edits.append(label)
        return result

    def _reverted_foreign(self, label):
        """After an undo meant for `label`: True when `label` is still on top, i.e. a user step
        made between our check and the undo was reverted instead; that step is redone."""
        try:
            if self._top() != label:
                return False
        except Exception:
            return False
        try:
            self.ctl.execute("edit.redo", {})
        except Exception:
            pass
        return True

    def undo_all(self):
        failed, interrupt, attempts = False, None, {}
        while self.edits:
            label = self.edits[-1]
            try:
                state = self._state()
            except KeyboardInterrupt as e:
                interrupt = e
                continue
            except Exception:
                failed = True
                break
            top = state[0]
            if state == self.baseline:     # back where the session started: all undone
                self.edits = []
                break
            if top != label:
                if top in self.edits:      # ours, deeper: the newer ones are already gone
                    del self.edits[self.edits.index(top) + 1:]
                    continue
                failed = True              # not ours: never undo the user's step
                break
            if attempts.get(label, 0) >= 2:
                failed = True              # undo keeps failing: give up rather than loop
                break
            attempts[label] = attempts.get(label, 0) + 1
            try:
                reply = self.ctl.execute("edit.undo", {})
            except KeyboardInterrupt as e:
                interrupt = e              # the top is checked again: it may have been undone
                continue
            except Exception:
                continue
            if isinstance(reply, dict) and reply.get("undone") is False:
                failed = True
                break
            try:
                foreign = self._reverted_foreign(label)
            except KeyboardInterrupt as e:
                interrupt, foreign = e, False
            if foreign:
                failed = True              # a user step landed just before: it is redone, ours stays
                break
            self.edits.pop()
        remaining, self.edits = list(self.edits), []
        if failed:
            raise RenderError(UNDO_FAILED, remaining)
        if interrupt is not None:
            raise interrupt
