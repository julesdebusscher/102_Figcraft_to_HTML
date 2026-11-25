"""Temporary document edits over control, always undone (see EditSession)."""
import binascii
import os

UNDO_FAILED = "Impossible d'annuler toutes les modifications temporaires : vérifiez le document."
USER_UNDONE = ("L'export a annulé par erreur votre dernière modification dans FigCraft : "
               "rétablissez-la avec Cmd/Ctrl+Maj+Z, puis vérifiez le document.")
BATCH_LABEL = "Export HTML (temporaire)"
FINAL_LABEL = "Export HTML (fin)"   # the no-op step that pushes our undone steps off the redo stack


_NONCE = binascii.hexlify(os.urandom(2)).decode("ascii")  # one per run: labels never match an older run's


class RenderError(Exception):
    """French message, shown as is. `remaining`: labels of our steps still in the document
    (newest last), when undoing could not finish. `user_undone`: the user's last step was
    reverted by our undo and could not be redone (message USER_UNDONE)."""

    def __init__(self, message, remaining=(), user_undone=False):
        Exception.__init__(self, message)
        self.remaining = list(remaining)
        self.user_undone = user_undone


def merge(outer, inner):
    """One RenderError for an outer session's failure and a nested session's: `remaining` lists
    the outer (older) labels first, `user_undone` if either says so (its message wins)."""
    user_undone = outer.user_undone or inner.user_undone
    remaining = list(outer.remaining) + [l for l in inner.remaining if l not in outer.remaining]
    return RenderError(USER_UNDONE if user_undone else str(inner), remaining, user_undone)


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
    (an undo that errored after working is no failure). A failed undo is retried once. Every undo
    is verified on the next history read: our label gone = undone; still on top with a deeper
    redo stack = a user step made in between was reverted instead (also after an undo that
    raised): it is redone (`edit.redo`) and RenderError is raised (USER_UNDONE when the redo did
    not bring it back); still on top with the same redo depth = nothing happened (retried). A
    label is only dropped once a history read shows it absent from the whole undo list, so
    `remaining` is exact (a user step made after a failed undo leaves our label in place). A KeyboardInterrupt during the undos
    is held until they are done, then re-raised."""

    _count = [0]

    def __init__(self, ctl):
        self.ctl, self.edits, self.baseline = ctl, [], None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if not isinstance(exc, RenderError):
            self.undo_all()
            return False
        # a nested session failed: still undo ours, then report both in one error
        try:
            self.undo_all()
        except RenderError as mine:
            raise merge(mine, exc)
        return False

    def _hist(self):
        """(top label of the undo history or None, its depth, redo depth, full undo list)."""
        h = (self.ctl.request("document.inspect", {"depth": 0}) or {}).get("history") or {}
        undo, redo = list(h.get("undo") or []), h.get("redo") or 0
        return (undo[0] if undo else None, len(undo), len(redo) if isinstance(redo, list) else int(redo), undo)

    def _state(self):
        """(top label of the undo history or None, its depth)."""
        return self._hist()[:2]

    def _top(self):
        return self._state()[0]

    def apply(self, command, params):
        return self.batch([(command, params)])

    def batch(self, commands, final=False):
        """[(command, params)] as one labelled undo step (`final`: labelled FINAL_LABEL <nonce>)."""
        if not commands:
            return None
        EditSession._count[0] += 1
        label = ("%s %s" % (FINAL_LABEL, _NONCE) if final
                 else "%s %s#%d" % (BATCH_LABEL, _NONCE, EditSession._count[0]))
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

    def _give_back(self, label):
        """Our undo reverted a user step (now on the redo stack): redo it. Returns
        (failure message, held KeyboardInterrupt or None)."""
        interrupt, reply = None, None
        try:
            reply = self.ctl.execute("edit.redo", {})
        except KeyboardInterrupt as e:
            interrupt = e
        except Exception:
            pass
        try:
            back = self._top() != label and not (isinstance(reply, dict) and reply.get("redone") is False)
        except KeyboardInterrupt as e:
            interrupt, back = e, False
        except Exception:
            back = False
        return (UNDO_FAILED if back else USER_UNDONE), interrupt

    def undo_all(self):
        failed, interrupt, attempts, unread = None, None, {}, 0
        pending = None   # redo depth before our last edit.undo of edits[-1], not yet verified
        while self.edits:
            label = self.edits[-1]
            try:
                top, depth, redo, undo = self._hist()
            except KeyboardInterrupt as e:
                interrupt = e
                continue
            except Exception:
                unread += 1                # inconclusive: keep the label, read again (3 tries)
                if unread >= 3:
                    failed = UNDO_FAILED
                    break
                continue
            unread = 0
            if pending is not None:
                before, pending = pending, None
                if label not in undo:      # proven gone: undone (a user step may sit on top now)
                    self.edits.pop()
                    continue
                if top != label:           # still in the document, under a user step: stop
                    failed = UNDO_FAILED
                    break
                if redo > before:          # still on top, yet something went to redo: the user's
                    failed, held = self._give_back(label)
                    interrupt = held or interrupt
                    break
                # same redo depth: nothing happened, retry below
            if (top, depth) == self.baseline:   # back where the session started: all undone
                self.edits = []
                break
            if top != label:
                if top in self.edits:      # ours, deeper: the newer ones are already gone
                    del self.edits[self.edits.index(top) + 1:]
                    continue
                failed = UNDO_FAILED       # not ours: never undo the user's step
                break
            if attempts.get(label, 0) >= 2:
                failed = UNDO_FAILED       # undo keeps failing: give up rather than loop
                break
            attempts[label] = attempts.get(label, 0) + 1
            reply = None
            try:
                reply = self.ctl.execute("edit.undo", {})
            except KeyboardInterrupt as e:
                interrupt = e
            except Exception:
                pass
            if isinstance(reply, dict) and reply.get("undone") is False:
                failed = UNDO_FAILED
                break
            pending = redo                 # verified on the next history read
        remaining, self.edits = list(self.edits), []
        if failed:
            raise RenderError(failed, remaining, user_undone=failed == USER_UNDONE)
        if interrupt is not None:
            raise interrupt
