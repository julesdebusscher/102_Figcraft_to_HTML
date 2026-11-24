#!/usr/bin/env python3
"""Minimal client for the FigCraft control channel (stdlib only).

Newline-delimited JSON over 127.0.0.1:<port>: one request object per line,
one reply line per request ({"id", "ok", "result"|"error"}).
See FigCraft docs/control-protocol.md.

Usage:
    python3 tools/fcctl.py smoke <file.figcraft> [--port 7979] [--keep]
    python3 tools/fcctl.py call <method> '<json params>' [--port 7979]
    python3 tools/fcctl.py exec <command> '<json params>' [--port 7979]
"""
import json
import os
import socket
import subprocess
import sys
import time

FIGCRAFT_BIN = "/Applications/FigCraft.app/Contents/MacOS/FigCraft"


class FcError(RuntimeError):
    """A reply with ok:false."""


class Fc:
    def __init__(self, port=7979, host="127.0.0.1"):
        self.port = port
        self.host = host
        self.proc = None
        self._sock = None
        self._buf = b""
        self._next_id = 0

    # -- connection -------------------------------------------------------
    def _connect(self):
        if self._sock is None:
            self._sock = socket.create_connection((self.host, self.port), timeout=5)
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
                raise ConnectionError("FigCraft closed the control connection")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return line

    # -- requests ---------------------------------------------------------
    def request(self, method, params=None, timeout_ms=60000):
        """Send one request; return its result or raise FcError on ok:false."""
        self._next_id += 1
        rid = self._next_id
        msg = {"id": rid, "method": method, "params": params or {}}
        if timeout_ms != 60000:
            msg["timeoutMs"] = int(timeout_ms)
        data = (json.dumps(msg) + "\n").encode("utf-8")
        try:
            sock = self._connect()
            sock.sendall(data)
            line = self._readline(timeout_ms / 1000 + 10)
        except (OSError, ConnectionError):
            # Idle connections are closed after 60 s: reconnect once.
            self.close()
            sock = self._connect()
            sock.sendall(data)
            line = self._readline(timeout_ms / 1000 + 10)
        reply = json.loads(line)
        if not reply.get("ok"):
            raise FcError(f"{method}: {reply.get('error')}")
        return reply.get("result")

    def execute(self, command, params=None, timeout_ms=60000):
        """engine.execute {command, params}."""
        return self.request("engine.execute", {"command": command, "params": params or {}}, timeout_ms)

    # -- app lifecycle ----------------------------------------------------
    @classmethod
    def launch(cls, file=None, port=7979, wait_s=60):
        """Start FigCraft with --control <port> [file] and wait until it answers."""
        fc = cls(port)
        args = [FIGCRAFT_BIN, "--control", str(port)]
        if file:
            args.append(os.path.abspath(file))
        fc.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + wait_s
        last = None
        while time.time() < deadline:
            if fc.proc.poll() is not None:
                raise RuntimeError(f"FigCraft exited with {fc.proc.returncode}")
            try:
                fc.request("document.inspect", {"depth": 0}, timeout_ms=5000)
                return fc
            except (OSError, ConnectionError, FcError, ValueError) as e:
                last = e
                fc.close()
                time.sleep(0.5)
        fc.quit()
        raise TimeoutError(f"FigCraft did not answer on port {port}: {last}")

    def quit(self):
        """Close the app we started (app.quit, then kill if needed)."""
        try:
            self.request("app.quit", {}, timeout_ms=5000)
        except Exception:
            pass
        self.close()
        if self.proc is not None:
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=10)
            self.proc = None


def _arg(argv, flag, default=None):
    if flag in argv:
        i = argv.index(flag)
        val = argv[i + 1] if i + 1 < len(argv) else default
        del argv[i:i + 2]
        return val
    return default


def main(argv):
    argv = list(argv)
    port = int(_arg(argv, "--port", "7979"))
    keep = "--keep" in argv
    if keep:
        argv.remove("--keep")
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "smoke":
        fc = Fc.launch(argv[2], port=port)
        try:
            doc = fc.request("document.inspect", {"depth": 1, "outline": True})
            for page in doc.get("pages", []):
                print(page.get("name"))
        finally:
            if not keep:
                fc.quit()
        return 0
    fc = Fc(port)
    params = json.loads(argv[3]) if len(argv) > 3 else {}
    if cmd == "call":
        out = fc.request(argv[2], params)
    elif cmd == "exec":
        out = fc.execute(argv[2], params)
    else:
        print(__doc__)
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
