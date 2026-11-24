import json
import socket
import threading
import time
from unittest import mock
import unittest

from figcraft_export.control import Control, ControlError, Unreachable
from tests.fake_control import FakeControl, canonical


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Server(threading.Thread):
    def __init__(self, handler):
        threading.Thread.__init__(self, daemon=True)
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.handler = handler
        self.seen = []

    def run(self):
        conn, _ = self.sock.accept()
        f = conn.makefile("rwb")
        for line in f:
            req = json.loads(line)
            self.seen.append(req)
            f.write((json.dumps(self.handler(req)) + "\n").encode("utf-8"))
            f.flush()
        conn.close()
        self.sock.close()


class ControlTests(unittest.TestCase):
    def test_unreachable_port_raises_unreachable(self):
        with self.assertRaises(Unreachable):
            Control(free_port()).request("document.inspect")

    def test_error_reply_raises_control_error_with_message(self):
        srv = Server(lambda r: {"id": r["id"], "ok": False, "error": "unknown method `x`"})
        srv.start()
        c = Control(srv.port)
        with self.assertRaises(ControlError) as cm:
            c.request("x")
        self.assertIn("unknown method", str(cm.exception))
        c.close()

    def test_request_ids_increment_and_replies_match(self):
        srv = Server(lambda r: {"id": r["id"], "ok": True, "result": r["method"]})
        srv.start()
        c = Control(srv.port)
        self.assertEqual(c.request("a"), "a")
        self.assertEqual(c.execute("b", {"k": 1}), "engine.execute")
        self.assertEqual([r["id"] for r in srv.seen], [1, 2])
        self.assertEqual(srv.seen[1]["params"], {"command": "b", "params": {"k": 1}})
        c.close()

    def test_timeout_is_not_retried(self):
        sent = []

        def silent(srv):
            conn, _ = srv.accept()
            f = conn.makefile("rb")
            sent.append(f.readline())
            time.sleep(3)
            f.close()
            conn.close()

        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(2)
        t = threading.Thread(target=silent, args=(srv,), daemon=True)
        t.start()
        c = Control(srv.getsockname()[1])
        with mock.patch.object(Control, "_readline", side_effect=socket.timeout()):
            with self.assertRaises(ControlError):
                c.request("node.set", {"x": 1}, timeout_ms=100)
        t.join()
        self.assertEqual(len(sent), 1)
        c.close()
        srv.close()

    def test_garbage_reply_raises_control_error(self):
        for garbage in (b"not json\n", b"\xff\xfe\n", b"[1,2]\n"):
            srv = socket.socket()
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)

            def serve(srv=srv, garbage=garbage):
                conn, _ = srv.accept()
                with conn.makefile("rb") as rf:
                    rf.readline()
                conn.sendall(garbage)
                conn.close()

            threading.Thread(target=serve, daemon=True).start()
            c = Control(srv.getsockname()[1])
            with self.assertRaises(ControlError):
                c.request("x")
            c.close()
            srv.close()

    def test_interrupt_mid_read_reconnects_and_next_reply_is_its_own(self):
        conns = []
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(4)

        def handle(conn):
            f = conn.makefile("rwb")
            try:
                for line in f:
                    req = json.loads(line)
                    if req["method"] == "slow":
                        time.sleep(0.3)   # answered after the client gave up on it
                    f.write((json.dumps({"id": req["id"], "ok": True, "result": req["method"]}) + "\n").encode("utf-8"))
                    f.flush()
            except OSError:
                pass                       # the client abandoned this socket
            finally:
                try:
                    f.close()
                except OSError:
                    pass

        def serve():
            while True:
                try:
                    conn, _ = srv.accept()
                except OSError:
                    return
                conns.append(conn)
                threading.Thread(target=handle, args=(conn,), daemon=True).start()

        threading.Thread(target=serve, daemon=True).start()
        c = Control(srv.getsockname()[1])
        real = Control._readline
        with mock.patch.object(Control, "_readline", side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                c.request("slow")
        time.sleep(0.5)                       # the stale "slow" reply is now waiting on the old socket
        self.assertIs(Control._readline, real)
        self.assertEqual(c.request("fresh"), "fresh")
        self.assertEqual(len(conns), 2)       # a new connection after the interrupt
        c.close()
        srv.close()
        for conn in conns:
            conn.close()

    def test_reply_with_another_id_is_discarded(self):
        def handler(r):
            return [{"id": r["id"] + 100, "ok": True, "result": "stale"}, {"id": r["id"], "ok": True, "result": "mine"}]

        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)

        def serve():
            conn, _ = srv.accept()
            f = conn.makefile("rwb")
            try:
                for line in f:
                    for rep in handler(json.loads(line)):
                        f.write((json.dumps(rep) + "\n").encode("utf-8"))
                    f.flush()
            except OSError:
                pass
            finally:
                f.close()
                conn.close()

        threading.Thread(target=serve, daemon=True).start()
        c = Control(srv.getsockname()[1])
        self.assertEqual(c.request("a"), "mine")
        self.assertEqual(c.request("b"), "mine")
        c.close()
        srv.close()

    def test_null_id_error_reply_raises_control_error_at_once(self):
        srv = Server(lambda r: {"id": None, "ok": False, "error": "invalid request"})
        srv.start()
        c = Control(srv.port)
        t0 = time.time()
        with self.assertRaises(ControlError) as cm:
            c.request("x", timeout_ms=2000)
        self.assertIn("invalid request", str(cm.exception))
        self.assertLess(time.time() - t0, 1.5)
        c.close()

    def test_fake_control_replies_and_records(self):
        fake = FakeControl({("node.get", canonical({"id": 2})): {"id": 2}})
        self.assertEqual(fake.request("node.get", {"id": 2}), {"id": 2})
        self.assertEqual(fake.calls, [("node.get", {"id": 2})])


if __name__ == "__main__":
    unittest.main()
