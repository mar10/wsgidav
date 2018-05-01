# -*- coding: iso-8859-1 -*-
# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""Unit tests for wsgidav.util"""
from __future__ import print_function

import logging
import logging.handlers
import unittest

from wsgidav.compat import StringIO

from wsgidav.util import (
    initLogging,
    isChildUri,
    isEqualOrChildUri,
    joinUri,
    lstripstr,
    popPath,
    shiftPath,
    getModuleLogger, BASE_LOGGER_NAME,
    )


class BasicTest(unittest.TestCase):
    """Test ."""

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
        """CLI initializes logging """
        enable_loggers = ["test",
                          ]
        initLogging(3, enable_loggers)

        _baseLogger = logging.getLogger(BASE_LOGGER_NAME)
        _enabledLogger = getModuleLogger("test")
        _disabledLogger = getModuleLogger("test2")

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

        # initLogging() removes all other handlers
        assert rootOutput == ""
        assert baseOutput == ""


if __name__ == "__main__":
    unittest.main()
