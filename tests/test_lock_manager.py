# -*- coding: iso-8859-1 -*-
# (c) 2009-2017 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""Unit test for lock_manager.py"""
import os
import sys
import unittest
from tempfile import gettempdir
from time import sleep

from wsgidav import lock_manager, lock_storage
from wsgidav.dav_error import DAVError


# ========================================================================
# BasicTest
# ========================================================================


class BasicTest(unittest.TestCase):
    """Test lock_manager.LockManager()."""
    principal = "Joe Tester"
    owner = b'joe.tester@example.com'
    root = "/dav/res"
    timeout = 10 * 60  # Default lock timeout 10 minutes

#     @classmethod
#     def suite(cls):
#         """Return test case suite (so we can control the order)."""
#         suite = TestSuite()
#         suite.addTest(cls("testPreconditions"))
# #        suite.addTest(cls("testOpen"))
#         suite.addTest(cls("testValidation"))
#         suite.addTest(cls("testLock"))
#         suite.addTest(cls("testTimeout"))
#         suite.addTest(cls("testConflict"))
#         return suite

    def setUp(self):
        storage = lock_storage.LockStorageDict()
        self.lm = lock_manager.LockManager(storage)
        self.lm._verbose = 1

    def tearDown(self):
        del self.lm

    def _acquire(self, url, locktype, lockscope, lockdepth, lockowner, timeout,
                 principal, tokenList):
        """Wrapper for lm.acquire, that returns None instead of raising DAVError."""
        try:
            return self.lm.acquire(url, locktype, lockscope, lockdepth, lockowner,
                                   timeout, principal, tokenList)
        except DAVError:
            return None

    def _isLockDict(self, o):
        try:
            _ = o["root"]
        except:
            return False
        return True

    def _isLockResultOK(self, resultTupleList):
        """Return True, if result is [ (lockDict, None) ]."""
        try:
            return (len(resultTupleList) == 1
                    and len(resultTupleList) == 2
                    and self._isLockDict(resultTupleList[0][0])
                    and resultTupleList[0][1] is None)
        except:
            return False

    def _isLockResultFault(self, lock, conflictList, status=None):
        """Return True, if it is a valid result tuple containing a DAVError."""
        try:
            if lock is not None:
                return False
            if len(conflictList) < 1:
                return False
            resultTuple = conflictList[0]
            if len(resultTuple) != 2 or not self._isLockDict(resultTuple[0]) or not isinstance(resultTuple[1], DAVError):
                return False
            elif status and status != DAVError.value:
                return False
            return True
        except:
            return False

    def testPreconditions(self):
        """Environment must be set."""
        self.assertTrue(
            __debug__, "__debug__ must be True, otherwise asserts are ignored")


#    def testOpen(self):
#        """Lock manager should be lazy opening on first access."""
#        lm = self.lm
##        assert not lm._loaded, "LM must only be opened after first access"
#        lm._generateLock(self.principal, "write", "exclusive", "infinity",
#                        self.owner,
#                        "/dav",
#                        10)
#        assert lm._loaded, "LM must be opened after first access"

    def testValidation(self):
        """Lock manager should raise errors on bad args."""
        lm = self.lm
        self.assertRaises(AssertionError,
                          lm._generateLock, lm, "writeX", "exclusive", "infinity",
                          self.owner, self.root, self.timeout)
        self.assertRaises(AssertionError,
                          lm._generateLock, lm, "write", "exclusiveX", "infinity",
                          self.owner, self.root, self.timeout)
        self.assertRaises(AssertionError,
                          lm._generateLock, lm, "write", "exclusive", "infinityX",
                          self.owner, self.root, self.timeout)
        self.assertRaises(AssertionError,
                          lm._generateLock, lm, "write", "exclusive", "infinity",
                          None, self.root, self.timeout)
        self.assertRaises(AssertionError,
                          lm._generateLock, lm, "write", "exclusive", "infinity",
                          self.owner, None, self.timeout)

#        assert lm._dict is None, "No locks should have been created by this test"

    def testLock(self):
        """Lock manager should create and find locks."""
        lm = self.lm
        url = "/dav/res"
        # Create a new lock
        lockDict = lm._generateLock(self.principal, "write", "exclusive", "infinity",
                                    self.owner, url, self.timeout)
        # Check returned dictionary
        assert lockDict is not None
        assert lockDict["root"] == url
        assert lockDict["type"] == "write"
        assert lockDict["scope"] == "exclusive"
        assert lockDict["depth"] == "infinity"
        assert lockDict["owner"] == self.owner
        assert lockDict["principal"] == self.principal

        # Test lookup
        tok = lockDict.get("token")
        assert lm.getLock(tok, "root") == url

        lockDict = lm.getLock(tok)

        assert lockDict is not None
        assert lockDict["root"] == url
        assert lockDict["type"] == "write"
        assert lockDict["scope"] == "exclusive"
        assert lockDict["depth"] == "infinity"
        assert lockDict["owner"] == self.owner
        assert lockDict["principal"] == self.principal

        # We locked "/dav/res", did we?
        assert lm.isTokenLockedByUser(tok, self.principal)

#        res = lm.getUrlLockList(url, self.principal)
        res = lm.getUrlLockList(url)
        self.assertEqual(len(res), 1)

#        res = lm.getUrlLockList(url, "another user")
#        assert len(res) == 0

        assert lm.isUrlLockedByToken(
            "/dav/res", tok), "url not directly locked by locktoken."
        assert lm.isUrlLockedByToken(
            "/dav/res/", tok), "url not directly locked by locktoken."
        assert lm.isUrlLockedByToken(
            "/dav/res/sub", tok), "child url not indirectly locked"

        assert not lm.isUrlLockedByToken(
            "/dav/ressub", tok), "non-child url reported as locked"
        assert not lm.isUrlLockedByToken(
            "/dav", tok), "parent url reported as locked"
        assert not lm.isUrlLockedByToken(
            "/dav/", tok), "parent url reported as locked"

    def testTimeout(self):
        """Locks should be purged after expiration date."""
        lm = self.lm
        timeout = 1
        lockDict = lm._generateLock(self.principal, "write", "exclusive", "infinity",
                                    self.owner, self.root, timeout)

        assert lockDict is not None
        tok = lockDict.get("token")
        assert lm.getLock(tok, "root") == self.root

        sleep(timeout - 0.5)
        lockDict = lm.getLock(tok)
        assert lockDict is not None, "Lock expired too early"

        sleep(1)
        lockDict = lm.getLock(tok)
        assert lockDict is None, "Lock has not expired"

    def testConflict(self):
        """Locks should prevent conflicts."""
        tokenList = []

        # Create a lock for '/dav/res/'
        l = self._acquire("/dav/res/", "write", "exclusive", "infinity",
                          self.owner, self.timeout,
                          self.principal, tokenList)
        assert l, "Could not acquire lock"

        # Try to lock with a slightly different URL (without trailing '/')
        l = self._acquire("/dav/res", "write", "exclusive", "infinity",
                          self.owner, self.timeout,
                          "another principal", tokenList)
        assert l is None, "Could acquire a conflicting lock"

        # Try to lock with another principal
        l = self._acquire("/dav/res/", "write", "exclusive", "infinity",
                          self.owner, self.timeout, "another principal", tokenList)
        assert l is None, "Could acquire a conflicting lock"

        # Try to lock child with another principal
        l = self._acquire("/dav/res/sub", "write", "exclusive", "infinity",
                          self.owner, self.timeout, "another principal", tokenList)
        assert l is None, "Could acquire a conflicting child lock"

        # Try to lock parent with same principal
        l = self._acquire("/dav/", "write", "exclusive", "infinity",
                          self.owner, self.timeout, self.principal, tokenList)
        assert l is None, "Could acquire a conflicting parent lock"

        # Try to lock child with same principal
        l = self._acquire("/dav/res/sub", "write", "exclusive", "infinity",
                          self.owner, self.timeout, self.principal, tokenList)
        assert l is None, "Could acquire a conflicting child lock (same principal)"


# ========================================================================
# ShelveTest
# ========================================================================
class ShelveTest(BasicTest):
    """Test lock_manager.ShelveLockManager()."""

    def setUp(self):
        if sys.version_info < (3, 0):
            modifier = "-py2"  # shelve formats are incompatible
        else:
            modifier = "-py3"
        self.path = os.path.join(
            gettempdir(), "wsgidav-locks%s.shelve" % modifier)
        storage = lock_storage.LockStorageShelve(self.path)
        self.lm = lock_manager.LockManager(storage)
        self.lm._verbose = 2

    def tearDown(self):
        self.lm.storage.clear()
        self.lm = None
        # Note: os.remove(self.path) does not work, because Shelve may append
        # a file extension.
#         if os.path.exists(self.path):
#             os.remove(self.path)


# ========================================================================
# suite
# ========================================================================
# def suite():
#     """Return suites of all test cases."""
#     return TestSuite([BasicTest.suite(),
#                       ShelveTest.suite(),
#                       ])


if __name__ == "__main__":
    unittest.main()
#     suite = suite()
#     TextTestRunner(descriptions=0, verbosity=2).run(suite)
