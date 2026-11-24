"""In-memory stand-in for figcraft_export.control.Control."""
import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def canonical(params):
    return json.dumps(params or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_fixture(name):
    with open(str(FIXTURES / (name if name.endswith(".json") else name + ".json")), encoding="utf-8") as f:
        return json.load(f)


class FakeControl:
    """replies: {(method_or_command, canonical_params_json): object | Exception}."""

    def __init__(self, replies=None):
        self.replies = dict(replies or {})
        self.calls = []

    def _answer(self, key, label):
        if key not in self.replies:
            raise AssertionError("unexpected call %r" % (key,))
        reply = self.replies[key]
        if isinstance(reply, Exception):
            raise reply
        return reply

    def request(self, method, params=None, timeout_ms=60000):
        self.calls.append((method, params or {}))
        return self._answer((method, canonical(params)), method)

    def execute(self, command, params=None, timeout_ms=60000):
        self.calls.append((command, params or {}))
        return self._answer((command, canonical(params)), command)

    def fixture(self, name):
        return load_fixture(name)

    def close(self):
        pass
