# -*- coding: iso-8859-1 -*-
# (c) 2009-2017 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""Unit tests for wsgidav.util"""

# from unittest import TestCase, TestSuite, TextTestRunner
import unittest

from wsgidav.util import (
    isChildUri,
    isEqualOrChildUri,
    joinUri,
    lstripstr,
    popPath,
    shiftPath
)


class BasicTest(unittest.TestCase):
    """Test ."""

#     @classmethod
#     def suite(cls):
#         """Return test case suite (so we can control the order)."""
#         suite = TestSuite()
#         suite.addTest(cls("testPreconditions"))
#         suite.addTest(cls("testBasics"))
#         return suite

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testPreconditions(self):
        """Environment must be set."""
        self.assertTrue(
            __debug__, "__debug__ must be True, otherwise asserts are ignored")

    def testBasics(self):
        """Test basic tool functions."""
        assert joinUri("/a/b", "c") == "/a/b/c"
        assert joinUri("/a/b/", "c") == "/a/b/c"
        assert joinUri("/a/b", "c", "d") == "/a/b/c/d"
        assert joinUri("a/b", "c", "d") == "a/b/c/d"
        assert joinUri("/", "c") == "/c"
        assert joinUri("", "c") == "/c"

        assert not isChildUri("/a/b", "/a/")
        assert not isChildUri("/a/b", "/a/b")
        assert not isChildUri("/a/b", "/a/b/")
        assert not isChildUri("/a/b", "/a/bc")
        assert not isChildUri("/a/b", "/a/bc/")
        assert isChildUri("/a/b", "/a/b/c")
        assert isChildUri("/a/b", "/a/b/c")

        assert not isEqualOrChildUri("/a/b", "/a/")
        assert isEqualOrChildUri("/a/b", "/a/b")
        assert isEqualOrChildUri("/a/b", "/a/b/")
        assert not isEqualOrChildUri("/a/b", "/a/bc")
        assert not isEqualOrChildUri("/a/b", "/a/bc/")
        assert isEqualOrChildUri("/a/b", "/a/b/c")
        assert isEqualOrChildUri("/a/b", "/a/b/c")

        assert lstripstr("/dav/a/b", "/dav") == "/a/b"
        assert lstripstr("/dav/a/b", "/DAV") == "/dav/a/b"
        assert lstripstr("/dav/a/b", "/DAV", True) == "/a/b"

        assert popPath("/a/b/c") == ("a", "/b/c")
        assert popPath("/a/b/") == ("a", "/b/")
        assert popPath("/a/") == ("a", "/")
        assert popPath("/a") == ("a", "/")
        assert popPath("/") == ("", "")
        assert popPath("") == ("", "")

        self.assertEqual(shiftPath("", "/a/b/c"),
                         ("a", "/a", "/b/c"))
        self.assertEqual(shiftPath("/a", "/b/c"),
                         ("b", "/a/b", "/c"))
        self.assertEqual(shiftPath("/a/b", "/c"),
                         ("c", "/a/b/c", ""))
        self.assertEqual(shiftPath("/a/b/c", "/"),
                         ("", "/a/b/c", ""))
        self.assertEqual(shiftPath("/a/b/c", ""),
                         ("", "/a/b/c", ""))


# ========================================================================
# suite
# ========================================================================
# def suite():
#     """Return suites of all test cases."""
#     return TestSuite([BasicTest.suite(),
#                       ])


if __name__ == "__main__":
    unittest.main()
#     suite = suite()
#     TextTestRunner(descriptions=0, verbosity=2).run(suite)
