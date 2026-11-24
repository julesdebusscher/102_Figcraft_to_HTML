"""Temporary document edits over control, always undone (see EditSession)."""

UNDO_FAILED = "Impossible d'annuler toutes les modifications temporaires : vérifiez le document."
BATCH_LABEL = "Export HTML (temporaire)"


class RenderError(Exception):
    """French message, shown as is."""


class EditSession(object):
    """Temporary edits, all undone on exit (normal exit or any exception, Ctrl-C included).

    Every edit is sent as a `command.batch` (one undo step) with its own label
    "Export HTML (temporaire) #<n>", and recorded when it landed: on success, and also when
    the call failed or was interrupted but the top of FigCraft's undo history carries that
    label (a timed-out call may still have been applied). `edit.undo` is global, so before
    each undo the top of the history must be our label; otherwise (the user changed the
    document meanwhile) undoing stops and RenderError(UNDO_FAILED) is raised, leaving the
    user's step alone. A failed undo is retried once. A KeyboardInterrupt during the undos
    is held until they are done, then re-raised."""

    _count = [0]

    def __init__(self, ctl):
        self.ctl, self.edits = ctl, []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.undo_all()
        return False

    def _top(self):
        undo = ((self.ctl.request("document.inspect", {"depth": 0}) or {}).get("history") or {}).get("undo") or []
        return undo[0] if undo else None

    def apply(self, command, params):
        return self.batch([(command, params)])

    def batch(self, commands):
        """[(command, params)] as one labelled undo step."""
        if not commands:
            return None
        EditSession._count[0] += 1
        label = "%s #%d" % (BATCH_LABEL, EditSession._count[0])
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

    def undo_all(self):
        failed, interrupt, attempts = False, None, {}
        while self.edits:
            label = self.edits[-1]
            try:
                top = self._top()
            except KeyboardInterrupt as e:
                interrupt = e
                continue
            except Exception:
                failed = True
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
            self.edits.pop()
        self.edits = []
        if failed:
            raise RenderError(UNDO_FAILED)
        if interrupt is not None:
            raise interrupt
