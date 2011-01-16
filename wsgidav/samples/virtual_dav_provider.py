# -*- coding: iso-8859-1 -*-
# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Sample implementation of a DAV provider that provides a browsable, 
multi-categorized resource tree.

Note that this is simply an example with no concrete real world benefit.
But it demonstrates some techniques to customize WsgiDAV. 

Compared to a published file system, we have these main differences:

#. A resource like ``My doc 1`` has several attributes like ``key``,  
   ``orga``, ``tags``, ``status``, ``description``. 
   Also there may be a list of attached files.
#. These attributes are used to dynamically create a virtual hierarchy.
   For example, if ``status`` is ``draft``, a collection 
   ``<share>/by_status/draft/`` is created and the resource is mapped to 
   ``<share>/by_status/draft/My doc 1``.
#. The resource ``My doc 1`` is rendered as a collection, that contains 
   some virtual descriptive files and the attached files.
#. The same resource may be referenced using different paths
   For example ``<share>/by_tag/cool/My doc 1``, 
   ``<share>/by_tag/hot/My doc 1``, and ``<share>/by_key/1`` map to the same
   resource. 
   Only the latter is considered the *real-path*, all others are 
   *virtual-paths*.
#. The attributes are exposed as live properties, like "{virtres:}key",
   "{virtres:}tags", and "{virtres:}description".
   Some of them are even writable. Note that modifying an attribute may also 
   change the dynamically created tree structure.
   For example changing "{virtres:}status" from 'draft' to 'published' will 
   make the resource appear as ``<share>/by_status/published/My doc 1``.
#. This provider implements native delete/move/copy methods, to change the
   semantics of these operations for the virtual '/by_tag/' collection.
   For example issuing a DELETE on ``<share>/by_tag/cool/My doc 1`` will
   simply remove the 'cool' tag from that resource.
#. Virtual collections and artifacts cannot be locked.
   However a resource can be locked. 
   For example locking ``<share>/by_tag/cool/My doc 1`` will also lock 
   ``<share>/by_key/1``.
#. Some paths may be hidden, i.e. by_key is not browsable (but can be referenced)
   TODO: is this WebDAV compliant? 
 
The *database* is a simple hard coded variable ``_resourceData``, that contains 
a list of resource description dictionaries.

A resource is served as an collection, which is generated on-the-fly and 
contains some virtual files (*artifacts*). 

In general, a URL is interpreted like this::

  <share>/<category-type>/<category-key>/<resource-name>/<artifact-name>


An example layout::
            
    <share>/
        by_tag/
            cool/
                My doc 1/
                    .Info.html
                    .Info.txt
                    .Description.txt
                    MySpec.pdf
                    MySpec.doc
                My doc 2/
            hot/
                My doc 1/
                My doc 2/
            nice/
                My doc 2/
                My doc 3
        by_orga/
            development/
                My doc 3/
            marketing/
                My doc 1/
                My doc 2/
        by_status/
            draft/
                My doc 2
            published/
                My doc 1
                My doc 3
        by_key/
            1/
            2/
            3/
            
When accessed using WebDAV, the following URLs both return the same resource 
'My doc 1'::

    <share>/by_tag/cool/My doc 1 
    <share>/by_tag/hot/My doc 1
    <share>/by_key/1
"""
import urllib
import stat
import os
import mimetypes
from wsgidav.util import joinUri
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport
from wsgidav.dav_provider import DAVProvider, DAVNonCollection, DAVCollection
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN, HTTP_INTERNAL_ERROR,\
    PRECONDITION_CODE_ProtectedProperty
from wsgidav import util

__docformat__ = "reStructuredText en"

_logger = util.getModuleLogger(__name__)

BUFFER_SIZE = 8192

#===============================================================================
# Fake hierarchical repository
#===============================================================================
"""
This is a dummy 'database', that serves as an example source for the
VirtualResourceProvider.

All files listed in resPathList are expected to exist in FILE_FOLDER.
"""
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
    assert attrName in RootCollection._visibleMemberNames
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
# 
#===============================================================================
class RootCollection(DAVCollection):
    """Resolve top-level requests '/'."""
    _visibleMemberNames = ("by_orga", "by_tag", "by_status")
    _validMemberNames = _visibleMemberNames + ("by_key", )
    
    def __init__(self, environ):
        DAVCollection.__init__(self, "/", environ)
        
    def getMemberNames(self):
        return self._visibleMemberNames
    
    def getMember(self, name):
        # Handle visible categories and also /by_key/...
        if name in self._validMemberNames:
            return CategoryTypeCollection(joinUri(self.path, name), self.environ)
        return None


class CategoryTypeCollection(DAVCollection):
    """Resolve '/catType' URLs, for example '/by_tag'."""
    def __init__(self, path, environ):
        DAVCollection.__init__(self, path, environ)
    
    def getDisplayInfo(self):
        return {"type": "Category type"}
    
    def getMemberNames(self):
        names = []
        for data in _resourceData:
            if self.name == "by_status":
                if not data["status"] in names:
                    names.append(data["status"])
            elif self.name == "by_orga":
                if not data["orga"] in names:
                    names.append(data["orga"])
            elif self.name == "by_tag":
                for tag in data["tags"]:
                    if not tag in names:
                        names.append(tag)
            
        names.sort()
        return names
    
    def getMember(self, name):
        if self.name == "by_key":
            data = _getResByKey(name)
            if data:
                return VirtualResource(joinUri(self.path, name), self.environ, data)
            else:
                return None
        return CategoryCollection(joinUri(self.path, name), self.environ, self.name)


class CategoryCollection(DAVCollection):
    """Resolve '/catType/cat' URLs, for example '/by_tag/cool'."""
    def __init__(self, path, environ, catType):
        DAVCollection.__init__(self, path, environ)
        self.catType = catType
    
    def getDisplayInfo(self):
        return {"type": "Category"}
    
    def getMemberNames(self):
        names = [ data["title"] for data in _getResListByAttr(self.catType, self.name) ]
        names.sort()
        return names
    
    def getMember(self, name):
        for data in _getResListByAttr(self.catType, self.name):
            if data["title"] == name:
                return VirtualResource(joinUri(self.path, name), self.environ, data)
        return None


#===============================================================================
# VirtualResource
#===============================================================================
class VirtualResource(DAVCollection):
    """A virtual 'resource', displayed as a collection of artifacts and files."""
    _artifactNames = (".Info.txt", 
                      ".Info.html", 
                      ".Description.txt",
#                     ".Admin.html",
                      )
    _supportedProps = ["{virtres:}key",
                       "{virtres:}title",
                       "{virtres:}status",
                       "{virtres:}orga",
                       "{virtres:}tags",
                       "{virtres:}description",
                       ]

    def __init__(self, path, environ, data):
        DAVCollection.__init__(self, path, environ)
        self.data = data

    def getDisplayInfo(self):
        return {"type": "Virtual Resource"}
    
    def getMemberNames(self):
        names = list(self._artifactNames)
        for f in self.data["resPathList"]:
            name = os.path.basename(f)
            names.append(name)
        return names

    def getMember(self, name):
        if name in self._artifactNames:
            return VirtualArtifact(joinUri(self.path, name), self.environ, self.data)
        for filePath in self.data["resPathList"]:
            fname = os.path.basename(filePath)
            if fname == name:
                return VirtualResFile(joinUri(self.path, name), self.environ, self.data, filePath)
        return None

    def handleDelete(self):
        """Change semantic of DELETE to remove resource tags."""
        # DELETE is only supported for the '/by_tag/' collection 
        if not "/by_tag/" in self.path:
            raise DAVError(HTTP_FORBIDDEN)
        # path must be '/by_tag/<tag>/<resname>' 
        catType, tag, _rest = util.saveSplit(self.path.strip("/"), "/", 2)
        assert catType == "by_tag"
        assert tag in self.data["tags"]
        self.data["tags"].remove(tag)
        return True # OK
        
    def handleCopy(self, destPath, depthInfinity):
        """Change semantic of COPY to add resource tags."""
        # destPath must be '/by_tag/<tag>/<resname>' 
        if not "/by_tag/" in destPath:
            raise DAVError(HTTP_FORBIDDEN)
        catType, tag, _rest = util.saveSplit(destPath.strip("/"), "/", 2)
        assert catType == "by_tag"
        if not tag in self.data["tags"]:
            self.data["tags"].append(tag)
        return True # OK

    def handleMove(self, destPath):
        """Change semantic of MOVE to change resource tags."""
        # path and destPath must be '/by_tag/<tag>/<resname>' 
        if not "/by_tag/" in self.path:
            raise DAVError(HTTP_FORBIDDEN)
        if not "/by_tag/" in destPath:
            raise DAVError(HTTP_FORBIDDEN)
        catType, tag, _rest = util.saveSplit(self.path.strip("/"), "/", 2)
        assert catType == "by_tag"
        assert tag in self.data["tags"]
        self.data["tags"].remove(tag)
        catType, tag, _rest = util.saveSplit(destPath.strip("/"), "/", 2)
        assert catType == "by_tag"
        if not tag in self.data["tags"]:
            self.data["tags"].append(tag)
        return True # OK

    def getRefUrl(self):
        refPath = "/by_key/%s" % self.data["key"] 
        return urllib.quote(self.provider.sharePath + refPath)
    
    def getPropertyNames(self, isAllProp):
        """Return list of supported property names in Clark Notation.
        
        See DAVResource.getPropertyNames() 
        """
        # Let base class implementation add supported live and dead properties
        propNameList = super(VirtualResource, self).getPropertyNames(isAllProp)
        # Add custom live properties (report on 'allprop' and 'propnames')
        propNameList.extend(VirtualResource._supportedProps)
        return propNameList

    def getPropertyValue(self, propname):
        """Return the value of a property.
        
        See getPropertyValue()
        """
        # Supported custom live properties
        if propname == "{virtres:}key":
            return self.data["key"]
        elif propname == "{virtres:}title":
            return self.data["title"]
        elif propname == "{virtres:}status":
            return self.data["status"]
        elif propname == "{virtres:}orga":
            return self.data["orga"]
        elif propname == "{virtres:}tags":
            # 'tags' is a string list
            return ",".join(self.data["tags"])
        elif propname == "{virtres:}description":
            return self.data["description"]
        # Let base class implementation report live and dead properties
        return super(VirtualResource, self).getPropertyValue(propname)
    
    def setPropertyValue(self, propname, value, dryRun=False):
        """Set or remove property value.
        
        See DAVResource.setPropertyValue()
        """
        if value is None:
            # We can never remove properties
            raise DAVError(HTTP_FORBIDDEN)
        if propname == "{virtres:}tags":
            # value is of type etree.Element
            self.data["tags"] = value.text.split(",")
        elif propname == "{virtres:}description":
            # value is of type etree.Element
            self.data["description"] = value.text
        elif propname in VirtualResource._supportedProps:
            # Supported property, but read-only    
            raise DAVError(HTTP_FORBIDDEN,  
                           errcondition=PRECONDITION_CODE_ProtectedProperty)
        else:
            # Unsupported property    
            raise DAVError(HTTP_FORBIDDEN)
        # Write OK
        return  
              


#===============================================================================
# _VirtualNonCollection classes
#===============================================================================
class _VirtualNonCollection(DAVNonCollection):
    """Abstract base class for all non-collection resources."""
    def __init__(self, path, environ):
        DAVNonCollection.__init__(self, path, environ)
    def getContentLength(self):
        return None
    def getContentType(self):
        return None
    def getCreationDate(self):
        return None
    def getDisplayName(self):
        return self.name
    def getDisplayInfo(self):
        raise NotImplementedError()
    def getEtag(self):
        return None
    def getLastModified(self):
        return None
    def supportRanges(self):
        return False
#    def handleDelete(self):
#        raise DAVError(HTTP_FORBIDDEN)
#    def handleMove(self, destPath):
#        raise DAVError(HTTP_FORBIDDEN)
#    def handleCopy(self, destPath, depthInfinity):
#        raise DAVError(HTTP_FORBIDDEN)


#===============================================================================
# VirtualArtifact
#===============================================================================
class VirtualArtifact(_VirtualNonCollection):
    """A virtual file, containing resource descriptions."""
    def __init__(self, path, environ, data):
#        assert name in _artifactNames
        _VirtualNonCollection.__init__(self, path, environ)
        self.data = data

    def getContentLength(self):
        return len(self.getContent().read())
    def getContentType(self):
        if self.name.endswith(".txt"):
            return "text/plain"
        return "text/html"
    def getDisplayInfo(self):
        return {"type": "Virtual info file"}
    def preventLocking(self):
        return True

    def getRefUrl(self):
        refPath = "/by_key/%s/%s" % (self.data["key"], self.name)
        return urllib.quote(self.provider.sharePath + refPath)
 
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


#===============================================================================
# VirtualResFile
#===============================================================================
class VirtualResFile(_VirtualNonCollection):
    """Represents an existing file, that is a member of a VirtualResource."""
    def __init__(self, path, environ, data, filePath):
        if not os.path.exists(filePath):
            util.warn("VirtualResFile(%r) does not exist." % filePath)
        _VirtualNonCollection.__init__(self, path, environ)
        self.data = data
        self.filePath = filePath

    def getContentLength(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_SIZE]      
    def getContentType(self):
        if not os.path.isfile(self.filePath):
            return "text/html"
        (mimetype, _mimeencoding) = mimetypes.guess_type(self.filePath) 
        if not mimetype:
            mimetype = "application/octet-stream" 
        return mimetype
    def getCreationDate(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_CTIME]      
    def getDisplayInfo(self):
        return {"type": "Content file"}
    def getLastModified(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_MTIME]      

    def getRefUrl(self):
        refPath = "/by_key/%s/%s" % (self.data["key"], os.path.basename(self.filePath))
        return urllib.quote(self.provider.sharePath + refPath)

    def getContent(self):
        mime = self.getContentType()
        if mime.startswith("text"):
            return file(self.filePath, "r", BUFFER_SIZE)
        return file(self.filePath, "rb", BUFFER_SIZE)

         
#===============================================================================
# VirtualResourceProvider
#===============================================================================
class VirtualResourceProvider(DAVProvider):
    """
    DAV provider that serves a VirtualResource derived structure.
    """
    def __init__(self):
        super(VirtualResourceProvider, self).__init__()
        self.resourceData = _resourceData

    def getResourceInst(self, path, environ):
        """Return _VirtualResource object for path.
        
        path is expected to be 
            categoryType/category/name/artifact
        for example:
            'by_tag/cool/My doc 2/info.html'

        See DAVProvider.getResourceInst()
        """
        _logger.info("getResourceInst('%s')" % path)
        self._count_getResourceInst += 1
        root = RootCollection(environ)
        return root.resolve("", path)

#class VirtualResourceProvider(DAVProvider):
#    """
#    DAV provider that serves a VirtualResource derived structure.
#    """
#    def __init__(self):
#        super(VirtualResourceProvider, self).__init__()
#        self.resourceData = _resourceData
##        self.rootCollection = VirtualCollection(self, "/", environ)
#        
#
#    def getResourceInst(self, path, environ):
#        """Return _VirtualResource object for path.
#        
#        path is expected to be 
#            categoryType/category/name/artifact
#        for example:
#            'by_tag/cool/My doc 2/info.html'
#
#        See DAVProvider.getResourceInst()
#        """
#        self._count_getResourceInst += 1
#        
#        catType, cat, resName, artifactName = util.saveSplit(path.strip("/"), "/", 3)
#    
#        _logger.info("getResourceInst('%s'): catType=%s, cat=%s, resName=%s" % (path, catType, cat, resName))
#        
#        if catType and catType not in _alllowedCategories:
#            return None
#    
#        if catType == _realCategory:
#            # Accessing /by_key/<key>
#            data = _getResByKey(cat)
#            if data:
#                return VirtualResource(self, path, environ, data)
#            return None
#            
#        elif resName:
#            # Accessing /<catType>/<cat>/<name> or /<catType>/<cat>/<resName>/<artifactName>
#            res = None
#            for data in _getResListByAttr(catType, cat):
#                if data["title"] == resName:
#                    res = data
#                    break
#            if not res:
#                return None
#            # Accessing /<catType>/<cat>/<name>
#            if artifactName in _artifactNames:
#                # Accessing /<catType>/<cat>/<name>/.info.html, or similar
#                return VirtualArtifact(self, util.joinUri(path, artifactName), environ, 
#                                       res, artifactName)
#            elif artifactName:
#                # Accessing /<catType>/<cat>/<name>/<file-name>
#                for f in res["resPathList"]:
#                    if artifactName == os.path.basename(f):
#                        return VirtualResFile(self, path, environ, res, f)
#                return None
#            # Accessing /<catType>/<cat>/<name>
#            return VirtualResource(self, path, environ, data) 
#                 
#        elif cat:
#            # Accessing /catType/cat: return list of matching names
#            resList = _getResListByAttr(catType, cat)
#            nameList = [ data["title"] for data in resList ]
#            return VirtualCollection(self, path, environ, nameList)
#        
#        elif catType: 
#            # Accessing /catType/: return all possible values for this catType
#            if catType in _browsableCategories:
#                resList = []
#                for data in _resourceData:
#                    if catType == "by_status":
#                        if not data["status"] in resList:
#                            resList.append(data["status"])
#                    elif catType == "by_orga":
#                        if not data["orga"] in resList:
#                            resList.append(data["orga"])
#                    elif catType == "by_tag":
#                        for tag in data["tags"]:
#                            if not tag in resList:
#                                resList.append(tag)
#                        
#                return VirtualCollection(self, path, environ, resList)
#            # Known category type, but not browsable (e.g. 'by_key')
#            raise DAVError(HTTP_FORBIDDEN)
#                 
#        # Accessing /: return list of categories
#        return VirtualCollection(self, path, environ, _browsableCategories)
