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
    write, warn, note, status, debug,
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
    """Test ."""

    def setUp(self):
        self.buffer = StringIO()
        print("# Log output buffer start", file=self.buffer)
        rootLogger = logging.getLogger()
        self.prevLogLevel = rootLogger.getEffectiveLevel()
        # rootLogger.setLevel(logging.DEBUG)
        self.logHandler = logging.StreamHandler(self.buffer)
        # self.formatter = logging.Formatter(
        #     "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # self.logHandler.setFormatter(formatter)
        rootLogger.addHandler(self.logHandler)

    def tearDown(self):
        rootLogger = logging.getLogger()
        rootLogger.setLevel(self.prevLogLevel)
        rootLogger.removeHandler(self.logHandler)

    def getLogOutput(self):
        self.logHandler.flush()
        self.buffer.flush()
        value = self.buffer.getvalue()
        return value

    def testLogging(self):

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
        print()

        _enabledLogger.debug("_enabledLogger.debug")
        _enabledLogger.info("_enabledLogger.info")
        _enabledLogger.warning("_enabledLogger.warning")
        _enabledLogger.error("_enabledLogger.error")
        print()

        _disabledLogger.debug("_disabledLogger.debug")
        _disabledLogger.info("_disabledLogger.info")
        _disabledLogger.warning("_disabledLogger.warning")
        _disabledLogger.error("_disabledLogger.error")
        print()

        write("util.write()")
        warn("util.warn()")
        status("util.status()")
        note("util.note()")
        debug("util.debug()")

    def testLogging2(self):
        """Test custom loggers."""
        logger = logging.getLogger("wsgidav")
        logger2 = logging.getLogger("wsgidav.test")
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug")
        logger2.debug("Debug2")

        output = self.getLogOutput()
        print(output)

        assert "# Log output buffer start" in output

        # assert False

        # Create and use a custom logger
        # custom_logger = wsgidav.getLogger("wsgidav_test")
        # log_path = os.path.join(PYFTPSYNC_TEST_FOLDER, "pyftpsync.log")
        # handler = logging.handlers.WatchedFileHandler(log_path)
        # # formatter = logging.Formatter(logging.BASIC_FORMAT)
        # formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # handler.setFormatter(formatter)
        # custom_logger.addHandler(handler)
        # set_wsgidav_logger(custom_logger)
        #
        # custom_logger.setLevel(logging.DEBUG)
        # print("print 1")
        # write("write info 1")
        # write_error("write error 1")
        #
        # custom_logger.setLevel(logging.WARNING)
        # write("write info 2")
        # write_error("write error 2")
        #
        # handler.flush()
        # log_data = read_test_file("pyftpsync.log")
        # assert "print 1" not in log_data
        # assert "write info 1" in log_data
        # assert "write error 1" in log_data
        # assert "write info 2" not in log_data, "Loglevel honored"
        # assert "write error 2" in log_data
        # # Cleanup properly (log file would be locked otherwise)
        # custom_logger.removeHandler(handler)
        # handler.close()


if __name__ == "__main__":
    unittest.main()
