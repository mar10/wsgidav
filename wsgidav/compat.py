# (c) 2009-2015 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Tool functions to support Python 2 and 3.
"""
from __future__ import print_function

import sys

__docformat__ = "reStructuredText"


IS_PY2 = sys.version_info < (3, 0)
IS_PY3 = not IS_PY2

# six_xrange = range if IS_PY3 else xrange

try:
    console_input = raw_input
except NameError:
    console_input = input

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO  # py3

try:
    from urllib.parse import urlparse  # py3
except ImportError:
    from urlparse import urlparse

try:
    xrange = xrange # py2
except NameError:
    xrange = range  # py3


if IS_PY2:
    def is_basestring(s):
        """Return True for any string type, i.e. for str/unicode on Py2 and bytes/str on Py3."""
        return isinstance(s, basestring)

    def is_binary(s):
        """Return True for binary strings, i.e. for str on Py2 and bytes on Py3."""
        return isinstance(s, str)

    def is_text(s):
        """Return True for unicode strings, i.e. for unicode on Py2 and str on Py3."""
        return isinstance(s, unicode)

    def to_binary(s, encoding="utf8"):
        """Convert unicode (text strings) to binary data, i.e. str on Py2 and bytes on Py3."""
        if type(s) is not str:
            s = s.encode(encoding)
        return s
    
    to_str = to_binary
    """Convert data to native str, i.e. binary on Py2 and text on Py3."""

    def to_text(s, encoding="utf8"):
        """Convert data to unicode text, i.e. unicode on Py2 and str on Py3."""
        if type(s) is not unicode:
            s = unicode(s, encoding)
        return s

    b_empty = ""
    b_slash = "/"

else:   # Python 3

    def is_basestring(s):
        """Return True for any string type, i.e. for str/unicode on Py2 and bytes/str on Py3."""
        return isinstance(s, (str, bytes))

    def is_binary(s):
        """Return True for binary strings, i.e. for str on Py2 and bytes on Py3."""
        return isinstance(s, bytes)

    def is_text(s):
        """Return True for unicode strings, i.e. for unicode on Py2 and str on Py3."""
        return isinstance(s, str)

    def to_binary(s, encoding="utf8"):
        """Convert unicode (text strings) to binary data, i.e. str on Py2 and bytes on Py3."""
        if type(s) is str:
            s = bytes(s, encoding)
        return s
    
    def to_str(s, encoding="utf8"):
        """Convert binary data to unicode (text strings) on Python 2 and 3."""
        if type(s) is bytes:
            s = str(s, encoding)
        return s 

    to_text = to_str
    """Convert binary data to unicode (text strings) on Python 2 and 3."""

    b_empty = b""
    b_slash = b"/"
