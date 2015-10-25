# (c) 2009-2015 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Small wrapper for different etree packages.

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://wsgidav.readthedocs.org/en/latest/develop.html  
"""
from __future__ import print_function

import sys

__docformat__ = "reStructuredText"


from wsgidav import compat

# Import XML support
useLxml = False
try:
    from lxml import etree
    useLxml = True
except ImportError:
    # Try xml module (Python 2.5 or later) 
    from xml.etree import ElementTree as etree
    print("WARNING: Could not import lxml: using xml instead (slower). Consider installing lxml from http://codespeak.net/lxml/.")


#===============================================================================
# XML
#===============================================================================

def stringToXML(text):
    """Convert XML string into etree.Element."""
    try:
        return etree.XML(text)
    except Exception:
        # TODO:
        # ExpatError: reference to invalid character number: line 1, column 62
        # litmus fails, when xml is used instead of lxml
        # 18. propget............... FAIL (PROPFIND on `/temp/litmus/prop2': Could not read status line: connection was closed by server)
        # text = <ns0:high-unicode xmlns:ns0="http://example.com/neon/litmus/">&#55296;&#56320;</ns0:high-unicode>
#        t2 = text.encode("utf8")
#        return etree.XML(t2)
        print("Error parsing XML string. If lxml is not available, and unicode is involved, then installing lxml _may_ solve this issue.", file=sys.stderr)
        print("XML source:", text, file=sys.stderr)
        raise


def xmlToBytes(element, pretty_print=False):
    """Wrapper for etree.tostring, that takes care of unsupported pretty_print 
    option and prepends an encoding header."""
    if useLxml:
        xml = etree.tostring(element, 
                             encoding="UTF-8", 
                             xml_declaration=True, 
                             pretty_print=pretty_print)
    else:
        xml = etree.tostring(element, encoding="UTF-8")
        if not xml.startswith(b"<?xml "):
            xml = b'<?xml version="1.0" encoding="utf-8" ?>\n' + xml

    assert xml.startswith(b"<?xml ")  # ET should prepend an encoding header
    return xml


def makeMultistatusEL():
    """Wrapper for etree.Element, that takes care of unsupported nsmap option."""
    if useLxml:
        return etree.Element("{DAV:}multistatus", nsmap={"D": "DAV:"})
    return etree.Element("{DAV:}multistatus")


def makePropEL():
    """Wrapper for etree.Element, that takes care of unsupported nsmap option."""
    if useLxml:
        return etree.Element("{DAV:}prop", nsmap={"D": "DAV:"})
    return etree.Element("{DAV:}prop")


def makeSubElement(parent, tag, nsmap=None):
    """Wrapper for etree.SubElement, that takes care of unsupported nsmap option."""
    if useLxml:
        return etree.SubElement(parent, tag, nsmap=nsmap)
    return etree.SubElement(parent, tag)


def elementContentAsString(element):
    """Serialize etree.Element.
    
    Note: element may contain more than one child or only text (i.e. no child 
          at all). Therefore the resulting string may raise an exception, when
          passed back to etree.XML(). 
    """
    if len(element) == 0:
        return element.text or ""  # Make sure, None is returned as '' 
    stream = compat.StringIO()
    for childnode in element:
        print(xmlToBytes(childnode, pretty_print=False), file=stream)
    s = stream.getvalue()
    stream.close()
    return s


#===============================================================================
# TEST
#===============================================================================
    
if __name__ == "__main__":
    pass
