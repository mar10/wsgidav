# -*- coding: utf-8 -*-
# (c) 2009-2021 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Tool functions dealing with strings and bytes (former comaptibility layer for Python 2/3).
"""

import sys

__docformat__ = "reStructuredText"

_filesystemencoding = sys.getfilesystemencoding()

# String Abstractions


def is_basestring(s):
    """Return True for any string type (for str/unicode on Py2 and bytes/str on Py3)."""
    return isinstance(s, (str, bytes))


def is_bytes(s):
    """Return True for bytestrings (for str on Py2 and bytes on Py3)."""
    return isinstance(s, bytes)


def is_str(s):
    """Return True for native strings (for str on Py2 and Py3)."""
    return isinstance(s, str)


# is_native = is_str
# is_unicode = is_str


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


# to_native = to_str
# to_unicode = to_str


# Binary Strings

# b_empty = b""
# b_slash = b"/"


# WSGI support


def unicode_to_wsgi(u):
    """Convert an environment variable to a WSGI 'bytes-as-unicode' string."""
    # Taken from PEP3333; the server should already have performed this, when
    # passing environ to the WSGI application
    return u.encode(_filesystemencoding, "surrogateescape").decode("iso-8859-1")


def wsgi_to_bytes(s):
    """Convert a native string to a WSGI / HTTP compatible byte string."""
    # Taken from PEP3333
    return s.encode("iso-8859-1")
