# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Implements two storage providers for `LockManager`.

Two alternative lock storage classes are defined here: one in-memory
(dict-based), and one persistent low performance variant using shelve.

See :class:`~wsgidav.lock_manager.LockManager`
"""
from wsgidav import compat, util
from wsgidav.lock_manager import (
    generate_lock_token,
    lock_string,
    normalize_lock_root,
    validate_lock,
)
from wsgidav.rw_lock import ReadWriteLock

import os
import shelve
import time


__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)

# TODO: comment's from Ian Bicking (2005)
# @@: Use of shelve means this is only really useful in a threaded environment.
#    And if you have just a single-process threaded environment, you could get
#    nearly the same effect with a dictionary of threading.Lock() objects.  Of course,
#    it would be better to move off shelve anyway, probably to a system with
#    a directory of per-file locks, using the file locking primitives (which,
#    sadly, are not quite portable).
# @@: It would probably be easy to store the properties as pickle objects
# in a parallel directory structure to the files you are describing.
# Pickle is expedient, but later you could use something more readable
# (pickles aren't particularly readable)


# ========================================================================
# LockStorageDict
# ========================================================================
class LockStorageDict(object):
    """
    An in-memory lock manager storage implementation using a dictionary.

    R/W access is guarded by a thread.lock object.

    Also, to make it work with a Shelve dictionary, modifying dictionary
    members is done by re-assignment and we call a _flush() method.

    This is obviously not persistent, but should be enough in some cases.
    For a persistent implementation, see lock_manager.LockStorageShelve().

    Notes:
        expire is stored as expiration date in seconds since epoch (not in
        seconds until expiration).

    The dictionary is built like::

        { 'URL2TOKEN:/temp/litmus/lockme': ['opaquelocktoken:0x1d7b86...',
                                            'opaquelocktoken:0xd7d4c0...'],
          'opaquelocktoken:0x1d7b86...': {
            'depth': '0',
            'owner': "<?xml version=\'1.0\' encoding=\'UTF-8\'?>\\n<owner xmlns="DAV:">"
                + "litmus test suite</owner>\\n",
            'principal': 'tester',
            'root': '/temp/litmus/lockme',
            'scope': 'shared',
            'expire': 1261328382.4530001,
            'token': 'opaquelocktoken:0x1d7b86...',
            'type': 'write',
            },
          'opaquelocktoken:0xd7d4c0...': {
            'depth': '0',
            'owner': '<?xml version=\'1.0\' encoding=\'UTF-8\'?>\\n<owner xmlns="DAV:">'
                + 'litmus: notowner_sharedlock</owner>\\n',
            'principal': 'tester',
            'root': '/temp/litmus/lockme',
            'scope': 'shared',
            'expire': 1261328381.6040001,
            'token': 'opaquelocktoken:0xd7d4c0...',
            'type': 'write'
           },
         }
    """  # noqa

    LOCK_TIME_OUT_DEFAULT = 604800  # 1 week, in seconds
    LOCK_TIME_OUT_MAX = 4 * 604800  # 1 month, in seconds

    def __init__(self):
        self._dict = None
        self._lock = ReadWriteLock()

    def __repr__(self):
        return self.__class__.__name__

    def __del__(self):
        pass

    def _flush(self):
        """Overloaded by Shelve implementation."""
        pass

    def open(self):
        """Called before first use.

        May be implemented to initialize a storage.
        """
        assert self._dict is None
        self._dict = {}

    def close(self):
        """Called on shutdown."""
        self._dict = None

    def cleanup(self):
        """Purge expired locks (optional)."""
        pass

    def clear(self):
        """Delete all entries."""
        if self._dict is not None:
            self._dict.clear()

    def get(self, token):
        """Return a lock dictionary for a token.

        If the lock does not exist or is expired, None is returned.

        token:
            lock token
        Returns:
            Lock dictionary or <None>

        Side effect: if lock is expired, it will be purged and None is returned.
        """
        self._lock.acquire_read()
        try:
            lock = self._dict.get(token)
            if lock is None:
                # Lock not found: purge dangling URL2TOKEN entries
                _logger.debug("Lock purged dangling: {}".format(token))
                self.delete(token)
                return None
            expire = float(lock["expire"])
            if expire >= 0 and expire < time.time():
                _logger.debug(
                    "Lock timed-out({}): {}".format(expire, lock_string(lock))
                )
                self.delete(token)
                return None
            return lock
        finally:
            self._lock.release()

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
        self._lock.acquire_write()
        try:
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
                timeout = LockStorageDict.LOCK_TIME_OUT_DEFAULT
            elif timeout < 0 or timeout > LockStorageDict.LOCK_TIME_OUT_MAX:
                timeout = LockStorageDict.LOCK_TIME_OUT_MAX

            lock["timeout"] = timeout
            lock["expire"] = time.time() + timeout

            validate_lock(lock)

            token = generate_lock_token()
            lock["token"] = token

            # Store lock
            self._dict[token] = lock

            # Store locked path reference
            key = "URL2TOKEN:{}".format(path)
            if key not in self._dict:
                self._dict[key] = [token]
            else:
                # Note: Shelve dictionary returns copies, so we must reassign
                # values:
                tokList = self._dict[key]
                tokList.append(token)
                self._dict[key] = tokList
            self._flush()
            _logger.debug(
                "LockStorageDict.set({!r}): {}".format(org_path, lock_string(lock))
            )
            return lock
        finally:
            self._lock.release()

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
        assert token in self._dict, "Lock must exist"
        assert timeout == -1 or timeout > 0
        if timeout < 0 or timeout > LockStorageDict.LOCK_TIME_OUT_MAX:
            timeout = LockStorageDict.LOCK_TIME_OUT_MAX

        self._lock.acquire_write()
        try:
            # Note: shelve dictionary returns copies, so we must reassign
            # values:
            lock = self._dict[token]
            lock["timeout"] = timeout
            lock["expire"] = time.time() + timeout
            self._dict[token] = lock
            self._flush()
        finally:
            self._lock.release()
        return lock

    def delete(self, token):
        """Delete lock.

        Returns True on success. False, if token does not exist, or is expired.
        """
        self._lock.acquire_write()
        try:
            lock = self._dict.get(token)
            _logger.debug("delete {}".format(lock_string(lock)))
            if lock is None:
                return False
            # Remove url to lock mapping
            key = "URL2TOKEN:{}".format(lock.get("root"))
            if key in self._dict:
                # _logger.debug("    delete token {} from url {}".format(token, lock.get("root")))
                tokList = self._dict[key]
                if len(tokList) > 1:
                    # Note: shelve dictionary returns copies, so we must
                    # reassign values:
                    tokList.remove(token)
                    self._dict[key] = tokList
                else:
                    del self._dict[key]
            # Remove the lock
            del self._dict[token]

            self._flush()
        finally:
            self._lock.release()
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
            for token in toklist:
                lock = self.get(token)
                if lock:
                    if token_only:
                        lockList.append(lock["token"])
                    else:
                        lockList.append(lock)

        path = normalize_lock_root(path)
        self._lock.acquire_read()
        try:
            key = "URL2TOKEN:{}".format(path)
            tokList = self._dict.get(key, [])
            lockList = []
            if include_root:
                __appendLocks(tokList)

            if include_children:
                for u, ltoks in self._dict.items():
                    if util.is_child_uri(key, u):
                        __appendLocks(ltoks)

            return lockList
        finally:
            self._lock.release()


# ========================================================================
# LockStorageShelve
# ========================================================================


class LockStorageShelve(LockStorageDict):
    """
    A low performance lock manager implementation using shelve.
    """

    def __init__(self, storage_path):
        super(LockStorageShelve, self).__init__()
        self._storage_path = os.path.abspath(storage_path)

    def __repr__(self):
        return "LockStorageShelve({!r})".format(self._storage_path)

    def _flush(self):
        """Write persistent dictionary to disc."""
        _logger.debug("_flush()")
        self._lock.acquire_write()  # TODO: read access is enough?
        try:
            self._dict.sync()
        finally:
            self._lock.release()

    def clear(self):
        """Delete all entries."""
        self._lock.acquire_write()  # TODO: read access is enough?
        try:
            was_closed = self._dict is None
            if was_closed:
                self.open()
            if len(self._dict):
                self._dict.clear()
                self._dict.sync()
            if was_closed:
                self.close()
        finally:
            self._lock.release()

    def open(self):
        _logger.debug("open({!r})".format(self._storage_path))
        # Open with writeback=False, which is faster, but we have to be
        # careful to re-assign values to _dict after modifying them
        self._dict = shelve.open(self._storage_path, writeback=False)

    #        if __debug__ and self._verbose >= 2:
    #                self._check("After shelve.open()")
    #            self._dump("After shelve.open()")

    def close(self):
        _logger.debug("close()")
        self._lock.acquire_write()
        try:
            if self._dict is not None:
                self._dict.close()
                self._dict = None
        finally:
            self._lock.release()
