# -*- coding: iso-8859-1 -*-
"""
:Author: Martin Wendt
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Sample implementation of a DAV provider that provides a browsable, 
multi-categorized resource tree (read-only).

Compared to a published file system, we have these main differences:

  1. The same resource may be referenced using different paths
     One path is considered the real-path, all others are virtual-paths
  2. A resource is served as a HTML file, that contains some data, as well as
     a link to the real file content.
  3. Some paths may be hidden, i.e. by_key is not browsable (but can be referenced)
     TODO: is this WebDAV compliant? 
 
The Layout is built like this::

    <share>\
        category1_name\
            category1_key\
                Resource title\
                    Artifact name\

For example::
            
    <share>\
        by_tag\
            cool\
                My doc 1\
                    .Info.html
                    .Info.txt
                    .Description.txt
                    MySpec.pdf
                    MySpec.doc
                My doc 2\
            hot\
                My doc 1\
                My doc 2\
            nice\
                My doc 2\
                My doc 3
        by_orga\
            development\
                My doc 3\
            marketing\
                My doc 1\
                My doc 2\
        by_status\
            draft\
                My doc 2
            published\
                My doc 1
                My doc 3
        by_key\
            1\
            2\
            3\
When accessed using WebDAV, the following URLs both return the same resource 
'spec.doc'::

  <realm>/ou/development/spec.doc
  <realm>/type/doc/spec.doc

In general, a URL is interpreted like this::

  /<category-type>/<category>/<name>

The *database* is a simple hard coded variable ``_resourceData``, that contains 
a list of resource dictionaries.

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
import urllib


import stat
import os
import mimetypes
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport
from wsgidav.dav_provider import DAVProvider, DAVResource
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN, HTTP_INTERNAL_ERROR
from wsgidav import util

__docformat__ = "reStructuredText en"

_logger = util.getModuleLogger(__name__)

#===============================================================================
# Fake hierarchical repository
#===============================================================================
"""
This is a dummy 'database', that serves as an example source for the
VirtualResourceProvider.

All files listed in resPathList are expected to exist in FILE_FOLDER.
"""
_browsableCategories = ("by_orga",
                        "by_tag",
                        "by_status",
                        )
_realCategory = "by_key"
_alllowedCategories = _browsableCategories + (_realCategory, )
_artifactNames = [".Info.txt", ".Info.html", ".Description.txt" ] #, ".Admin.html"]

FILE_FOLDER = r"c:\temp\virtfiles"

_resourceData = [
    {"key": "1", 
     "title": "My doc 1", 
     "orga": "development", 
     "tags": ["cool", "hot"],
     "status": "draft",
     "description": "This resource contains two specification files.", 
     "resPathList": [os.path.join(FILE_FOLDER, "MySpec.doc"),
                     os.path.join(FILE_FOLDER, "MySpec.pdf"),
                     ],
     },
    {"key": "2", 
     "title": "My doc 2", 
     "orga": "development", 
     "tags": ["cool", "nice"],
     "status": "published",
     "description": "This resource contains one file.", 
     "resPathList": [os.path.join(FILE_FOLDER, "My URS.doc"),
                     ],
     },
    {"key": "3", 
     "title": u"My doc (euro:\u20AC, uuml:ü€)".encode("utf8"), 
     "orga": "marketing", 
     "tags": ["nice"],
     "status": "published",
     "description": "Long text describing it", 
     "resPathList": [os.path.join(FILE_FOLDER, "My URS.doc"),
                     ],
     },
    ]


def _getResListByAttr(attrName, attrVal):
    """"""
    assert attrName in _browsableCategories
    if attrName == "by_status":
        return [ data for data in _resourceData if data.get("status") == attrVal ]
    elif attrName == "by_orga":
        resList =[ data for data in _resourceData if data.get("orga") == attrVal ]
    elif attrName == "by_tag":
        resList =[ data for data in _resourceData if attrVal in data.get("tags") ]
    return resList
    

def _getResByKey(key):
    """"""
    for data in _resourceData:
        if data["key"] == key:
            return data
    return None
    



#===============================================================================
# _VirtualResource classes
#===============================================================================
class _VirtualResource(DAVResource):
    """Abstract base class for all resources."""
    def __init__(self):
        pass

    def isCollection(self):
        raise NotImplementedError()
    def name(self):
        return util.getUriName(self.path)

    def contentLength(self):
        return None
    def contentType(self):
        return None
    def created(self):
        return None
    def displayName(self):
        return self.name()
    def displayType(self):
        raise NotImplementedError()
    def etag(self):
        return None
    def modified(self):
        return None
    def supportRanges(self):
        return False


class VirtualResCollection(_VirtualResource):
    """Collection type resource, that contains a list of names."""
    def __init__(self, provider, path, nameList):
        self.provider = provider
        self.path = path
        self._nameList = nameList
    def isCollection(self):
        return True
    def displayType(self):
        return "Category"
    def getMemberNames(self):
        return self._nameList


class VirtualResource(_VirtualResource):
    """A virtual 'resource', displayed as a collection of artifacts and files."""
    def __init__(self, provider, path, data):
        self.provider = provider
        self.path = path
        self._data = data
        self._nameList = _artifactNames[:] # Use a copy
        for f in data["resPathList"]:
            self._nameList.append(os.path.basename(f))
    def displayType(self):
        return "Resource folder"
    def isCollection(self):
        return True
    
    def getRefUrl(self):
        refPath = "/by_key/%s" % self._data["key"] 
        return urllib.quote(self.provider.sharePath + refPath)
    
    def getMemberNames(self):
        return self._nameList


class VirtualArtifact(_VirtualResource):
    """A virtual file, containing resource descriptions."""
    def __init__(self, provider, path, data, name):
        assert name in _artifactNames
        self.provider = provider
        self.path = path
        self._data = data
        self._name = name

    def contentLength(self):
        return len(self.getContent().read())
    def contentType(self):
        if self._name.endswith(".txt"):
            return "text/plain"
        return "text/html"
    def displayType(self):
        return "Virtual info file"
    def isCollection(self):
        return False
    def name(self):
        return self._name

    def getRefUrl(self):
        refPath = "/by_key/%s/%s" % (self._data["key"], self._name)
        return urllib.quote(self.provider.sharePath + refPath)
 
    def getContent(self):
        fileLinks = [ "<a href='%s'>%s</a>\n" % (os.path.basename(f), f) for f in self._data["resPathList"] ]
        dict = self._data.copy()
        dict["fileLinks"] = ", ".join(fileLinks)
        if self._name == ".Info.html":
            html = """\
            <html><head>
            <title>%(title)s</title>
            </head><body>
            <h1>%(title)s</h1>
            <table>
            <tr>
                <td>Description</td>
                <td>%(description)s</td>
            </tr><tr>
                <td>Status</td>
                <td>%(status)s</td>
            </tr><tr>
                <td>Tags</td>
                <td>%(tags)s</td>
            </tr><tr>
                <td>Orga unit</td>
                <td>%(orga)s</td>
            </tr><tr>
                <td>Files</td>
                <td>%(fileLinks)s</td>
            </tr><tr>
                <td>Key</td>
                <td>%(key)s</td>
            </tr>
            </table>
            <p>This is a virtual WsgiDAV resource called '%(title)s'.</p>
            </body></html>""" % dict
        elif self._name == ".Info.txt":
            lines = [self._data["title"],
                     "=" * len(self._data["title"]),
                     self._data["description"],
                     "",
                     "Status: %s" % self._data["status"],
                     "Orga:   %8s" % self._data["orga"],
                     "Tags:   '%s'" % "', '".join(self._data["tags"]),
                     "Key:    %s" % self._data["key"],
                     ] 
            html = "\n".join(lines)
        elif self._name == ".Description.txt":
            html = self._data["description"]
        else:
            raise DAVError(HTTP_INTERNAL_ERROR, "Invalid artifact '%s'" % self._name)
        return StringIO(html)


class VirtualResFile(_VirtualResource):
    """Represents an existing file, that is a member of a VirtualResource."""
    def __init__(self, provider, path, data, filePath):
#        assert os.path.exists(filePath)
        self.provider = provider
        self.path = path
        self._data = data
        self.filePath = filePath

    def contentLength(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_SIZE]      
    def contentType(self):
        if not os.path.isfile(self.filePath):
            return "text/html"
        (mimetype, _mimeencoding) = mimetypes.guess_type(self.filePath) 
        if not mimetype:
            mimetype = "application/octet-stream" 
        return mimetype
    def created(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_CTIME]      
    def displayType(self):
        return "Content file"
    def isCollection(self):
        return False
    def modified(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_MTIME]      

    def getRefUrl(self):
        refPath = "/by_key/%s/%s" % (self._data["key"], os.path.basename(self.filePath))
        return urllib.quote(self.provider.sharePath + refPath)

    def getContent(self):
        mime = self.contentType()
        if mime.startswith("text"):
            return file(self.filePath, "r", BUFFER_SIZE)
        return file(self.filePath, "rb", BUFFER_SIZE)


        
         
#===============================================================================
# VirtualResourceProvider
#===============================================================================
BUFFER_SIZE = 8192

class VirtualResourceProvider(DAVProvider):
    """
    DAV provider that serves a VirtualResource derived structure.
    """
    def __init__(self):
        super(VirtualResourceProvider, self).__init__()
        self.resourceData = _resourceData
        

    def getResourceInst(self, path):
        """Return a DAVResource object for path.

        Return _VirtualResource object for a path.
        
        path is expected to be 
            categoryType/category/name/artifact
        for example:
            'by_tag/cool/My doc 2/info.html'

        See DAVProvider.getResourceInst()
        """
        self._count_getResourceInst += 1
        
        catType, cat, resName, contentSpec = util.saveSplit(path.strip("/"), "/", 3)
    
        _logger.info("getResourceInst('%s'): catType=%s, cat=%s, resName=%s" % (path, catType, cat, resName))
        
        if catType and catType not in _alllowedCategories:
            return None
    
        if catType == _realCategory:
            # Accessing /by_key/<key>
            data = _getResByKey(cat)
            if data:
                return VirtualResource(self, path, data)
            return None
            
        elif resName:
            # Accessing /<catType>/<cat>/<name> or /<catType>/<cat>/<name>/<contentSpec>
            res = None
            for data in _getResListByAttr(catType, cat):
                if data["title"] == resName:
                    res = data
                    break
            if not res:
                return None
            # Accessing /<catType>/<cat>/<name>
            if contentSpec in _artifactNames:
                # Accessing /<catType>/<cat>/<name>/.info.html, or similar
                return VirtualArtifact(self, path, res, contentSpec)
            elif contentSpec:
                # Accessing /<catType>/<cat>/<name>/<file-name>
                for f in res["resPathList"]:
                    if contentSpec == os.path.basename(f):
                        return VirtualResFile(self, path, res, f)
                return None
            # Accessing /<catType>/<cat>/<name>
            return VirtualResource(self, path, data) 
                 
        elif cat:
            # Accessing /catType/cat: return list of matching names
            resList = _getResListByAttr(catType, cat)
            nameList = [ data["title"] for data in resList ]
            return VirtualResCollection(self, path, nameList)
        
        elif catType: 
            # Accessing /catType/: return all possible values for this catType
            if catType in _browsableCategories:
                resList = []
                for data in _resourceData:
                    if catType == "by_status":
                        if not data["status"] in resList:
                            resList.append(data["status"])
                    elif catType == "by_orga":
                        if not data["orga"] in resList:
                            resList.append(data["orga"])
                    elif catType == "by_tag":
                        for tag in data["tags"]:
                            if not tag in resList:
                                resList.append(tag)
                        
                return VirtualResCollection(self, path, resList)
            # Known category type, but not browsable (e.g. 'by_key')
            raise DAVError(HTTP_FORBIDDEN)
                 
        # Accessing /: return list of categories
        return VirtualResCollection(self, path, _browsableCategories)
