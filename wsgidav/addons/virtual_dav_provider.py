"""
:Author: Martin Wendt
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Sample implementation of a DAV provider that provides a browsable, 
multi-categorized resource tree (read-only).

This is a dummy 'database', that serves as an example source for the
VirtualResourceProvider.

The *database* is a simple hard coded variable ``_resourceData``, that contains 
a list of resource dictionaries.

Every resource has these attributes:

title
    resource name
key
    unique key 


Compared to a published file system, we have these main differences:

  1. The same resource may be referenced using different paths
     One path is considered the real-path, all others are virtual-paths
  2. A resource is served as a HTML file, that contains some data, as well as
     a link to the real file content.
 
When accessed using WebDAV, the following URLs both return the same resource 
'spec.doc'::

  <realm>/ou/development/spec.doc
  <realm>/type/doc/spec.doc

In general, a URL is interpreted like this::

  /<category-type>/<category>/<name>

A resource is served as an descriptive HTML file, which is generated 
on-the-fly. 
Resources may contain files, which are linked from the HTML file.
By appending "/content", it is possible to address the file data::

  /<category-type>/<category>/<name>/content

Additionally the special category-type *key* can be used to address a resource 
(or resource content) by key:: 

  /by_key/<key>
  /by_key/<key>/content

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
import stat
import os
import mimetypes
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport
from wsgidav.dav_provider import DAVProvider
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN, HTTP_NOT_FOUND
from wsgidav import util

__docformat__ = "reStructuredText en"


#===============================================================================
# Tool functions
#===============================================================================


#===============================================================================
# Fake hierarchical repository
#===============================================================================
_browsableCategories = ("ou",
                        "type",
                        )
_realCategory = "by_key"
_alllowedCategories = _browsableCategories + (_realCategory, )
_contentSegment = "content" 

FILE_FOLDER = r"c:\temp\virtfiles"

_resourceData = [
    {"key": "1", "title": "My URS", 
     "ou": "development", "type": "doc", 
     "file": FILE_FOLDER + r"\My URS.doc"},
    {"key": "2", "title": "Spec", 
     "ou": "development", "type": "doc", 
     "file": FILE_FOLDER + r"\Spec.doc"},
    {"key": "3", "title": "Fact sheet", 
     "ou": "marketing", "type": "doc", 
     "file": FILE_FOLDER + r"\Fact sheet.doc"},
    {"key": "4", "title": "Presentation", 
     "ou": "marketing", "type": "ppt", 
     "file": FILE_FOLDER + r"\Presentation.ppt"},
    {"key": "5", "title": "handbook", 
     "ou": "development", "type": "pdf", 
     "file": FILE_FOLDER + r"\handbook.pdf"},
    {"key": "6", "title": "source code", 
     "ou": "development", "type": "link", 
     "file": FILE_FOLDER + r"\source code.link"},
    ]


#===============================================================================
# _VirtualResource
#===============================================================================
class _VirtualResource(object):
    def __init__(self):
        pass
    def isCollection(self):
        return False
    def getContent(self):
        return None
    def getContentType(self):
        return None
    def getContentLength(self):
        return None
    def getCreationDate(self):
        return None
    def getModifiedDate(self):
        return None


class VirtualResCollection(_VirtualResource):
    def __init__(self, entryList):
        self.entryList = entryList
    def isCollection(self):
        return True


class VirtualResource(_VirtualResource):
    def __init__(self, dict):
        self.data = dict
    def getContent(self):
        html = """\
        <html><head>
        <title>%(title)s</title>
        </head><body>
        <h1>%(title)s</h1>
        <table>
        <tr>
            <td>Type</td>
            <td>%(type)s</td>
        </tr><tr>
            <td>Orga unit</td>
            <td>%(ou)s</td>
        </tr><tr>
            <td>Link</td>
            <td><a href='/by_key/%(key)s/content'>File content</a>
            <a href='%(title)s/content'>File content2</a>
            </td>
        </tr><tr>
            <td>Key</td>
            <td>%(key)s</td>
        </tr>
        </table>
        <p>This is a virtual WsgiDAV resource called '%(title)s'.</p>
        </body></html>""" % self.data
        return StringIO(html)
    def getContentType(self):
        return "text/html"
    def getContentLength(self):
        return len(self.getContent().read())
    def getCreationDate(self):
        return None
    def getModifiedDate(self):
        return None


class VirtualResFile(_VirtualResource):
    def __init__(self, dict):
        self.data = dict
    def getContent(self):
        fp = self.data["file"]
        mime = self.getContentType()
        if mime.startswith("text"):
            return file(fp, "r", BUFFER_SIZE)
        else:
            return file(fp, "rb", BUFFER_SIZE)
    def getContentType(self):
        fp = self.data["file"]
        if not os.path.isfile(fp):
            return "text/html"
        (mimetype, _mimeencoding) = mimetypes.guess_type(fp) 
        if not mimetype:
            mimetype = "application/octet-stream" 
        return mimetype
    def getContentLength(self):
        fp = self.data["file"]
        statresults = os.stat(fp)
        return statresults[stat.ST_SIZE]      
    def getCreationDate(self):
        fp = self.data["file"]
        statresults = os.stat(fp)
        return statresults[stat.ST_CTIME]      
    def getModifiedDate(self):
        fp = self.data["file"]
        statresults = os.stat(fp)
        return statresults[stat.ST_MTIME]      


        
         
#===============================================================================
# VirtualResourceProvider
#===============================================================================
BUFFER_SIZE = 8192

class VirtualResourceProvider(DAVProvider):
    """
    Serve a VirtualResource derived structure for WsgiDAV.
    """
    def __init__(self):
        super(VirtualResourceProvider, self).__init__()
        # TODO: this is just for demonstration:
        self.resourceData = _resourceData


    def _getResByPath(self, path):
        """Return _VirtualResource object for a path.
        
        path is expected to be 
            categoryType/category/name
        for example:
            'ou/development/spec.doc'
        """
        assert not "\\" in path
        
        catType, cat, resName, contentSpec = util.saveSplit(path.strip("/"), "/", 3)
    
#        print "_getResByPath('%s'): catType=%s, cat=%s, resName=%s" % (path, catType, cat, resName)
        
        if catType and catType not in _alllowedCategories:
            raise DAVError(HTTP_NOT_FOUND, "Unknown category type '%s'" % catType)

        if catType == _realCategory:
            # Accessing /by_key/<key> or /by_key/<key>/content
            for data in _resourceData:
                if data["key"] == cat:
                    if resName == "content":
                        return VirtualResFile(data)
                    return VirtualResource(data)
            raise DAVError(HTTP_NOT_FOUND, "Unknown key '%s'" % cat)
            
        elif resName:
            # Accessing /<catType>/<cat>/<name> or /<catType>/<cat>/<name>/??
            res = None
            for data in _resourceData:
                if data.get(catType) == cat and data["title"] == resName:
                    res = data
                    break
            if not res:
                raise DAVError(HTTP_NOT_FOUND)
            if contentSpec == _contentSegment:
                # Accessing /<catType>/<cat>/<name>/content
                return VirtualResFile(res) 
            elif contentSpec:
                # Accessing /<catType>/<cat>/<name>/??
                raise DAVError(HTTP_NOT_FOUND)
            # Accessing /<catType>/<cat>/<name>
            return VirtualResource(res) 
                 
        elif cat:
            # Accessing /catType/cat: return list of matching names
            resList = [ data["title"] for data in _resourceData if data.get(catType) == cat ]
            return VirtualResCollection(resList)
        
        elif catType: 
            # Accessing /catType/: return all possible values for this catType
            if catType in _browsableCategories:
                resList = []
                for data in _resourceData:
                    if not data[catType] in resList:
                        resList.append(data[catType])
                return VirtualResCollection(resList)
            # Known category type, but not browsable (e.g. 'by_key')
            raise DAVError(HTTP_FORBIDDEN)
                 
        # Accessing /: return list of categories
        return VirtualResCollection(_browsableCategories)
        
    
    def getMemberNames(self, path):
        res = self._getResByPath(path)
#        names = [ e+".html" for e in res.entryList ]
#        return names
        return res.entryList


    def getSupportedInfoTypes(self, path):
        """Return a list of supported information types.
        
        See DAVProvider.getSupportedInfoTypes()
        """
        res = self._getResByPath(path)
        infoTypes = ["isCollection",
                     "displayName", 
                     "displayType", 
                    ]
        if not res.isCollection(): 
            infoTypes.append("contentType")
            infoTypes.append("contentLength")
            infoTypes.append("etag")
        if isinstance(res, VirtualResFile):
            infoTypes.append("created")
            infoTypes.append("modified")

        return infoTypes

    
    def getInfoDict(self, path, typeList=None):
        """Return info dictionary for path.

        See DAVProvider.getInfoDict()
        """
        res = self._getResByPath(path)
        if res is None:
            return None
        # Early out,if typeList is [] (i.e. test for resource existence only)
        if not (typeList or typeList is None):
            return {} 
        isCollection = res.isCollection()
        name = util.getUriName(self.getPreferredPath(path))

        if isCollection:
            displayType = "Category"
        else:
            displayType = "%s-File" % res.data["type"]
        
        dict = {"contentLength": None,
                "contentType": None,
                "name": name,
                "displayName": name,
                "displayType": displayType,
                "etag": util.getETag(path),
                "modified": res.getModifiedDate(),
                "created": res.getCreationDate(),
                "supportRanges": False,
                "isCollection": isCollection, 
                }
#        fp = res.data.get("file")
#        statresults = os.stat(fp)
        # Some resource-only infos: 
        if not isCollection:
#            dict["etag"] = util.getETag(file path), # TODO: should be using the file path here
            dict["contentType"] = res.getContentType()
            dict["contentLength"] = res.getContentLength()
            dict["supportRanges"] = True

        return dict

    
    def exists(self, path):
        res = self._getResByPath(path)
        return res is not None
    
    
    def isCollection(self, path):
        res = self._getResByPath(path)
        return res and res.isCollection()
    
    
    def isResource(self, path):
        res = self._getResByPath(path)
        return res and not res.isCollection()
    
    
    def createCollection(self, path):
        raise DAVError(HTTP_FORBIDDEN)               
    

    def deleteCollection(self, path):
        raise DAVError(HTTP_FORBIDDEN)               

    
    def openResourceForRead(self, path):
        res = self._getResByPath(path)
        return res.getContent()
