# (c) 2009-2015 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Small wrapper for different etree packages.

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://wsgidav.readthedocs.org/en/latest/develop.html  
"""
import sys

__docformat__ = "reStructuredText"


try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# Import XML support
useLxml = False
try:
    from lxml import etree
    useLxml = True
except ImportError:
    try:    
        # Try xml module (Python 2.5 or later) 
        from xml.etree import ElementTree as etree
        # print "WARNING: Could not import lxml: using xml instead (slower). Consider installing lxml from http://codespeak.net/lxml/."
    except ImportError:
        try:
            # Try elementtree (http://effbot.org/zone/element-index.htm) 
            from elementtree import ElementTree as etree
        except ImportError:
            print "ERROR: Could not import lxml, xml, nor elementtree. Consider installing lxml from http://codespeak.net/lxml/ or update to Python 2.5 or later."
            raise


#===============================================================================
# XML
#===============================================================================

def stringToXML(text):
    """Convert XML string into etree.Element."""
    try:
        return etree.XML(text)
    except Exception, e:
        # TODO:
        # ExpatError: reference to invalid character number: line 1, column 62
        # litmus fails, when xml is used instead of lxml
        # 18. propget............... FAIL (PROPFIND on `/temp/litmus/prop2': Could not read status line: connection was closed by server)
        # text = <ns0:high-unicode xmlns:ns0="http://example.com/neon/litmus/">&#55296;&#56320;</ns0:high-unicode>
#        t2 = text.encode("utf8")
#        return etree.XML(t2)
        print >>sys.stderr, "Error parsing XML string. If lxml is not available, and unicode is involved, then installing it _may_ solve this issue."
        raise


def xmlToString(element, pretty_print=False):
    """Wrapper for etree.tostring, that takes care of unsupported pretty_print 
    option and prepends an encoding header."""
    if useLxml:
        xml = etree.tostring(element, 
                             encoding="UTF-8", 
                             xml_declaration=True, 
                             pretty_print=pretty_print)
    else:
        xml = etree.tostring(element, "UTF-8")
    assert xml.startswith("<?xml ")

    # Fix for Total Commander WebDAV plugin
    # Without it all nodes with non-ascii characters in naming look incorrect
    # You can download sources of WebDAV TC plugin using this link: http://www.ghisler.com/plugins.htm
    # and find the mistake in file davfunc.cpp on line 2663:
    # if (p) {
	#	p+=9;
	#	while (p[0]=='"' || p[0]==' ' || p[0]=='\r' || p[0]=='\n' || p[0]=='\t')
	#		p++;
	#	if (strnicmp(p,"utf-8",5)==0)
	#		return BODY_UTF8;
	# }
    # So plugin couldn't detect correct charset because it depends on "utf-8" string in first XML tag
    # but lxml.etree object generates xml structure with only single quotes and TC WebDAV plugin doesn't understand it
    pos = xml.find('?>')
    if pos != -1:
        xml_declaration_old = xml[:pos+2]
        xml_declaration_new = xml_declaration_old.replace("'", '"')
        xml = xml.replace(xml_declaration_old, xml_declaration_new, 1)

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
    stream = StringIO()
    for childnode in element:
        print >>stream, xmlToString(childnode, pretty_print=False)
    s = stream.getvalue()
    stream.close()
    return s


#===============================================================================
# TEST
#===============================================================================
    
if __name__ == "__main__":
    pass
