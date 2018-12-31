# -*- coding: utf-8 -*-
# (c) 2009-2019 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""Unit tests for wsgidav.util"""
from __future__ import print_function
from wsgidav.compat import StringIO
from wsgidav.util import (
    BASE_LOGGER_NAME,
    get_module_logger,
    init_logging,
    is_child_uri,
    is_equal_or_child_uri,
    join_uri,
    lstripstr,
    pop_path,
    shift_path,
)

import logging
import logging.handlers
import unittest


class BasicTest(unittest.TestCase):
    """Test ."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testPreconditions(self):
        """Environment must be set."""
        self.assertTrue(
            __debug__, "__debug__ must be True, otherwise asserts are ignored"
        )

    def testBasics(self):
        """Test basic tool functions."""
        assert join_uri("/a/b", "c") == "/a/b/c"
        assert join_uri("/a/b/", "c") == "/a/b/c"
        assert join_uri("/a/b", "c", "d") == "/a/b/c/d"
        assert join_uri("a/b", "c", "d") == "a/b/c/d"
        assert join_uri("/", "c") == "/c"
        assert join_uri("", "c") == "/c"

        assert not is_child_uri("/a/b", "/a/")
        assert not is_child_uri("/a/b", "/a/b")
        assert not is_child_uri("/a/b", "/a/b/")
        assert not is_child_uri("/a/b", "/a/bc")
        assert not is_child_uri("/a/b", "/a/bc/")
        assert is_child_uri("/a/b", "/a/b/c")
        assert is_child_uri("/a/b", "/a/b/c")

        assert not is_equal_or_child_uri("/a/b", "/a/")
        assert is_equal_or_child_uri("/a/b", "/a/b")
        assert is_equal_or_child_uri("/a/b", "/a/b/")
        assert not is_equal_or_child_uri("/a/b", "/a/bc")
        assert not is_equal_or_child_uri("/a/b", "/a/bc/")
        assert is_equal_or_child_uri("/a/b", "/a/b/c")
        assert is_equal_or_child_uri("/a/b", "/a/b/c")

        assert lstripstr("/dav/a/b", "/dav") == "/a/b"
        assert lstripstr("/dav/a/b", "/DAV") == "/dav/a/b"
        assert lstripstr("/dav/a/b", "/DAV", True) == "/a/b"

        assert pop_path("/a/b/c") == ("a", "/b/c")
        assert pop_path("/a/b/") == ("a", "/b/")
        assert pop_path("/a/") == ("a", "/")
        assert pop_path("/a") == ("a", "/")
        assert pop_path("/") == ("", "")
        assert pop_path("") == ("", "")

        self.assertEqual(shift_path("", "/a/b/c"), ("a", "/a", "/b/c"))
        self.assertEqual(shift_path("/a", "/b/c"), ("b", "/a/b", "/c"))
        self.assertEqual(shift_path("/a/b", "/c"), ("c", "/a/b/c", ""))
        self.assertEqual(shift_path("/a/b/c", "/"), ("", "/a/b/c", ""))
        self.assertEqual(shift_path("/a/b/c", ""), ("", "/a/b/c", ""))


class LoggerTest(unittest.TestCase):
    """Test configurable logging."""

    def setUp(self):
        # We add handlers that store root- and base-logger output
        self.rootBuffer = StringIO()
        rootLogger = logging.getLogger()
        self.prevRootLogLevel = rootLogger.getEffectiveLevel()
        self.rootLogHandler = logging.StreamHandler(self.rootBuffer)
        rootLogger.addHandler(self.rootLogHandler)

        self.baseBuffer = StringIO()
        baseLogger = logging.getLogger(BASE_LOGGER_NAME)
        self.prevBaseLogLevel = baseLogger.getEffectiveLevel()
        self.baseLogHandler = logging.StreamHandler(self.baseBuffer)
        baseLogger.addHandler(self.baseLogHandler)

    def tearDown(self):
        rootLogger = logging.getLogger()
        self.rootLogHandler.close()
        rootLogger.setLevel(self.prevRootLogLevel)
        rootLogger.removeHandler(self.rootLogHandler)

        baseLogger = logging.getLogger(BASE_LOGGER_NAME)
        self.baseLogHandler.close()
        baseLogger.setLevel(self.prevBaseLogLevel)
        baseLogger.removeHandler(self.baseLogHandler)

    def getLogOutput(self):
        self.rootLogHandler.flush()
        self.baseLogHandler.flush()
        return (self.rootBuffer.getvalue(), self.baseBuffer.getvalue())

    def testDefault(self):
        """By default, there should be no logging."""
        _baseLogger = logging.getLogger(BASE_LOGGER_NAME)

        _baseLogger.debug("_baseLogger.debug")
        _baseLogger.info("_baseLogger.info")
        _baseLogger.warning("_baseLogger.warning")
        _baseLogger.error("_baseLogger.error")

        rootOutput, baseOutput = self.getLogOutput()
        # Printed for debugging, when test fails:
        print("ROOT OUTPUT:\n'{}'\nBASE OUTPUT:\n'{}'".format(rootOutput, baseOutput))

        # No output should be generated in the root logger
        assert rootOutput == ""
        # The library logger should default to INFO level
        # (this output will not be visble, because the base logger only has a NullHandler)
        assert ".debug" not in baseOutput
        assert ".info" in baseOutput
        assert ".warning" in baseOutput
        assert ".error" in baseOutput

    def testEnablePropagation(self):
        """Users can enable logging by propagating to root logger."""
        _baseLogger = logging.getLogger(BASE_LOGGER_NAME)

        _baseLogger.propagate = True

        _baseLogger.debug("_baseLogger.debug")
        _baseLogger.info("_baseLogger.info")
        _baseLogger.warning("_baseLogger.warning")
        _baseLogger.error("_baseLogger.error")

        rootOutput, baseOutput = self.getLogOutput()
        # Printed for debugging, when test fails:
        print("ROOT OUTPUT:\n'{}'\nBASE OUTPUT:\n'{}'".format(rootOutput, baseOutput))

        # Now output we should see output in the root logger
        assert rootOutput == baseOutput
        # The library logger should default to INFO level
        # (this output will not be visble, because the base logger only has a NullHandler)
        assert ".debug" not in baseOutput
        assert ".info" in baseOutput
        assert ".warning" in baseOutput
        assert ".error" in baseOutput

    def testCliLogging(self):
        """CLI initializes logging."""
        config = {"verbose": 3, "enable_loggers": ["test"]}
        init_logging(config)

        _baseLogger = logging.getLogger(BASE_LOGGER_NAME)
        _enabledLogger = get_module_logger("test")
        _disabledLogger = get_module_logger("test2")

        _baseLogger.debug("_baseLogger.debug")
        _baseLogger.info("_baseLogger.info")
        _baseLogger.warning("_baseLogger.warning")
        _baseLogger.error("_baseLogger.error")

        _enabledLogger.debug("_enabledLogger.debug")
        _enabledLogger.info("_enabledLogger.info")
        _enabledLogger.warning("_enabledLogger.warning")
        _enabledLogger.error("_enabledLogger.error")

        _disabledLogger.debug("_disabledLogger.debug")
        _disabledLogger.info("_disabledLogger.info")
        _disabledLogger.warning("_disabledLogger.warning")
        _disabledLogger.error("_disabledLogger.error")

        rootOutput, baseOutput = self.getLogOutput()
        # Printed for debugging, when test fails:
        print("ROOT OUTPUT:\n'{}'\nBASE OUTPUT:\n'{}'".format(rootOutput, baseOutput))

        # init_logging() removes all other handlers
        assert rootOutput == ""
        assert baseOutput == ""


if __name__ == "__main__":
    unittest.main()
