# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
from wsgidav import compat, util
from wsgidav.lock_manager import (
    generate_lock_token,
    lock_string,
    normalize_lock_root,
    validate_lock,
)

import pickle
import redis
import time


_logger = util.get_module_logger(__name__)


class LockStorageRedis(object):
    """
    A (high performance?) lock manager implementation using redis!
    """

    def __init__(self, host="127.0.0.1", port=6379, db=0):
        super(LockStorageRedis, self).__init__()
        self._redis_host = host
        self._redis_port = port
        self._redis_db = db
        self._redis_prefix = "wsgidav-{}"
        self._redis_lock_prefix = self._redis_prefix.format("lock:{}")
        self._redis_url2token_prefix = self._redis_prefix.format("URL2TOKEN:{}")
        self._redis = None

    LOCK_TIME_OUT_DEFAULT = 604800  # 1 week, in seconds
    LOCK_TIME_OUT_MAX = 4 * 604800  # 1 month, in seconds

    def __repr__(self):
        return self.__class__.__name__

    def __del__(self):
        pass

    def _flush(self):
        """Overloaded by Shelve implementation."""

    def open(self):
        """Called before first use.
        May be implemented to initialize a storage.
        """
        assert self._redis is None
        self._redis = redis.Redis(
            host=self._redis_host, port=self._redis_port, db=self._redis_db
        )

    def close(self):
        """Called on shutdown."""
        self._redis = None

    def cleanup(self):
        """Purge expired locks (optional)."""

    def clear(self):
        """Delete all entries."""
        if self._redis is not None:
            keys = self._redis.keys(self._redis_prefix.format("*"))
            for key in keys:
                self._redis.delete(key)

    def get(self, token):
        """Return a lock dictionary for a token.
        If the lock does not exist or is expired, None is returned.
        token:
            lock token
        Returns:
            Lock dictionary or <None>
        Side effect: if lock is expired, it will be purged and None is returned.
        """
        lock = self._redis.get(self._redis_lock_prefix.format(token))
        if lock is None:
            # Lock not found: purge dangling URL2TOKEN entries
            _logger.debug("Lock purged dangling: {}".format(token))
            self.delete(token)
            return None
        lock = pickle.loads(lock)
        expire = float(lock["expire"])
        if 0 <= expire < time.time():
            _logger.debug("Lock timed-out({}): {}".format(expire, lock_string(lock)))
            self.delete(token)
            return None
        return lock

    def create(self, path, lock):
        """Create a direct lock for a resource path.
        path:
            Normalized path (utf8 encoded string, no trailing '/')
        lock:
            lock dictionary, without a token entry
        Returns:
            New unique lock token.: <lock
        **Note:** the lock dictionary may be modified on return:
        - lock['root'] is ignored and set to the normalized <path>
        - lock['timeout'] may be normalized and shorter than requested
        - lock['token'] is added
        """
        # We expect only a lock definition, not an existing lock
        assert lock.get("token") is None
        assert lock.get("expire") is None, "Use timeout instead of expire"
        assert path and "/" in path

        # Normalize root: /foo/bar
        org_path = path
        path = normalize_lock_root(path)
        lock["root"] = path

        # Normalize timeout from ttl to expire-date
        timeout = float(lock.get("timeout"))
        if timeout is None:
            timeout = LockStorageRedis.LOCK_TIME_OUT_DEFAULT
        elif timeout < 0 or timeout > LockStorageRedis.LOCK_TIME_OUT_MAX:
            timeout = LockStorageRedis.LOCK_TIME_OUT_MAX

        lock["timeout"] = timeout
        lock["expire"] = time.time() + timeout

        validate_lock(lock)

        token = generate_lock_token()
        lock["token"] = token

        # Store lock
        self._redis.set(
            self._redis_lock_prefix.format(token), pickle.dumps(lock), ex=int(timeout)
        )

        # Store locked path reference
        key = self._redis_url2token_prefix.format(path)
        if not self._redis.exists(key):
            self._redis.lpush(key, token)
        else:
            self._redis.lpush(key, token)
        self._flush()
        _logger.debug(
            "LockStorageRedis.set({!r}): {}".format(org_path, lock_string(lock))
        )
        return lock

    def refresh(self, token, timeout):
        """Modify an existing lock's timeout.
        token:
            Valid lock token.
        timeout:
            Suggested lifetime in seconds (-1 for infinite).
            The real expiration time may be shorter than requested!
        Returns:
            Lock dictionary.
            Raises ValueError, if token is invalid.
        """
        assert self._redis.exists(self._redis_lock_prefix.format(token))
        assert timeout == -1 or timeout > 0
        if timeout < 0 or timeout > LockStorageRedis.LOCK_TIME_OUT_MAX:
            timeout = LockStorageRedis.LOCK_TIME_OUT_MAX

        # Note: shelve dictionary returns copies, so we must reassign
        # values:
        lock = pickle.loads(self._redis.get(self._redis_lock_prefix.format(token)))
        lock["timeout"] = timeout
        lock["expire"] = time.time() + timeout
        self._redis.set(
            self._redis_lock_prefix.format(token), pickle.dumps(lock), ex=int(timeout)
        )
        self._flush()
        return lock

    def delete(self, token):
        """Delete lock.
        Returns True on success. False, if token does not exist, or is expired.
        """
        lock = self._redis.get(self._redis_lock_prefix.format(token))
        if lock is None:
            return False
        lock = pickle.loads(lock)
        _logger.debug("delete {}".format(lock_string(lock)))
        # Remove url to lock mapping
        key = self._redis_url2token_prefix.format(lock.get("root"))
        self._redis.lrem(key, 1, token)
        self._redis.delete(self._redis_lock_prefix.format(token))
        self._flush()
        return True

    def get_lock_list(self, path, include_root, include_children, token_only):
        """Return a list of direct locks for <path>.
        Expired locks are *not* returned (but may be purged).
        path:
            Normalized path (utf8 encoded string, no trailing '/')
        include_root:
            False: don't add <path> lock (only makes sense, when include_children
            is True).
        include_children:
            True: Also check all sub-paths for existing locks.
        token_only:
            True: only a list of token is returned. This may be implemented
            more efficiently by some providers.
        Returns:
            List of valid lock dictionaries (may be empty).
        """
        assert compat.is_native(path)
        assert path and path.startswith("/")
        assert include_root or include_children

        def __appendLocks(toklist):
            # Since we can do this quickly, we use self.get() even if
            # token_only is set, so expired locks are purged.
            for token in map(lambda x: x.decode("utf-8"), toklist):
                lock = self._redis.get(self._redis_lock_prefix.format(token))
                if lock:
                    lock = pickle.loads(lock)
                    if token_only:
                        lockList.append(lock["token"])
                    else:
                        lockList.append(lock)

        path = normalize_lock_root(path)
        key = self._redis_url2token_prefix.format(path)

        tokList = self._redis.lrange(key, 0, -1)
        lockList = []
        if include_root:
            __appendLocks(tokList)

        if include_children:
            for u in map(lambda x: x.decode("utf-8"), self._redis.keys(key + "/*")):
                if util.is_child_uri(key, u):
                    __appendLocks(self._redis.lrange(u, 0, -1))
        return lockList
