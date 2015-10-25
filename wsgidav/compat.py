# (c) 2009-2015 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Tool functions to support Python 2 and 3.

Inspired by six https://pythonhosted.org/six/
"""
from __future__ import print_function

import sys

__docformat__ = "reStructuredText"


PY2 = sys.version_info < (3, 0)
PY3 = not PY2
_filesystemencoding = sys.getfilesystemencoding()


try:
    console_input = raw_input
except NameError:
    console_input = input

try:
    from cStringIO import StringIO
    BytesIO = StringIO
except ImportError:
    from io import StringIO  # py3
    from io import BytesIO  # py3

try:
    from urllib.parse import quote, unquote, urlparse  # py3
except ImportError:
    from urllib import quote, unquote
    from urlparse import urlparse

try:
    xrange = xrange # py2
except NameError:
    xrange = range  # py3


# String Abstractions

if PY2:

    def is_basestring(s):
        """Return True for any string type, i.e. for str/unicode on Py2 and bytes/str on Py3."""
        return isinstance(s, basestring)

    def is_bytes(s):
        """Return True for bytestrings, i.e. for str on Py2 and bytes on Py3."""
        return isinstance(s, str)

    def is_native(s):
        """Return True for native strings, i.e. for str on Py2 and Py3."""
        return isinstance(s, str)

    def is_unicode(s):
        """Return True for unicode strings, i.e. for unicode on Py2 and str on Py3."""
        return isinstance(s, unicode)

    def to_bytes(s, encoding="utf8"):
        """Convert unicode (text strings) to binary data, i.e. str on Py2 and bytes on Py3."""
        if type(s) is unicode:
            s = s.encode(encoding)
        elif type(s) is not str:
            s = str(s)
        return s
    
    to_native = to_bytes
    """Convert data to native str type, i.e. bytestring on Py2 and unicode on Py3."""

    def to_unicode(s, encoding="utf8"):
        """Convert data to unicode text, i.e. unicode on Py2 and str on Py3."""
        if type(s) is not unicode:
            s = unicode(s, encoding)
        return s

else:   # Python 3

    def is_basestring(s):
        """Return True for any string type, i.e. for str/unicode on Py2 and bytes/str on Py3."""
        return isinstance(s, (str, bytes))

    def is_bytes(s):
        """Return True for bytestrings, i.e. for str on Py2 and bytes on Py3."""
        return isinstance(s, bytes)

    def is_native(s):
        """Return True for native strings, i.e. for str on Py2 and Py3."""
        return isinstance(s, str)

    def is_unicode(s):
        """Return True for unicode strings, i.e. for unicode on Py2 and str on Py3."""
        return isinstance(s, str)

    def to_bytes(s, encoding="utf8"):
        """Convert a text string (unicode) to bytestring, i.e. str on Py2 and bytes on Py3."""
        if type(s) is not bytes:
            s = bytes(s, encoding)
        return s
    
    def to_native(s, encoding="utf8"):
        """Convert data to native str type, i.e. bytestring on Py2 and unicode on Py3."""
        if type(s) is not str:
            s = str(s, encoding)
        return s 

    to_unicode = to_native
    """Convert binary data to unicode (text strings) on Python 2 and 3."""


# Binary Strings

b_empty = to_bytes("")
b_slash = to_bytes("/")


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
