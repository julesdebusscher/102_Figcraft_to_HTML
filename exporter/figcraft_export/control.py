"""Minimal client for the FigCraft control channel (stdlib only).

Newline-delimited JSON over 127.0.0.1:<port>: one request object per line,
one reply line per request ({"id", "ok", "result"|"error"}).
"""
import json
import socket

DEFAULT_PORT = 47917


class Unreachable(Exception):
    """FigCraft does not answer on the control port."""


class ControlError(Exception):
    """A reply with ok:false (the message is FigCraft's own)."""


class _Closed(Exception):
    pass


class Control:
    def __init__(self, port=DEFAULT_PORT, host="127.0.0.1"):
        self.port = port
        self.host = host
        self._sock = None
        self._buf = b""
        self._next_id = 0

    def _connect(self):
        if self._sock is None:
            try:
                self._sock = socket.create_connection((self.host, self.port), timeout=5)
            except OSError as e:
                raise Unreachable("%s:%s (%s)" % (self.host, self.port, e))
            self._buf = b""
        return self._sock

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def _readline(self, timeout_s):
        sock = self._sock
        sock.settimeout(timeout_s)
        while b"\n" not in self._buf:
            chunk = sock.recv(1 << 20)
            if not chunk:
                raise ConnectionError("FigCraft a fermé la connexion")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return line

    def request(self, method, params=None, timeout_ms=60000):
        """Send one request; return its result or raise ControlError on ok:false."""
        self._next_id += 1
        msg = {"id": self._next_id, "method": method, "params": params or {}}
        if timeout_ms != 60000:
            msg["timeoutMs"] = int(timeout_ms)
        data = (json.dumps(msg) + "\n").encode("utf-8")
        try:
            try:
                reply = self._roundtrip(data, timeout_ms, msg["id"])
            except _Closed:
                # Idle connections are closed after 60 s: reconnect once, but only
                # when the connection was closed (never after a timeout).
                self.close()
                try:
                    reply = self._roundtrip(data, timeout_ms, msg["id"])
                except _Closed as e:
                    self.close()
                    raise Unreachable(str(e))
        except ControlError:
            raise
        except BaseException:
            # Ctrl-C or any other error mid-request: this connection may still deliver the
            # reply later, so drop it; the next request starts on a fresh one.
            self.close()
            raise
        if not reply.get("ok"):
            raise ControlError(str(reply.get("error")))
        return reply.get("result")

    def _roundtrip(self, data, timeout_ms, want_id):
        sock = self._connect()
        try:
            sock.sendall(data)
        except (ConnectionError, BrokenPipeError) as e:
            raise _Closed(str(e))
        while True:
            try:
                line = self._readline(timeout_ms / 1000.0 + 10)
            except socket.timeout:
                self.close()
                raise ControlError("FigCraft n'a pas répondu à temps.")
            except ConnectionError as e:
                raise _Closed(str(e))
            try:
                reply = json.loads(line.decode("utf-8"))
            except ValueError:
                self.close()
                raise ControlError("Réponse illisible de FigCraft.")
            if not isinstance(reply, dict):
                self.close()
                raise ControlError("Réponse inattendue de FigCraft.")
            if "id" in reply and reply["id"] is None and not reply.get("ok"):
                return reply  # a protocol error FigCraft could not tie to a request: ours
            if "id" in reply and reply["id"] != want_id:
                continue  # a stale reply to an earlier request: not ours
            return reply

    def execute(self, command, params=None, timeout_ms=60000):
        """engine.execute {command, params}."""
        return self.request(
            "engine.execute", {"command": command, "params": params or {}}, timeout_ms
        )
