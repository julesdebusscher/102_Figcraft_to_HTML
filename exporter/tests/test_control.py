import json
import socket
import threading
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

    def test_fake_control_replies_and_records(self):
        fake = FakeControl({("node.get", canonical({"id": 2})): {"id": 2}})
        self.assertEqual(fake.request("node.get", {"id": 2}), {"id": 2})
        self.assertEqual(fake.calls, [("node.get", {"id": 2})])


if __name__ == "__main__":
    unittest.main()
