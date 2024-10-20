# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/m ar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Miscellaneous support functions for WsgiDAV.
"""

import base64
import calendar
import collections.abc
import logging
import mimetypes
import os
import re
import stat
import sys
import time
import warnings
from copy import deepcopy
from email.utils import formatdate, parsedate
from hashlib import md5
from pprint import pformat
from typing import Iterable, Optional, Tuple
from urllib.parse import quote

from wsgidav import __version__
from wsgidav.dav_error import (
    HTTP_BAD_REQUEST,
    HTTP_CREATED,
    HTTP_NO_CONTENT,
    HTTP_NOT_MODIFIED,
    HTTP_OK,
    HTTP_PRECONDITION_FAILED,
    HTTP_RANGE_NOT_SATISFIABLE,
    DAVError,
    as_DAVError,
    get_http_status_string,
)
from wsgidav.xml_tools import etree, is_etree_element, make_sub_element, xml_to_bytes

__docformat__ = "reStructuredText"

#: The base logger (silent by default)
BASE_LOGGER_NAME = "wsgidav"
_logger = logging.getLogger(BASE_LOGGER_NAME)

#: Currently used Python version as string
PYTHON_VERSION = ".".join([str(s) for s in sys.version_info[:3]])

filesystemencoding = sys.getfilesystemencoding()

#: Project name and version presented to the clients
#: This is reset to ``"WsgiDAV"`` if ``suppress_version_info`` is set in the
#: configuration.
public_wsgidav_info = f"WsgiDAV/{__version__}"
#: This is reset to ``"Python/3"`` if ``suppress_version_info`` is set in the
#: configuration.
public_python_info = f"Python/{PYTHON_VERSION}"


class NO_DEFAULT:
    """"""


def check_python_version(min_version: Tuple[str]) -> bool:
    """Check for deprecated Python version."""
    if sys.version_info < min_version:
        min_ver = ".".join([str(s) for s in min_version[:3]])
        warnings.warn(
            f"Support for Python version less than `{min_ver}` is deprecated "
            f"(using {PYTHON_VERSION})",
            DeprecationWarning,
            stacklevel=2,
        )
        return False
    return True


# ========================================================================
# String tools
# ========================================================================


def is_basestring(s):
    """Return True for any string type (for str/unicode on Py2 and bytes/str on Py3)."""
    return isinstance(s, (str, bytes))


def is_bytes(s):
    """Return True for bytestrings (for str on Py2 and bytes on Py3)."""
    return isinstance(s, bytes)


def is_str(s):
    """Return True for native strings (for str on Py2 and Py3)."""
    return isinstance(s, str)


def to_bytes(s, encoding="utf8"):
    """Convert a text string (unicode) to bytestring (str on Py2 and bytes on Py3)."""
    if type(s) is not bytes:
        s = bytes(s, encoding)
    return s


def to_str(s, encoding="utf8"):
    """Convert data to native str type (bytestring on Py2 and unicode on Py3)."""
    if type(s) is bytes:
        s = str(s, encoding)
    elif type(s) is not str:
        s = str(s)
    return s


def to_set(val, *, or_none=False, raise_error=False) -> set:
    res = set()
    if type(val) is set:
        res = val
    elif type(val) is str:
        res = set(map(str.strip, val.split(",")))
    elif isinstance(val, (dict, list, tuple)):
        res = set(map(str, val))
    elif val is None and or_none:
        res = None
    elif raise_error:
        raise TypeError(f"{val}, {type(val)}")
    return res


def get_dict_value(d, key_path, default=NO_DEFAULT, *, as_dict=False):
    """Return the value of a nested dict using dot-notation path.

    Args:
        d (dict):
        key_path (str):
        default  (any):
        as_dict (bool):
            Assume default is `{}` and also return `{}` if the key exists with
            a value of `None`. This covers the case where suboptions are
            supposed to be dicts, but are defined in a YAML file as entry
            without a value.

    Raises:
        KeyError:
        ValueError:
        IndexError:

    Examples::

        ...

    Todo:
        * k[1] instead of k.[1]
    """
    if as_dict:
        try:
            res = get_dict_value(d, key_path, default={})
            return res if res is not None else {}
        except (AttributeError, KeyError, ValueError, IndexError):
            return {}

    if default is not NO_DEFAULT:
        try:
            return get_dict_value(d, key_path)
        except (AttributeError, KeyError, ValueError, IndexError):
            return default

    seg_list = key_path.split(".")
    seg = seg_list.pop(0)
    value = d[seg]

    while seg_list:
        seg = seg_list.pop(0)
        if isinstance(value, dict):
            value = value[seg]
        elif isinstance(value, (list, tuple)):
            if not seg.startswith("[") or not seg.endswith("]"):
                raise ValueError("Use `[INT]` syntax to address list items")
            seg = seg[1:-1]
            value = value[int(seg)]
        else:
            # raise ValueError("Segment {!r} cannot be nested".format(seg))
            try:
                value = getattr(value, seg)
            except AttributeError:
                raise  # ValueError("Segment {!r} cannot be nested".format(seg))

    return value


# password_patterns = []


def purge_passwords(d, *, in_place=False):
    def _purge(v):
        if isinstance(v, dict):
            if "password" in v:
                v["password"] = "<REMOVED>"
            for ele in v.values():
                _purge(ele)
        elif isinstance(v, Iterable) and not isinstance(v, str):
            for ele in v:
                _purge(ele)

    if not in_place:
        d = deepcopy(d)

    for v in d.values():
        _purge(v)

    if in_place:
        return None  # good convention to return None for mutating functions
    return d


def check_tags(tags, known, *, msg=None, raise_error=True, required=False):
    """Check if `tags` only contains known tags.

    If check fails and raise_error is true, a ValueError is raised.
    If check passes, None is returned.
    """
    assert known, "must not be empty"
    known = to_set(known)
    optional = known

    if required is True:
        required = known
        optional = set()
    elif required:
        required = to_set(required)
        known = known.union(required)
        optional = known.difference(required)

    tags = to_set(tags)

    res = []
    unknown = tags.difference(known)
    if unknown:
        res.append("Unknown: {!r}".format("', '".join(unknown)))

    if required:
        missing = required.difference(tags)
        if missing:
            res.append("Missing: {!r}".format("', '".join(missing)))

    if res:
        if msg:
            res.insert(0, msg)

        if required and optional:
            res.append(
                "Required: ({!r}). Optional: ({!r})".format(
                    "', '".join(required), "', '".join(optional)
                )
            )
        elif required:
            res.append("Required: ({!r})".format("', '".join(required)))
        elif optional:
            res.append("Optional: ({!r})".format("', '".join(optional)))

        res = "\n".join(res)
        if raise_error:
            raise ValueError(res)
        return res

    return None


# --- WSGI support ---


def unicode_to_wsgi(u):
    """Convert an environment variable to a WSGI 'bytes-as-unicode' string."""
    # Taken from PEP3333; the server should already have performed this, when
    # passing environ to the WSGI application
    return u.encode(filesystemencoding, "surrogateescape").decode("iso-8859-1")


def wsgi_to_bytes(s):
    """Convert a native string to a WSGI / HTTP compatible byte string.

    WSGI always assumes iso-8859-1 (PEP 3333).
    https://bugs.python.org/issue16679#msg177450
    """
    return s.encode("iso-8859-1")


def re_encode_wsgi(s: str, *, encoding="utf-8", fallback=False) -> str:
    """Convert a WSGI string to `str`, assuming the client used UTF-8.

    WSGI always assumes iso-8859-1. Modern clients send UTF-8, so we have to
    re-encode

    https://www.python.org/dev/peps/pep-3333/#unicode-issues
    https://bugs.python.org/issue16679#msg177450
    """
    try:
        if type(s) is bytes:
            # haven't seen this case, but may be possible according to PEP 3333?
            return s.decode(encoding)
        return s.encode("iso-8859-1").decode(encoding)
    except UnicodeDecodeError:
        if fallback:
            return s
        raise


# ========================================================================
# Time tools
# ========================================================================


def get_rfc1123_time(secs=None):
    """Return <secs> in rfc 1123 date/time format (pass secs=None for current date)."""
    # GC issue #20: time string must be locale independent
    return formatdate(timeval=secs, localtime=False, usegmt=True)


def get_rfc3339_time(secs=None):
    """Return <secs> in RFC 3339 date/time format (pass secs=None for current date).

    RFC 3339 is a subset of ISO 8601, used for '{DAV:}creationdate'.
    See http://tools.ietf.org/html/rfc3339
    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(secs))


def get_log_time(secs=None):
    """Return <secs> in log time format (pass secs=None for current date)."""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(secs))


def parse_time_string(timestring):
    """Return the number of seconds since the epoch, for a date/time string.

    Returns None for invalid input

    The following time type strings are supported:

    Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
    Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
    Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format
    """
    result = _parse_gmt_time(timestring)
    if result:
        return calendar.timegm(result)
    return None


def _parse_gmt_time(timestring):
    """Return a standard time tuple (see time and calendar), for a date/time string."""
    # Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
    try:
        return time.strptime(timestring, "%a, %d %b %Y %H:%M:%S GMT")
    except Exception:
        pass

    # Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
    try:
        return time.strptime(timestring, "%A %d-%b-%y %H:%M:%S GMT")
    except Exception:
        pass

    # Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format
    try:
        return time.strptime(timestring, "%a %b %d %H:%M:%S %Y")
    except Exception:
        pass

    # Sun Nov  6 08:49:37 1994 +0100      ; ANSI C's asctime() format with
    # timezon
    try:
        return parsedate(timestring)
    except Exception:
        pass

    return None


# ========================================================================
# Logging
# ========================================================================


def init_logging(config):
    """Initialize base logger named 'wsgidav'.

    The base logger is filtered by the `verbose` configuration option.
    Log entries will have a time stamp and thread id.

    **Note:** init_logging() is automatically called if an application adds
    ``"logging": { "enable": true }`` to the configuration.

    Module loggers
    ~~~~~~~~~~~~~~
    Module loggers (e.g 'wsgidav.lock_man.lock_manager') are named loggers, that
    can be independently switched to DEBUG mode.

    Except for verbosity, they will inherit settings from the base logger.

    They will suppress DEBUG level messages, unless they are enabled by passing
    their name to util.init_logging().

    If enabled, module loggers will print DEBUG messages, even if verbose == 3.

    Example initialize and use a module logger, that will generate output,
    if enabled (and verbose >= 2)::

        _logger = util.get_module_logger(__name__)
        [..]
        _logger.debug("foo: {!r}".format(s))

    This logger would be enabled by passing its name to init_logging()::

        config.logging.enable_loggers = ["lock_manager",
                          "property_manager",
                         ]
        util.init_logging(2, enable_loggers)


    Log Level Matrix
    ~~~~~~~~~~~~~~~~

    +---------+--------+---------------------------------------------------------------+
    | Verbose | Option |                       Log level                               |
    | level   |        +-------------+------------------------+------------------------+
    |         |        | base logger | module logger(default) | module logger(enabled) |
    +=========+========+=============+========================+========================+
    |    0    | -qqq   | CRITICAL    | CRITICAL               | CRITICAL               |
    +---------+--------+-------------+------------------------+------------------------+
    |    1    | -qq    | ERROR       | ERROR                  | ERROR                  |
    +---------+--------+-------------+------------------------+------------------------+
    |    2    | -q     | WARN        | WARN                   | WARN                   |
    +---------+--------+-------------+------------------------+------------------------+
    |    3    |        | INFO        | INFO                   | **DEBUG**              |
    +---------+--------+-------------+------------------------+------------------------+
    |    4    | -v     | DEBUG       | DEBUG                  | DEBUG                  |
    +---------+--------+-------------+------------------------+------------------------+
    |    5    | -vv    | DEBUG       | DEBUG                  | DEBUG                  |
    +---------+--------+-------------+------------------------+------------------------+

    """
    from wsgidav.default_conf import DEFAULT_LOGGER_DATE_FORMAT, DEFAULT_LOGGER_FORMAT

    verbose = config.get("verbose", 3)
    log_opts = config.get("logging") or {}

    enable_loggers = log_opts.get("enable_loggers", [])
    if enable_loggers is None:
        enable_loggers = []

    logger_date_format = log_opts.get("logger_date_format", DEFAULT_LOGGER_DATE_FORMAT)
    logger_format = log_opts.get("logger_format", DEFAULT_LOGGER_FORMAT)
    # Verbose format by default (but wsgidav.util.DEFAULT_CONFIG defines a short format)
    # logger_date_format = log_opts.get("logger_date_format", "%Y-%m-%d %H:%M:%S")
    # logger_format = log_opts.get(
    #     "logger_format",
    #     "%(asctime)s.%(msecs)03d - <%(thread)d> %(name)-27s %(levelname)-8s:  %(message)s",
    # )

    formatter = logging.Formatter(logger_format, logger_date_format)

    # Define handlers
    consoleHandler = logging.StreamHandler(sys.stdout)
    #    consoleHandler = logging.StreamHandler(sys.stderr)
    consoleHandler.setFormatter(formatter)
    # consoleHandler.setLevel(logging.DEBUG)

    # Add the handlers to the base logger
    logger = logging.getLogger(BASE_LOGGER_NAME)

    if verbose >= 4:  # --verbose
        logger.setLevel(logging.DEBUG)
    elif verbose == 3:  # default
        logger.setLevel(logging.INFO)
    elif verbose == 2:  # --quiet
        logger.setLevel(logging.WARN)
        # consoleHandler.setLevel(logging.WARN)
    elif verbose == 1:  # -qq
        logger.setLevel(logging.ERROR)
        # consoleHandler.setLevel(logging.WARN)
    else:  # -qqq
        logger.setLevel(logging.CRITICAL)
        # consoleHandler.setLevel(logging.ERROR)

    # Don't call the root's handlers after our custom handlers
    logger.propagate = False

    # Remove previous handlers
    for hdlr in logger.handlers[:]:  # Must iterate an array copy
        try:
            hdlr.flush()
            hdlr.close()
        except Exception:
            pass
        logger.removeHandler(hdlr)

    logger.addHandler(consoleHandler)

    if verbose >= 3:
        for e in enable_loggers:
            if not e.startswith(BASE_LOGGER_NAME + "."):
                e = BASE_LOGGER_NAME + "." + e
            lg = logging.getLogger(e.strip())
            lg.setLevel(logging.DEBUG)
    return


def get_module_logger(moduleName, *, default_to_verbose=False):
    """Create a module logger, that can be en/disabled by configuration.

    @see: unit.init_logging
    """
    # moduleName = moduleName.split(".")[-1]
    if not moduleName.startswith(BASE_LOGGER_NAME + "."):
        moduleName = BASE_LOGGER_NAME + "." + moduleName
    logger = logging.getLogger(moduleName)
    # if logger.level == logging.NOTSET and not default_to_verbose:
    #     logger.setLevel(logging.INFO)  # Disable debug messages by default
    return logger


def deep_update(d, u):
    # print(f"deep_update({d}, {u})")
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            # print(f"deep_update({d}, {u}): k={k}, v={v}")
            prev_val = d.get(k)
            # if type(prev_val) in (bool, float, int, str):
            if prev_val is None or type(prev_val) in (bool, float, int, str):
                # Prev. values is a scalar: replace it with a copy of the new dict
                d[k] = v.copy()
            else:
                # Merge new values into prev. dict
                d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


# ========================================================================
# Module Import
# ========================================================================


def dynamic_import_class(name):
    """Import a class from a module string, e.g. ``my.module.ClassName``."""
    import importlib

    if "." not in name:
        raise ValueError(f"Expected `path.to.ClassName` string: {name!r}")
    module_name, class_name = name.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        _logger.error(f"Dynamic import of {name!r} failed: {e}")
        raise
    the_class = getattr(module, class_name)
    return the_class


def dynamic_instantiate_class(class_name, options, *, expand=None, raise_error=True):
    """Import a class and instantiate with custom args.

    Equivalent of
    ```py
    from my.module import Foo
    return Foo(bar=42, baz="qux")
    ```
    would be
    ```py
    options = {
        "bar": 42,
        "baz": "qux"
    }
    =>
    ```
    Examples:
        # Equivalent of
        name = "my.module.Foo"
        from my.module import Foo
        return Foo(bar=42, baz="qux")
    """

    def _expand(v):
        """Replace some string templates with defined values."""
        if expand and is_basestring(v) and v.lower() in expand:
            return expand[v]
        return v

    check_tags(
        options,
        {"args", "kwargs"},
        msg=f"Invalid class instantiation options for {class_name}",
    )
    pos_args = options.get("args") or []
    if pos_args is not None and not isinstance(pos_args, (tuple, list)):
        raise ValueError(f"Expected list format for `args` option: {options}")

    kwargs = options.get("kwargs") or {}
    if kwargs is not None and not isinstance(kwargs, dict):
        raise ValueError(f"Expected dict format for `kwargs` option: {options}")

    try:
        inst = None
        the_class = dynamic_import_class(class_name)
        pos_args = tuple(map(_expand, pos_args))
        kwargs = {k: _expand(v) for k, v in kwargs.items()}
        # pos_args = []
        # kwargs = {}
        # if type(options) in (tuple, list):
        #     pos_args = tuple(map(_expand, options))
        # elif type(options) is dict:
        #     kwargs = {k: _expand(v) for k, v in options.items()}
        # else:
        #     raise ValueError(f"Unexpected options format: {options}")

        inst = the_class(*pos_args, **kwargs)

        disp_args = [f"{o}" for o in pos_args] + [
            f"{k}={v!r}" for k, v in kwargs.items()
        ]
        _logger.debug(
            "Instantiate {}({}) => {}".format(class_name, ", ".join(disp_args), inst)
        )
    except Exception:
        msg = f"Instantiate {class_name}({options}) failed"
        if raise_error:
            _logger.error(msg)
            raise
        _logger.exception(msg)

    return inst


def dynamic_instantiate_class_from_opts(options, *, expand=None):
    """Import a class and instantiate with custom args.


    Construct from class path, without constructor args:
    ```py
    dynamic_instantiate_class_from_opts("wsgidav.lock_man.lock_storage.LockStorageDict")
    ```
    Construct with constructor args:
    ```py
    opts = {
        "class": "wsgidav.lock_man.lock_storage.LockStorageShelve",
        "kwargs": {
            "storage_path": "~/wsgidav_locks.shelve",
        }
    }
    dynamic_instantiate_class_from_opts(opts, expand=...)
    ```
    """
    if type(options) is str:
        options = {"class": options}
    else:
        options = options.copy()

    check_tags(
        options,
        {"class", "args", "kwargs"},
        required="class",
        msg="Invalid class instantiation options",
    )
    class_name = options.pop("class")
    return dynamic_instantiate_class(class_name, options, expand=expand)


# ========================================================================
# Strings
# ========================================================================


def removeprefix(s: str, prefix: str, ignore_case: bool = False) -> str:
    """Replacement for str.removeprefix() (Py3.9+) with ignore_case option."""
    if ignore_case:
        if not s.lower().startswith(prefix.lower()):
            return s
    else:
        if not s.startswith(prefix):
            return s
    return s[len(prefix) :]


def save_split(s, sep, maxsplit):
    """Split string, always returning n-tuple (filled with None if necessary)."""
    tok = s.split(sep, maxsplit)
    while len(tok) <= maxsplit:
        tok.append(None)
    return tok


def pop_path(path):
    """Return '/a/b/c' -> ('a', '/b/c')."""
    if path in ("", "/"):
        return ("", "")
    assert path.startswith("/")
    first, _sep, rest = path.lstrip("/").partition("/")
    return (first, "/" + rest)


def pop_path2(path):
    """Return '/a/b/c' -> ('a', 'b', '/c')."""
    if path in ("", "/"):
        return ("", "", "")
    first, rest = pop_path(path)
    second, rest = pop_path(rest)
    return (first, second, "/" + rest)


def shift_path(script_name, path_info):
    """Return ('/a', '/b/c') -> ('b', '/a/b', 'c')."""
    segment, rest = pop_path(path_info)
    return (segment, join_uri(script_name.rstrip("/"), segment), rest.rstrip("/"))


def split_namespace(clark_name):
    """Return (namespace, localname) tuple for a property name in Clark Notation.

    Namespace defaults to ''.
    Example:
    '{DAV:}foo'  -> ('DAV:', 'foo')
    'bar'  -> ('', 'bar')
    """
    if clark_name.startswith("{") and "}" in clark_name:
        ns, localname = clark_name.split("}", 1)
        return (ns[1:], localname)
    return ("", clark_name)


def to_unicode_safe(s):
    """Convert a binary string to Unicode using UTF-8 (fallback to ISO-8859-1)."""
    try:
        u = to_str(s, "utf8")
    except ValueError:
        _logger.error(f"to_unicode_safe({s!r}) *** UTF-8 failed. Trying ISO-8859-1")
        u = to_str(s, "ISO-8859-1")
    return u


def safe_re_encode(s, encoding_to, *, errors="backslashreplace"):
    """Re-encode str or binary so that is compatible with a given encoding (replacing
    unsupported chars).

    We use ASCII as default, which gives us some output that contains \x99 and \u9999
    for every character > 127, for easier debugging.
    (e.g. if we don't know the encoding, see #87, #96)
    """
    # prev = s
    if not encoding_to:
        encoding_to = "ASCII"
    if is_bytes(s):
        s = s.decode(encoding_to, errors=errors).encode(encoding_to)
    else:
        s = s.encode(encoding_to, errors=errors).decode(encoding_to)
    # print("safe_re_encode({}, {}) => {}".format(prev, encoding_to, s))
    return s


def string_repr(s):
    """Return a string as hex dump."""
    if is_bytes(s):
        res = f"{s!r}: "
        for b in s:
            if type(b) is str:  # Py2
                b = ord(b)
            res += "%02x " % b
        return res
    return f"{s}"


def get_file_extension(path):
    ext = os.path.splitext(path)[1]
    return ext


def byte_number_string(
    number, *, thousands_sep=True, partition=False, base1024=True, append_bytes=True
):
    """Convert bytes into human-readable representation."""
    magsuffix = ""
    bytesuffix = ""

    if partition:
        magnitude = 0
        if base1024:
            while number >= 1024:
                magnitude += 1
                number = number >> 10
        else:
            while number >= 1000:
                magnitude += 1
                number /= 1000.0
        # TODO: use "9 KB" instead of "9K Bytes"?
        # TODO use 'kibi' for base 1024?
        # http://en.wikipedia.org/wiki/Kibi-#IEC_standard_prefixes
        magsuffix = ["", "K", "M", "G", "T", "P"][magnitude]

    if append_bytes:
        if number == 1:
            bytesuffix = " Byte"
        else:
            bytesuffix = " Bytes"

    if thousands_sep and (number >= 1000 or magsuffix):
        # locale.setlocale(locale.LC_ALL, "")
        # # TODO: make precision configurable
        # snum = locale.format("%d", number, thousandsSep)
        snum = f"{number:,d}"
    else:
        snum = str(number)

    return f"{snum}{magsuffix}{bytesuffix}"


def fix_path(path, root, *, expand_vars=True, must_exist=True, allow_none=True):
    """Convert path to absolute, expand and check.

    Convert path to absolute if required, expand leading '~' as user home dir,
    expand %VAR%, $Var, ...
    """
    if path in (None, ""):
        if allow_none:
            return None
        raise ValueError(f"Invalid path {path!r}")

    if not os.path.isabs(path):
        if not root:
            root = os.getcwd()
        elif type(root) is dict:
            # Evaluate path relative to the folder of the config file (if any)
            config_file = root.get("_config_file")
            if config_file:
                root = os.path.dirname(config_file)
            else:
                root = os.getcwd()
        # NOTE:
        # Changed in version 3.13: On Windows, `os.path.isabs` returns False
        # if the given path starts with exactly one (back)slash.
        path = os.path.abspath(os.path.join(root, path))

    if expand_vars:
        path = os.path.expandvars(os.path.expanduser(path))

    if must_exist and not os.path.exists(path):
        raise ValueError(f"Invalid path: {path!r}")

    return path


# ========================================================================
# WSGI
# ========================================================================
def get_content_length(environ):
    """Return a positive CONTENT_LENGTH in a safe way (return 0 otherwise)."""
    # TODO: http://www.wsgi.org/wsgi/WSGI_2.0
    try:
        return max(0, int(environ.get("CONTENT_LENGTH", 0)))
    except ValueError:
        return 0


# def readAllInput(environ):
#    """Read and discard all from from wsgi.input, if this has not been done yet."""
#    cl = get_content_length(environ)
#    if environ.get("wsgidav.all_input_read") or cl == 0:
#        return
#    assert not environ.get("wsgidav.some_input_read")
#    write("Reading and discarding %s bytes input." % cl)
#    environ["wsgi.input"].read(cl)
#    environ["wsgidav.all_input_read"] = 1


def read_and_discard_input(environ):
    """Read 1 byte from wsgi.input, if this has not been done yet.

    Returning a response without reading from a request body might confuse the
    WebDAV client.
    This may happen, if an exception like '401 Not authorized', or
    '500 Internal error' was raised BEFORE anything was read from the request
    stream.

    See GC issue 13, issue 23
    See http://groups.google.com/group/paste-users/browse_frm/thread/fc0c9476047e9a47?hl=en

    Note that with persistent sessions (HTTP/1.1) we must make sure, that the
    'Connection: closed' header is set with the response, to prevent reusing
    the current stream.
    """
    if environ.get("wsgidav.some_input_read") or environ.get("wsgidav.all_input_read"):
        return
    cl = get_content_length(environ)
    assert cl >= 0
    if cl == 0:
        return

    READ_ALL = True

    environ["wsgidav.some_input_read"] = 1
    if READ_ALL:
        environ["wsgidav.all_input_read"] = 1

    wsgi_input = environ["wsgi.input"]

    # TODO: check if still required after GC issue 24 is fixed
    if hasattr(wsgi_input, "_consumed") and hasattr(wsgi_input, "length"):
        # Seems to be Paste's httpserver.LimitedLengthFile
        # see http://groups.google.com/group/paste-users/browse_thread/thread/fc0c9476047e9a47/aa4a3aa416016729?hl=en&lnk=gst&q=.input#aa4a3aa416016729  # noqa
        # Consume something if nothing was consumed *and* work
        # around a bug where paste.httpserver allows negative lengths
        if wsgi_input._consumed == 0 and wsgi_input.length > 0:
            # This seems to work even if there's 10K of input.
            if READ_ALL:
                n = wsgi_input.length
            else:
                n = 1
            body = wsgi_input.read(n)
            _logger.debug(
                f"Reading {n} bytes from potentially unread httpserver.LimitedLengthFile: {body[:50]!r}..."
            )

    elif hasattr(wsgi_input, "_sock") and hasattr(wsgi_input._sock, "settimeout"):
        # Seems to be a socket
        try:
            # Set socket to non-blocking
            sock = wsgi_input._sock
            timeout = sock.gettimeout()
            sock.settimeout(0)
            # Read one byte
            try:
                if READ_ALL:
                    n = cl
                else:
                    n = 1
                body = wsgi_input.read(n)
                _logger.debug(
                    f"Reading {n} bytes from potentially unread POST body: {body[:50]!r}..."
                )
            except OSError as se:
                # se(10035, 'The socket operation could not complete without blocking')
                _logger.error(f"-> read {n} bytes failed: {se}")
            # Restore socket settings
            sock.settimeout(timeout)
        except Exception:
            _logger.error(f"--> wsgi_input.read(): {sys.exc_info()}")


def fail(
    value,
    context_info=None,
    *,
    src_exception=None,
    err_condition=None,
    add_headers=None,
):
    """Wrapper to raise (and log) DAVError."""
    if isinstance(value, Exception):
        e = as_DAVError(value)
    else:
        e = DAVError(
            value,
            context_info,
            src_exception=src_exception,
            err_condition=err_condition,
            add_headers=add_headers,
        )
    _logger.debug(f"Raising DAVError {e.get_user_info()}")
    raise e


# ========================================================================
# SubAppStartResponse
# ========================================================================
class SubAppStartResponse:
    def __init__(self):
        self.__status = ""
        self.__response_headers = []
        self.__exc_info = None

        super().__init__()

    @property
    def status(self):
        return self.__status

    @property
    def response_headers(self):
        return self.__response_headers

    @property
    def exc_info(self):
        return self.__exc_info

    def __call__(self, status, response_headers, exc_info=None):
        self.__status = status
        self.__response_headers = response_headers
        self.__exc_info = exc_info


# ========================================================================
# URLs
# ========================================================================


def join_uri(uri, *segments):
    """Append segments to URI.

    Example: join_uri("/a/b", "c", "d")
    """
    sub = "/".join(segments)
    if not sub:
        return uri
    return uri.rstrip("/") + "/" + sub


def get_uri_name(uri: str) -> str:
    """Return local name, i.e. last segment of URI."""
    return uri.strip("/").split("/")[-1]


def get_uri_parent(uri: str) -> Optional[str]:
    """Return URI of parent collection with trailing '/', or None, if URI is top-level.

    This function simply strips the last segment. It does not test, if the
    target is a 'collection', or even exists.
    """
    if not uri or uri.strip() == "/":
        return None
    return uri.rstrip("/").rsplit("/", 1)[0] + "/"


def is_child_uri(parent_uri: str, child_uri: str) -> bool:
    """Return True, if child_uri is a child of parent_uri.

    This function accounts for the fact that '/a/b/c' and 'a/b/c/' are
    children of '/a/b' (and also of '/a/b/').
    Note that '/a/b/cd' is NOT a child of 'a/b/c'.
    """
    return (
        bool(parent_uri)
        and bool(child_uri)
        and child_uri.rstrip("/").startswith(parent_uri.rstrip("/") + "/")
    )


def is_equal_or_child_uri(parent_uri, child_uri):
    """Return True, if child_uri is a child of parent_uri or maps to the same resource.

    Similar to <util.is_child_uri>_ ,  but this method also returns True, if parent
    equals child. ('/a/b' is considered identical with '/a/b/').
    """
    return (
        parent_uri
        and child_uri
        and (child_uri.rstrip("/") + "/").startswith(parent_uri.rstrip("/") + "/")
    )


def make_complete_url(environ, local_uri=None):
    """URL reconstruction according to PEP 333.
    @see https://www.python.org/dev/peps/pep-3333/#url-reconstruction
    """
    url = environ["wsgi.url_scheme"] + "://"

    if environ.get("HTTP_HOST"):
        url += environ["HTTP_HOST"]
    else:
        url += environ["SERVER_NAME"]

        if environ["wsgi.url_scheme"] == "https":
            if environ["SERVER_PORT"] != "443":
                url += ":" + environ["SERVER_PORT"]
        else:
            if environ["SERVER_PORT"] != "80":
                url += ":" + environ["SERVER_PORT"]

    url += quote(environ.get("SCRIPT_NAME", ""))

    if local_uri is None:
        url += quote(environ.get("PATH_INFO", ""))
        if environ.get("QUERY_STRING"):
            url += "?" + environ["QUERY_STRING"]
    else:
        url += local_uri  # TODO: quote?
    return url


def update_headers_in_place(target, new_items) -> None:
    """Modify or append new headers to existing header list (in-place)."""
    new_dict = {k.lower(): (k, v) for k, v in new_items}
    for idx, (name, _value) in enumerate(target):
        new_val = new_dict.pop(name.lower(), None)
        if new_val is not None:
            target[idx] = new_val
    for value in new_dict.values():
        target.append(value)

    return  # in-place does not return a value


# ========================================================================
# XML
# ========================================================================


def parse_xml_body(environ, *, allow_empty=False):
    """Read request body XML into an etree.Element.

    Return None, if no request body was sent.
    Raise HTTP_BAD_REQUEST, if something else went wrong.

    TODO: this is a very relaxed interpretation: should we raise HTTP_BAD_REQUEST
    instead, if CONTENT_LENGTH is missing, invalid, or 0?

    RFC: For compatibility with HTTP/1.0 applications, HTTP/1.1 requests containing
    a message-body MUST include a valid Content-Length header field unless the
    server is known to be HTTP/1.1 compliant.
    If a request contains a message-body and a Content-Length is not given, the
    server SHOULD respond with 400 (bad request) if it cannot determine the
    length of the message, or with 411 (length required) if it wishes to insist
    on receiving a valid Content-Length."

    So I'd say, we should accept a missing CONTENT_LENGTH, and try to read the
    content anyway.
    But WSGI doesn't guarantee to support input.read() without length(?).
    At least it locked, when I tried it with a request that had a missing
    content-type and no body.

    Current approach: if CONTENT_LENGTH is

    - valid and >0:
      read body (exactly <CONTENT_LENGTH> bytes) and parse the result.
    - 0:
      Assume empty body and return None or raise exception.
    - invalid (negative or not a number:
      raise HTTP_BAD_REQUEST
    - missing:
      NOT: Try to read body until end and parse the result.
      BUT: assume '0'
    - empty string:
      WSGI allows it to be empty or absent: treated like 'missing'.
    """
    #
    clHeader = environ.get("CONTENT_LENGTH", "").strip()
    #    content_length = -1 # read all of stream
    if clHeader == "":
        # No Content-Length given: read to end of stream
        # TODO: etree.parse() locks, if input is invalid?
        #        pfroot = etree.parse(environ["wsgi.input"]).getroot()
        # requestbody = environ["wsgi.input"].read()  # TODO: read() should be
        # called in a loop?
        requestbody = ""
    else:
        try:
            content_length = int(clHeader)
            if content_length < 0:
                raise DAVError(HTTP_BAD_REQUEST, "Negative content-length.")
        except ValueError:
            raise DAVError(HTTP_BAD_REQUEST, "content-length is not numeric.") from None

        if content_length == 0:
            requestbody = ""
        else:
            requestbody = environ["wsgi.input"].read(content_length)
            environ["wsgidav.all_input_read"] = 1

    if requestbody == "":
        if allow_empty:
            return None
        else:
            raise DAVError(HTTP_BAD_REQUEST, "Body must not be empty.")

    try:
        rootEL = etree.fromstring(requestbody)
    except Exception as e:
        raise DAVError(
            HTTP_BAD_REQUEST, "Invalid XML format.", src_exception=e
        ) from None

    # If dumps of the body are desired, then this is the place to do it pretty:
    if environ.get("wsgidav.dump_request_body"):
        _logger.info(
            "{} XML request body:\n{}".format(
                environ["REQUEST_METHOD"],
                to_str(xml_to_bytes(rootEL, pretty=True)),
            )
        )
        environ["wsgidav.dump_request_body"] = False

    return rootEL


# def sendResponse(environ, start_response, body, content_type):
#    """Send a WSGI response for a HTML or XML string."""
#    assert content_type in ("application/xml", "text/html")
#
#    start_response(status, [("Content-Type", content_type),
#                            ("Date", get_rfc1123_time()),
#                            ("Content-Length", str(len(body))),
#                            ])
#    return [ body ]


def send_redirect_response(environ, start_response, *, location):
    """Start a WSGI response for a DAVError or status code."""

    start_response(
        "301 Moved Permanently",  # this is was nginx uses
        [
            ("Content-Length", "0"),
            ("Date", get_rfc1123_time()),
            ("Location", location),
        ],
    )
    return [b""]


def send_status_response(
    environ, start_response, e, *, add_headers=None, is_head=False
):
    """Start a WSGI response for a DAVError or status code."""
    status = get_http_status_string(e)
    headers = []
    if add_headers:
        headers.extend(add_headers)
    if isinstance(e, DAVError) and e.add_headers:
        headers.extend(e.add_headers)
    #    if 'keep-alive' in environ.get('HTTP_CONNECTION', '').lower():
    #        headers += [
    #            ('Connection', 'keep-alive'),
    #        ]

    if e in (HTTP_NOT_MODIFIED, HTTP_NO_CONTENT):
        # See paste.lint: these code don't have content
        start_response(
            status, [("Content-Length", "0"), ("Date", get_rfc1123_time())] + headers
        )
        return [b""]

    if e in (HTTP_OK, HTTP_CREATED):
        e = DAVError(e)
    assert isinstance(e, DAVError)

    content_type, body = e.get_response_page()
    if is_head:
        body = b""

    assert is_bytes(body), body  # If not, Content-Length is wrong!
    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Date", get_rfc1123_time()),
            ("Content-Length", str(len(body))),
        ]
        + headers,
    )
    return [body]


def send_multi_status_response(environ, start_response, multistatus_elem):
    # If logging of the body is desired, then this is the place to do it
    # pretty:
    if environ.get("wsgidav.dump_response_body"):
        xml = "{} XML response body:\n{}".format(
            environ["REQUEST_METHOD"],
            to_str(xml_to_bytes(multistatus_elem, pretty=True)),
        )
        environ["wsgidav.dump_response_body"] = xml

    # Hotfix for Windows XP
    # PROPFIND XML response is not recognized, when pretty_print = True!
    # (Vista and others would accept this).
    xml_data = xml_to_bytes(multistatus_elem, pretty=False)
    # If not, Content-Length is wrong!
    assert is_bytes(xml_data), xml_data

    headers = [
        ("Content-Type", "application/xml; charset=utf-8"),
        ("Date", get_rfc1123_time()),
        ("Content-Length", str(len(xml_data))),
    ]

    #    if 'keep-alive' in environ.get('HTTP_CONNECTION', '').lower():
    #        headers += [
    #            ('Connection', 'keep-alive'),
    #        ]

    start_response("207 Multi-Status", headers)
    return [xml_data]


def add_property_response(multistatus_elem, href, prop_list):
    """Append <response> element to <multistatus> element.

    <prop> node depends on the value type:
      - str or unicode: add element with this content
      - None: add an empty element
      - etree.Element: add XML element as child
      - DAVError: add an empty element to an own <propstatus> for this status code

    @param multistatus_elem: etree.Element
    @param href: global URL of the resource, e.g. 'http://server:port/path'.
    @param prop_list: list of 2-tuples (name, value)
    """
    # Split prop_list by status code and build a unique list of namespaces
    nsCount = 1
    nsDict = {}
    nsMap = {}
    propDict = {}

    for name, value in prop_list:
        status = "200 OK"
        if isinstance(value, DAVError):
            status = get_http_status_string(value)
            # Always generate *empty* elements for props with error status
            value = None

        # Collect namespaces, so we can declare them in the <response> for
        # compacter output
        ns, _ = split_namespace(name)
        if ns != "DAV:" and ns not in nsDict and ns != "":
            nsDict[ns] = True
            nsMap[f"NS{nsCount}"] = ns
            nsCount += 1

        propDict.setdefault(status, []).append((name, value))

    # <response>
    responseEL = make_sub_element(multistatus_elem, "{DAV:}response", nsmap=nsMap)

    #    log("href value:{}".format(string_repr(href)))
    #    etree.SubElement(responseEL, "{DAV:}href").text = toUnicode(href)
    etree.SubElement(responseEL, "{DAV:}href").text = href
    #    etree.SubElement(responseEL, "{DAV:}href").text = quote(href, safe="/" + "!*'(),"
    #       + "$-_|.")

    # One <propstat> per status code
    for status in propDict:
        propstatEL = etree.SubElement(responseEL, "{DAV:}propstat")
        # List of <prop>
        propEL = etree.SubElement(propstatEL, "{DAV:}prop")
        for name, value in propDict[status]:
            if value is None:
                etree.SubElement(propEL, name)
            elif is_etree_element(value):
                propEL.append(value)
            else:
                # value must be string or unicode
                #                log("{} value:{}".format(name, string_repr(value)))
                #                etree.SubElement(propEL, name).text = value
                etree.SubElement(propEL, name).text = to_unicode_safe(value)
        # <status>
        etree.SubElement(propstatEL, "{DAV:}status").text = f"HTTP/1.1 {status}"


# ========================================================================
# ETags
# ========================================================================


def calc_hexdigest(s):
    """Return md5 digest for a string."""
    s = to_bytes(s)
    return md5(s).hexdigest()  # return native string


def calc_base64(s):
    """Return base64 encoded binarystring."""
    s = to_bytes(s)
    s = base64.encodebytes(s).strip()  # return bytestring
    return to_str(s)


def checked_etag(etag, *, allow_none=False):
    """Validate etag string to ensure propare comparison.

    This function is used to assert that `DAVResource.get_etag()` does not add
    quotes, so it can be passed as `ETag: "<etag_value>"` header.
    Note that we also reject weak entity tags (W/"<etag_value>"), since WebDAV
    servers commonly use strong ETags.
    """
    if etag is None and allow_none:
        return None
    etag = etag.strip()
    if not etag or '"' in etag or etag.startswith("W/"):
        # This is an internal server error
        raise ValueError(f"Invalid ETag format: '{etag!r}'.")
    return etag


def parse_if_match_header(value):
    """Return a list of etag-values for a `If-Match` or `If-Not-Match` header.

    Remove enclosing quotes for easy comparison with the `DAVResource.get_etag()`
    results.
    We strip the weak-ETag prefix, because WebDAV servers commonly use strong
    ETags. If the client sends a weak tag, it should not hurt to compare
    against the resources strong etag however(?).
    """
    res = []
    for etag in value.split(","):
        etag = removeprefix(etag.strip(), "W/")
        if etag.startswith('"') and etag.endswith('"'):
            etag = etag[1:-1]
        if etag:
            res.append(etag)
        elif '"' in etag:
            # Client error
            raise DAVError(HTTP_BAD_REQUEST, f"Invalid ETag format: '{value!r}'.")
    return res


def get_file_etag(file_path):
    """Return a strong, unquoted Entity Tag for a (file)path.

    http://www.webdav.org/specs/rfc4918.html#etag

    Returns the following as entity tags::

        Non-file - md5(pathname)
        Win32 - md5(pathname)-lastmodifiedtime-filesize
        Others - inode-lastmodifiedtime-filesize
    """
    # (At least on Vista) os.path.exists returns False, if a file name contains
    # special characters, even if it is correctly UTF-8 encoded.
    # So we convert to unicode. On the other hand, md5() needs a byte string.
    if is_bytes(file_path):
        unicode_file_path = to_unicode_safe(file_path)
    else:
        unicode_file_path = file_path
        file_path = file_path.encode("utf8", "surrogateescape")

    if not os.path.isfile(unicode_file_path):
        return md5(file_path).hexdigest()

    fstat = os.stat(unicode_file_path)
    if sys.platform == "win32":
        etag = (
            f"{md5(file_path).hexdigest()}-{fstat[stat.ST_MTIME]}-{fstat[stat.ST_SIZE]}"
        )
    else:
        etag = f"{fstat[stat.ST_INO]}-{fstat[stat.ST_MTIME]}-{fstat[stat.ST_SIZE]}"
    return etag


# ========================================================================
# Ranges
# ========================================================================

# Range Specifiers
reByteRangeSpecifier = re.compile("(([0-9]+)-([0-9]*))")
reSuffixByteRangeSpecifier = re.compile("(-([0-9]+))")


def obtain_content_ranges(range_header, filesize):
    """
    See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Range

    Return tuple (range_list, total_length)

    range_list
        content ranges as values to their parsed components in the tuple
        (seek_position/abs position of first byte, abs position of last byte, num_of_bytes_to_read)
    total_length
        total length for Content-Length
    """
    list_ranges = []
    request_ranges = range_header.split(",")
    for subrange in request_ranges:
        is_matched = False
        if not is_matched:
            match = reByteRangeSpecifier.search(subrange)
            if match:
                range_start = int(match.group(2))

                if range_start >= filesize:
                    # TODO: set "Content-Range: bytes */filesize"
                    fail(
                        HTTP_RANGE_NOT_SATISFIABLE,
                        f"Requested range starts behind file size ({range_start} >= {filesize})",
                        add_headers=[("Content-Range", f"bytes */{filesize}")],
                    )

                if match.group(3) == "":
                    # "START-"
                    range_end = filesize - 1
                else:
                    # "START-END"
                    range_end = int(match.group(3))

                if range_start <= range_end and range_start < filesize:
                    if range_end >= filesize:
                        range_end = filesize - 1
                    list_ranges.append((range_start, range_end))
                    is_matched = True

        if not is_matched:
            match = reSuffixByteRangeSpecifier.search(subrange)
            if match:
                range_start = filesize - int(match.group(2))
                if range_start < 0:
                    range_start = 0
                range_end = filesize - 1
                list_ranges.append((range_start, range_end))
                is_matched = True

    # consolidate ranges
    list_ranges.sort()
    list_ranges_2 = []
    total_length = 0
    while len(list_ranges) > 0:
        (rfirstpos, rlastpos) = list_ranges.pop()
        counter = len(list_ranges)
        while counter > 0:
            (nfirstpos, nlastpos) = list_ranges[counter - 1]
            if nlastpos < rfirstpos - 1 or nfirstpos > nlastpos + 1:
                pass
            else:
                rfirstpos = min(rfirstpos, nfirstpos)
                rlastpos = max(rlastpos, nlastpos)
                del list_ranges[counter - 1]
            counter = counter - 1
        list_ranges_2.append((rfirstpos, rlastpos, rlastpos - rfirstpos + 1))
        total_length = total_length + rlastpos - rfirstpos + 1

    return (list_ranges_2, total_length)


# ========================================================================
#
# ========================================================================

#: any numofsecs above the following limit is regarded as infinite
MAX_FINITE_TIMEOUT_LIMIT = 10 * 365 * 24 * 60 * 60  # approx 10 years
reSecondsReader = re.compile(r"second\-([0-9]+)", re.I)


def read_timeout_value_header(timeoutvalue):
    """Return -1 if infinite, else return numofsecs."""
    timeoutsecs = 0
    timeoutvaluelist = timeoutvalue.split(",")
    for timeoutspec in timeoutvaluelist:
        timeoutspec = timeoutspec.strip()
        if timeoutspec.lower() == "infinite":
            return -1
        else:
            listSR = reSecondsReader.findall(timeoutspec)
            for secs in listSR:
                timeoutsecs = int(secs)
                if timeoutsecs > MAX_FINITE_TIMEOUT_LIMIT:
                    return -1
                if timeoutsecs != 0:
                    return timeoutsecs
    return None


# ========================================================================
# If Headers
# ========================================================================


def evaluate_http_conditionals(dav_res, last_modified, entity_tag, environ):
    """Handle 'If-...:' headers (but not 'If:' header).

    If-Match
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.24
        Only perform the action if the client supplied entity matches the
        same entity on the server. This is mainly for methods like
        PUT to only update a resource if it has not been modified since the
        user last updated it.
        If-Match: "737060cd8c284d8af7ad3082f209582d"
    If-Modified-Since
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.25
        Allows a 304 Not Modified to be returned if content is unchanged
        If-Modified-Since: Sat, 29 Oct 1994 19:43:31 GMT
    If-None-Match
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.26
        Allows a 304 Not Modified to be returned if content is unchanged,
        see HTTP ETag
        If-None-Match: "737060cd8c284d8af7ad3082f209582d"
    If-Unmodified-Since
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.28
        Only send the response if the entity has not been modified since a
        specific time.
    """
    if not dav_res:
        return
    # Conditions

    # An HTTP/1.1 origin server, upon receiving a conditional request that includes both a
    # Last-Modified date (e.g., in an If-Modified-Since or If-Unmodified-Since header field) and
    # one or more entity tags (e.g., in an If-Match, If-None-Match, or If-Range header field) as
    # cache validators, MUST NOT return a response status of 304 (Not Modified) unless doing so
    # is consistent with all of the conditional header fields in the request.

    if "HTTP_IF_MATCH" in environ and dav_res.support_etag():
        token_list = parse_if_match_header(environ["HTTP_IF_MATCH"])
        match = False
        for token in token_list:
            if token == entity_tag or token == "*":
                match = True
                break
        if not match:
            raise DAVError(HTTP_PRECONDITION_FAILED, "If-Match header condition failed")

    # TODO: after the refactoring
    ifModifiedSinceFailed = False
    if "HTTP_IF_MODIFIED_SINCE" in environ and dav_res.support_modified():
        ifmodtime = parse_time_string(environ["HTTP_IF_MODIFIED_SINCE"])
        if ifmodtime and ifmodtime > last_modified:
            ifModifiedSinceFailed = True

    # If-None-Match
    # If none of the entity tags match, then the server MAY perform the requested method as if the
    # If-None-Match header field did not exist, but MUST also ignore any If-Modified-Since header
    # field (s) in the request. That is, if no entity tags match, then the server MUST NOT return
    # a 304 (Not Modified) response.
    ignoreIfModifiedSince = False
    if "HTTP_IF_NONE_MATCH" in environ and dav_res.support_etag():
        token_list = parse_if_match_header(environ["HTTP_IF_NONE_MATCH"])
        for token in token_list:
            if token == entity_tag or token == "*":
                # ETag matched. If it's a GET request and we don't have an
                # conflicting If-Modified header, we return NOT_MODIFIED
                if (
                    environ["REQUEST_METHOD"] in ("GET", "HEAD")
                    and not ifModifiedSinceFailed
                ):
                    raise DAVError(HTTP_NOT_MODIFIED, "If-None-Match header failed")
                raise DAVError(
                    HTTP_PRECONDITION_FAILED, "If-None-Match header condition failed"
                )
        ignoreIfModifiedSince = True

    if "HTTP_IF_UNMODIFIED_SINCE" in environ and dav_res.support_modified():
        ifunmodtime = parse_time_string(environ["HTTP_IF_UNMODIFIED_SINCE"])
        if ifunmodtime and ifunmodtime < last_modified:
            raise DAVError(
                HTTP_PRECONDITION_FAILED, "If-Unmodified-Since header condition failed"
            )

    if ifModifiedSinceFailed and not ignoreIfModifiedSince:
        raise DAVError(HTTP_NOT_MODIFIED, "If-Modified-Since header condition failed")

    return


reIfSeparator = re.compile(r"(\<([^>]+)\>)|(\(([^\)]+)\))")
reIfHeader = re.compile(r"\<([^>]+)\>([^<]+)")
reIfTagList = re.compile(r"\(([^)]+)\)")
reIfTagListContents = re.compile(r"(\S+)")


def parse_if_header_dict(environ):
    """Parse HTTP_IF header into a dictionary and lists, and cache the result.

    @see http://www.webdav.org/specs/rfc4918.html#HEADER_If
    """
    if "wsgidav.conditions.if" in environ:
        return

    if "HTTP_IF" not in environ:
        environ["wsgidav.conditions.if"] = None
        environ["wsgidav.ifLockTokenList"] = []
        return

    iftext = environ["HTTP_IF"].strip()
    if not iftext.startswith("<"):
        iftext = "<*>" + iftext

    ifDict = dict([])
    ifLockList = []

    resource1 = "*"
    for tmpURLVar, URLVar, _tmpContentVar, contentVar in reIfSeparator.findall(iftext):
        if tmpURLVar != "":
            resource1 = URLVar
        else:
            listTagContents = []
            testflag = True
            for listitem in reIfTagListContents.findall(contentVar):
                if listitem.upper() != "NOT":
                    if listitem.startswith("["):
                        listTagContents.append(
                            (testflag, "entity", listitem.strip('"[]'))
                        )
                    else:
                        listTagContents.append(
                            (testflag, "locktoken", listitem.strip("<>"))
                        )
                        ifLockList.append(listitem.strip("<>"))
                testflag = listitem.upper() != "NOT"

            if resource1 in ifDict:
                listTag = ifDict[resource1]
            else:
                listTag = []
                ifDict[resource1] = listTag
            listTag.append(listTagContents)

    environ["wsgidav.conditions.if"] = ifDict
    environ["wsgidav.ifLockTokenList"] = ifLockList
    _logger.debug(f"parse_if_header_dict\n{pformat(ifDict)}")
    return


def test_if_header_dict(dav_res, if_dict, fullurl, locktoken_list, entity_tag):
    _logger.debug(f"test_if_header_dict({fullurl}, {locktoken_list}, {entity_tag})")

    if fullurl in if_dict:
        listTest = if_dict[fullurl]
    elif "*" in if_dict:
        listTest = if_dict["*"]
    else:
        return True

    #    supportEntityTag = dav.isInfoTypeSupported(path, "etag")
    supportEntityTag = dav_res.support_etag()
    for listTestConds in listTest:
        matchfailed = False

        for testflag, checkstyle, checkvalue in listTestConds:
            if checkstyle == "entity" and supportEntityTag:
                testresult = entity_tag == checkvalue
            elif checkstyle == "entity":
                testresult = testflag
            elif checkstyle == "locktoken":
                testresult = checkvalue in locktoken_list
            else:  # unknown
                testresult = True
            checkresult = testresult == testflag
            if not checkresult:
                matchfailed = True
                break
        if not matchfailed:
            return True
    _logger.debug("  -> FAILED")
    return False


# test_if_header_dict.__test__ = False  # Tell nose to ignore this function


# ========================================================================
# guess_mime_type
# ========================================================================
_MIME_TYPES = {
    ".oga": "audio/ogg",
    ".ogg": "audio/ogg",
    ".ogv": "video/ogg",
    ".webm": "video/webm",
    # https://mailarchive.ietf.org/arch/msg/media-types/DA8UuKX2dyaVxWh-oevy-t3Vg9Q/
    ".yml": "application/yaml",
    ".yaml": "application/yaml",
}


def guess_mime_type(url):
    """Use the mimetypes module to lookup the type for an extension.

    This function also adds some extensions required for HTML5
    """
    (mimetype, _mimeencoding) = mimetypes.guess_type(url)
    if not mimetype:
        ext = os.path.splitext(url)[1]
        mimetype = _MIME_TYPES.get(ext)
        _logger.debug(f"mimetype({url}): {mimetype}")
    if not mimetype:
        mimetype = "application/octet-stream"
    return mimetype
