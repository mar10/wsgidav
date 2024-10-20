# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""Unit tests for wsgidav.util"""

import logging
import logging.handlers
import sys
import unittest
from io import StringIO

from wsgidav.util import (
    BASE_LOGGER_NAME,
    check_tags,
    checked_etag,
    deep_update,
    fix_path,
    get_dict_value,
    get_module_logger,
    init_logging,
    is_child_uri,
    is_equal_or_child_uri,
    join_uri,
    parse_if_match_header,
    pop_path,
    removeprefix,
    shift_path,
    update_headers_in_place,
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

        assert removeprefix("/dav/a/b", "/dav") == "/a/b"
        assert removeprefix("/dav/a/b", "/DAV") == "/dav/a/b"
        assert removeprefix("/dav/a/b", "/DAV", ignore_case=True) == "/a/b"

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

        assert check_tags("b", ["a", "b", "c"]) is None
        assert check_tags("b", ("a", "b", "c")) is None
        assert check_tags("b", {"a", "b", "c"}) is None
        assert check_tags("b", "a, b, c") is None
        assert check_tags("b", {"a": 1, "b": 2, "c": 3}) is None
        self.assertRaises(ValueError, check_tags, "x", ["a", "b", "c"])
        known = {"a", "b", "c"}
        assert check_tags(("a", "c"), known) is None
        assert check_tags(["a", "c"], known) is None
        assert check_tags({"a", "c"}, known) is None
        assert check_tags("a, c", known) is None
        assert check_tags({"a": 1, "c": 3}, known) is None
        self.assertRaises(ValueError, check_tags, {"a", "x"}, known)
        self.assertRaises(ValueError, check_tags, {"a", "c"}, known, required=True)
        # assert (
        #     check_tags({"a", "x"}, known, check_missing=True, raise_error=False)
        #     == "Unknown: 'x'\n"
        #     "Missing: 'c', 'b'\n"
        #     "Known: 'c', 'a', 'b'"
        # )

        assert checked_etag(None, allow_none=True) is None
        assert checked_etag("abc") == "abc"
        self.assertRaises(ValueError, checked_etag, '"abc"')
        self.assertRaises(ValueError, checked_etag, 'W/"abc"')

        assert parse_if_match_header("") == []
        assert parse_if_match_header("  ") == []
        assert parse_if_match_header("*") == ["*"]
        assert parse_if_match_header("abc,def") == ["abc", "def"]
        assert parse_if_match_header(" abc , def") == ["abc", "def"]
        assert parse_if_match_header(' "abc" , def ') == ["abc", "def"]
        assert parse_if_match_header(' W/"abc" , def ') == ["abc", "def"]

        self.assertRaises(ValueError, fix_path, "a/b", "/root/x")
        if sys.platform == "win32":
            assert (
                fix_path("a/b", "/root/x", must_exist=False).lower() == r"c:\root\x\a\b"
            )
            # NOTE:
            # Changed in version 3.13: On Windows, `os.path.isabs` returns False
            # if the given path starts with exactly one (back)slash.
            # So, on n Windows, Python 3.12 and before return "/a/b"
            # but on Python 3.13 and later return "c:\a\b"
            res = fix_path("/a/b", "/root/x", must_exist=False)
            if sys.version_info < (3, 13):
                assert res.lower() == r"/a/b"
            else:
                assert res.lower() == r"c:\a\b"
        else:
            assert fix_path("a/b", "/root/x", must_exist=False) == "/root/x/a/b"
            assert fix_path("/a/b", "/root/x", must_exist=False) == "/a/b"

        headers = [("foo", "bar"), ("baz", "qux")]
        update_headers_in_place(headers, [("Foo", "bar2"), ("New", "new_val")])
        assert headers == [("Foo", "bar2"), ("baz", "qux"), ("New", "new_val")]

        d_org = {"b": True, "d": {"i": 1, "t": (1, 2)}}
        d_new = {}
        assert deep_update(d_org.copy(), d_new) == d_org
        assert deep_update(d_org.copy(), {"b": False}) == {
            "b": False,
            "d": {"i": 1, "t": (1, 2)},
        }
        assert deep_update(d_org.copy(), {"b": {"class": "c"}}) == {
            "b": {"class": "c"},
            "d": {"i": 1, "t": (1, 2)},
        }

        d_new = {
            "user_mapping": {
                "*": {
                    "tester": {
                        "password": "secret",
                        "description": "",
                        "roles": [],
                    },
                    "tester2": {
                        "password": "secret2",
                        "description": "",
                        "roles": [],
                    },
                }
            }
        }
        assert deep_update({"user_mapping": {}}, d_new) == d_new

        d = {"b": True, "d": {"i": 1, "t": (1, 2)}}
        assert get_dict_value(d, "b") is True
        assert get_dict_value(d, "d.i") == 1
        assert get_dict_value(d, "d.i", default="def") == 1
        assert get_dict_value(d, "d.q", default="def") == "def"
        assert get_dict_value(d, "d.q.v", default="def") == "def"
        assert get_dict_value(d, "q.q.q", default="def") == "def"
        assert get_dict_value(d, "d.t.[1]") == 2
        self.assertRaises(IndexError, get_dict_value, d, "d.t.[2]")
        self.assertRaises(KeyError, get_dict_value, d, "d.q")

        d = {"a": None, "b": {}, "c": False}
        assert get_dict_value(d, "a", as_dict=True) == {}
        assert get_dict_value(d, "b", as_dict=True) == {}
        assert get_dict_value(d, "c", as_dict=True) is False
        assert get_dict_value(d, "x", as_dict=True) == {}
        self.assertRaises(KeyError, get_dict_value, d, "x", as_dict=False)


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
        print(f"ROOT OUTPUT:\n{rootOutput!r}\nBASE OUTPUT:\n{baseOutput!r}")

        # No output should be generated in the root logger
        assert rootOutput == ""
        # The library logger should default to INFO level
        # (this output will not be visible, because the base logger only has a NullHandler)
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
        print(f"ROOT OUTPUT:\n{rootOutput!r}\nBASE OUTPUT:\n{baseOutput!r}")

        # Now output we should see output in the root logger
        assert rootOutput == baseOutput
        # The library logger should default to INFO level
        # (this output will not be visible, because the base logger only has a NullHandler)
        assert ".debug" not in baseOutput
        assert ".info" in baseOutput
        assert ".warning" in baseOutput
        assert ".error" in baseOutput

    def testCliLogging(self):
        """CLI initializes logging."""
        config = {
            "verbose": 3,
            "logging": {
                "enable_loggers": ["test"],
            },
        }
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
        print(f"ROOT OUTPUT:\n{rootOutput!r}\nBASE OUTPUT:\n{baseOutput!r}")

        # init_logging() removes all other handlers
        assert rootOutput == ""
        assert baseOutput == ""


if __name__ == "__main__":
    unittest.main()
