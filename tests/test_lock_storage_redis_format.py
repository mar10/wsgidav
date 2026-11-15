# (c) 2009-2026 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
LockStorageRedis must not use pickle to store locks (CWE-502).

These tests use an in-memory stand-in for the redis client, so they also run
when neither the `redis` package nor a Redis server is available.
"""

import fnmatch
import importlib
import pickle
import sys
import unittest
from unittest.mock import MagicMock, patch


class FakeRedis:
    def __init__(self, **kwargs):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value.encode() if isinstance(value, str) else value

    def delete(self, key):
        self.data.pop(key, None)

    def exists(self, key):
        return key in self.data

    def lpush(self, key, value):
        self.data.setdefault(key, []).insert(0, value.encode())

    def lrem(self, key, count, value):
        if value.encode() in self.data.get(key, []):
            self.data[key].remove(value.encode())

    def lrange(self, key, start, end):
        return list(self.data.get(key, []))

    def keys(self, pattern):
        return [k.encode() for k in self.data if fnmatch.fnmatchcase(k, pattern)]


class RedisLockFormatTest(unittest.TestCase):
    def setUp(self):
        fake_module = MagicMock()
        fake_module.Redis = FakeRedis
        name = "wsgidav.lock_man.lock_storage_redis"
        with patch.dict(sys.modules, {"redis": fake_module}):
            sys.modules.pop(name, None)
            self.mod = importlib.import_module(name)
        self.addCleanup(sys.modules.pop, name, None)
        self.storage = self.mod.LockStorageRedis()
        self.storage.open()

    def _lock(self):
        return {
            "type": "write",
            "scope": "exclusive",
            "depth": "0",
            "owner": b"<D:href>\xc3\xa4 owner</D:href>",
            "timeout": 100,
            "principal": "joe",
        }

    def test_roundtrip(self):
        lock = self._lock()
        lock.update({"root": "/a/b", "token": "opaquelocktoken:0x1", "expire": 1.5})
        data = self.mod.dump_lock(lock)
        assert isinstance(data, str)
        assert self.mod.load_lock(data) == lock
        assert self.mod.load_lock(data.encode()) == lock

    def test_storage_does_not_pickle(self):
        lock = self.storage.create("/a/b", self._lock())
        token = lock["token"]
        raw = self.storage._redis.get(f"wsgidav-lock:{token}")
        assert raw.startswith(b"{"), raw

        assert self.storage.get(token) == lock
        assert self.storage.get(token)["owner"] == self._lock()["owner"]
        assert self.storage.get_lock_list(
            "/a/b", include_root=True, include_children=False, token_only=True
        ) == [token]
        assert self.storage.get_lock_list(
            "/a", include_root=False, include_children=True, token_only=False
        ) == [lock]

        assert self.storage.refresh(token, timeout=200)["timeout"] == 200
        assert self.storage.delete(token) is True
        assert self.storage.get(token) is None

    def test_pickled_entries_are_not_loaded(self):
        """An entry that is not JSON must be ignored, never unpickled."""

        class Canary:
            def __reduce__(self):
                return (exec, ("raise SystemExit('unpickled!')",))

        key = "wsgidav-lock:opaquelocktoken:0xbad"
        for payload in (pickle.dumps(Canary()), pickle.dumps(self._lock()), b"[1]"):
            self.storage._redis.data[key] = payload
            assert self.mod.load_lock(payload) is None
            assert self.storage.get("opaquelocktoken:0xbad") is None
            assert key not in self.storage._redis.data, "invalid entry is dropped"


if __name__ == "__main__":
    unittest.main()
