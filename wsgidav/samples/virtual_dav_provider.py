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
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN, HTTP_NOT_FOUND,\
    HTTP_INTERNAL_ERROR
from wsgidav import util

__docformat__ = "reStructuredText en"

_logger = util.getModuleLogger(__name__)

#===============================================================================
# Tool functions
#===============================================================================


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
     "title": "My doc 3", 
     "orga": "marketing", 
     "tags": ["nice"],
     "status": "published",
     "description": "Long text describing it", 
     "resPathList": [os.path.join(FILE_FOLDER, "My URS.doc"),
                     os.path.join(FILE_FOLDER, "My URS.doc"),
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


def _getResByPath(path):
    """Return _VirtualResource object for a path.
    
    path is expected to be 
        categoryType/category/name/artifact
    for example:
        'by_tag/cool/My doc 2/info.html'
    """
    assert not "\\" in path
    
    catType, cat, resName, contentSpec = util.saveSplit(path.strip("/"), "/", 3)

    _logger.info("_getResByPath('%s'): catType=%s, cat=%s, resName=%s" % (path, catType, cat, resName))
    
    if catType and catType not in _alllowedCategories:
        raise DAVError(HTTP_NOT_FOUND, "Unknown category type '%s'" % catType)

    if catType == _realCategory:
        # Accessing /by_key/<key>
        data = _getResByKey(cat)
        if data:
            return VirtualResource(data)
        raise DAVError(HTTP_NOT_FOUND, "Unknown key '%s'" % cat)
        
    elif resName:
        # Accessing /<catType>/<cat>/<name> or /<catType>/<cat>/<name>/<contentSpec>
        res = None
        for data in _getResListByAttr(catType, cat):
            if data["title"] == resName:
                res = data
                break
        if not res:
            raise DAVError(HTTP_NOT_FOUND)
        # Accessing /<catType>/<cat>/<name>
        if contentSpec in _artifactNames:
            # Accessing /<catType>/<cat>/<name>/.info.html, or similar
            return VirtualArtifact(res, contentSpec)
        elif contentSpec:
            # Accessing /<catType>/<cat>/<name>/<file-name>
            for f in res["resPathList"]:
                if contentSpec == os.path.basename(f):
                    return VirtualResFile(res, f)
            raise DAVError(HTTP_NOT_FOUND)
        # Accessing /<catType>/<cat>/<name>
        return VirtualResource(data) 
             
    elif cat:
        # Accessing /catType/cat: return list of matching names
        resList = _getResListByAttr(catType, cat)
        nameList = [ data["title"] for data in resList ]
        return VirtualResCollection(nameList)
    
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
                    
            return VirtualResCollection(resList)
        # Known category type, but not browsable (e.g. 'by_key')
        raise DAVError(HTTP_FORBIDDEN)
             
    # Accessing /: return list of categories
    return VirtualResCollection(_browsableCategories)
    



#===============================================================================
# _VirtualResource classes
#===============================================================================
class _VirtualResource(object):
    """Abstract base class for all resources."""
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
    def getRefPath(self):
        return None


class VirtualResCollection(_VirtualResource):
    """Collection type resource, that contains a list of names."""
    def __init__(self, nameList):
        self.nameList = nameList
    def isCollection(self):
        return True


class VirtualResource(VirtualResCollection):
    """A virtual 'resource', displayed as a collection of artifacts and files."""
    def __init__(self, data):
        self.data = data
        self.nameList = _artifactNames[:] # Use a copy
        for f in data["resPathList"]:
            self.nameList.append(os.path.basename(f))
    def isCollection(self):
        return True
    def getRefPath(self):
        return "/by_key/%s" % self.data["key"] 


class VirtualArtifact(_VirtualResource):
    """A virtual file, containing resource descriptions."""
    def __init__(self, data, name):
        assert name in _artifactNames
        self.data = data
        self.name = name
    def getContent(self):
        fileLinks = [ "<a href='%s'>%s</a>\n" % (os.path.basename(f), f) for f in self.data["resPathList"] ]
        dict = self.data.copy()
        dict["fileLinks"] = ", ".join(fileLinks)
        if self.name == ".Info.html":
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
        elif self.name == ".Info.txt":
            lines = [self.data["title"],
                     "=" * len(self.data["title"]),
                     self.data["description"],
                     "",
                     "Status: %s" % self.data["status"],
                     "Orga:   %8s" % self.data["orga"],
                     "Tags:   '%s'" % "', '".join(self.data["tags"]),
                     "Key:    %s" % self.data["key"],
                     ] 
            html = "\n".join(lines)
        elif self.name == ".Description.txt":
            html = self.data["description"]
        else:
            raise DAVError(HTTP_INTERNAL_ERROR, "Invalid artifact '%s'" % self.name)
        return StringIO(html)
    def getContentType(self):
        if self.name.endswith(".txt"):
            return "text/plain"
        return "text/html"
    def getContentLength(self):
        return len(self.getContent().read())
    def getRefPath(self):
        return "/by_key/%s/%s" % (self.data["key"], self.name) 


class VirtualResFile(_VirtualResource):
    """Represents an existing file, that is a member of a VirtualResource."""
    def __init__(self, data, filePath):
        self.data = data
        self.filePath = filePath
    def getContent(self):
        mime = self.getContentType()
        if mime.startswith("text"):
            return file(self.filePath, "r", BUFFER_SIZE)
        else:
            return file(self.filePath, "rb", BUFFER_SIZE)
    def getContentType(self):
        if not os.path.isfile(self.filePath):
            return "text/html"
        (mimetype, _mimeencoding) = mimetypes.guess_type(self.filePath) 
        if not mimetype:
            mimetype = "application/octet-stream" 
        return mimetype
    def getContentLength(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_SIZE]      
    def getCreationDate(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_CTIME]      
    def getModifiedDate(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_MTIME]      
    def getRefPath(self):
        return "/by_key/%s/%s" % (self.data["key"], os.path.basename(self.filePath)) 


        
         
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
        

    def getRefUrl(self, path):
        """Return the quoted, absolute, unique URL of a resource, relative to appRoot.
        
        See also comments in DEVELOPERS.txt glossary.
        """
        res = _getResByPath(path)
        if res is None or res.getRefPath() is None:
            return super(VirtualResourceProvider, self).getRefUrl(path)
        _logger.info("path=%s, refpath=%s" % (path, res.getRefPath()))
        return urllib.quote(self.sharePath + res.getRefPath())

    
    def getMemberNames(self, path):
        res = _getResByPath(path)
        return res.nameList

    
    def getResourceInst(self, path, typeList=None):
        """Return a DAVResource object for path.

        See DAVProvider.getResourceInst()
        """
        res = _getResByPath(path)
        if res is None:
            # Return non-existing davresource
            return DAVResource(self, path, None, typeList)

        isCollection = res.isCollection()
        name = util.getUriName(self.getPreferredPath(path))  # TODO: inefficient: calls getPreferred -> isCollection -> getResInstance

        dict = {"contentLength": None,
                "contentType": None,
                "name": name,
                "displayName": name,
                "displayType": res.__class__.__name__, #displayType,
#                "etag": util.getETag(path),
                "modified": res.getModifiedDate(),
                "created": res.getCreationDate(),
                "supportRanges": False,
                "isCollection": isCollection, 
                }
        # Some resource-only infos: 
        if not isCollection:
#            dict["etag"] = util.getETag(file path), # TODO: should be using the file path here
            dict["contentType"] = res.getContentType()
            dict["contentLength"] = res.getContentLength()
            dict["supportRanges"] = True

        davres = DAVResource(self, path, dict, typeList)
        return davres

    
    def exists(self, path):
        res = _getResByPath(path)
        return res is not None
    
    
    def isCollection(self, path):
        res = _getResByPath(path)
        return res and res.isCollection()
    
    
    def isResource(self, path):
        res = _getResByPath(path)
        return res and not res.isCollection()
    
    
    def createCollection(self, path):
        raise DAVError(HTTP_FORBIDDEN)               
    

    def deleteCollection(self, path):
        raise DAVError(HTTP_FORBIDDEN)               

    
    def openResourceForRead(self, path, davres=None):
        res = _getResByPath(path)
        return res.getContent()
