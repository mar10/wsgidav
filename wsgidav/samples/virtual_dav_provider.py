# -*- coding: iso-8859-1 -*-
# (c) 2009 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
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
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport
from wsgidav.dav_provider import DAVProvider, DAVResource
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN, HTTP_INTERNAL_ERROR,\
    PRECONDITION_CODE_ProtectedProperty
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
    def __init__(self, provider, path, isCollection, environ):
        super(_VirtualResource, self).__init__(provider, path, isCollection, environ)

    def getContentLength(self):
        return None
    def getContentType(self):
        return None
    def getCreationDate(self):
        return None
    def getDisplayName(self):
        return self.name
    def displayType(self):
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


class VirtualResCollection(_VirtualResource):
    """Collection resource, that contains a list of names."""
    def __init__(self, provider, path, environ, nameList):
        _VirtualResource.__init__(self, provider, path, True, environ)
        self._nameList = nameList
    def displayType(self):
        return "Category"
    def getMemberNames(self):
        return self._nameList
    def preventLocking(self):
        return True


class VirtualResource(_VirtualResource):
    """A virtual 'resource', displayed as a collection of artifacts and files."""
    _supportedProps = ["{virtres:}key",
                       "{virtres:}title",
                       "{virtres:}status",
                       "{virtres:}orga",
                       "{virtres:}tags",
                       "{virtres:}description",
                       ]
    def __init__(self, provider, path, environ, data):
        _VirtualResource.__init__(self, provider, path, True, environ)
        self._data = data
        self._nameList = _artifactNames[:] # Use a copy
        for f in data["resPathList"]:
            self._nameList.append(os.path.basename(f))

    def displayType(self):
        return "Resource folder"
    
    def handleDelete(self):
        """Change semantic of DELETE to remove resource tags."""
        # DELETE is only supported for the '/by_tag/' collection 
        if not "/by_tag/" in self.path:
            raise DAVError(HTTP_FORBIDDEN)
        # path must be '/by_tag/<tag>/<resname>' 
        catType, tag, _rest = util.saveSplit(self.path.strip("/"), "/", 2)
        assert catType == "by_tag"
        assert tag in self._data["tags"]
        self._data["tags"].remove(tag)
        return True # OK
        
    def handleCopy(self, destPath, depthInfinity):
        """Change semantic of COPY to add resource tags."""
        # destPath must be '/by_tag/<tag>/<resname>' 
        if not "/by_tag/" in destPath:
            raise DAVError(HTTP_FORBIDDEN)
        catType, tag, _rest = util.saveSplit(destPath.strip("/"), "/", 2)
        assert catType == "by_tag"
        if not tag in self._data["tags"]:
            self._data["tags"].append(tag)
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
        assert tag in self._data["tags"]
        self._data["tags"].remove(tag)
        catType, tag, _rest = util.saveSplit(destPath.strip("/"), "/", 2)
        assert catType == "by_tag"
        if not tag in self._data["tags"]:
            self._data["tags"].append(tag)
        return True # OK

    def getRefUrl(self):
        refPath = "/by_key/%s" % self._data["key"] 
        return urllib.quote(self.provider.sharePath + refPath)
    
    def getMemberNames(self):
        return self._nameList

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
            return self._data["key"]
        elif propname == "{virtres:}title":
            return self._data["title"]
        elif propname == "{virtres:}status":
            return self._data["status"]
        elif propname == "{virtres:}orga":
            return self._data["orga"]
        elif propname == "{virtres:}tags":
            # 'tags' is a string list
            return ",".join(self._data["tags"])
        elif propname == "{virtres:}description":
            return self._data["description"]
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
            self._data["tags"] = value.text.split(",")
        elif propname == "{virtres:}description":
            # value is of type etree.Element
            self._data["description"] = value.text
        elif propname in VirtualResource._supportedProps:
            # Supported property, but read-only    
            raise DAVError(HTTP_FORBIDDEN,  
                           errcondition=PRECONDITION_CODE_ProtectedProperty)
        else:
            # Unsupported property    
            raise DAVError(HTTP_FORBIDDEN)
        # Write OK
        return  
              


class VirtualArtifact(_VirtualResource):
    """A virtual file, containing resource descriptions."""
    def __init__(self, provider, path, environ, data, name):
        assert name in _artifactNames
        _VirtualResource.__init__(self, provider, path, False, environ)
        assert self.name == name
        self._data = data

    def getContentLength(self):
        return len(self.getContent().read())
    def getContentType(self):
        if self.name.endswith(".txt"):
            return "text/plain"
        return "text/html"
    def displayType(self):
        return "Virtual info file"
    def preventLocking(self):
        return True

    def getRefUrl(self):
        refPath = "/by_key/%s/%s" % (self._data["key"], self.name)
        return urllib.quote(self.provider.sharePath + refPath)
 
    def getContent(self):
        fileLinks = [ "<a href='%s'>%s</a>\n" % (os.path.basename(f), f) for f in self._data["resPathList"] ]
        dict = self._data.copy()
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
        elif self.name == ".Description.txt":
            html = self._data["description"]
        else:
            raise DAVError(HTTP_INTERNAL_ERROR, "Invalid artifact '%s'" % self._name)
        return StringIO(html)


class VirtualResFile(_VirtualResource):
    """Represents an existing file, that is a member of a VirtualResource."""
    def __init__(self, provider, path, environ, data, filePath):
#        assert os.path.exists(filePath)
        _VirtualResource.__init__(self, provider, path, False, environ)
        self._data = data
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
    def displayType(self):
        return "Content file"
    def getLastModified(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_MTIME]      

    def getRefUrl(self):
        refPath = "/by_key/%s/%s" % (self._data["key"], os.path.basename(self.filePath))
        return urllib.quote(self.provider.sharePath + refPath)

    def getContent(self):
        mime = self.getContentType()
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
        

    def getResourceInst(self, path, environ):
        """Return _VirtualResource object for path.
        
        path is expected to be 
            categoryType/category/name/artifact
        for example:
            'by_tag/cool/My doc 2/info.html'

        See DAVProvider.getResourceInst()
        """
        self._count_getResourceInst += 1
        
        catType, cat, resName, artifactName = util.saveSplit(path.strip("/"), "/", 3)
    
        _logger.info("getResourceInst('%s'): catType=%s, cat=%s, resName=%s" % (path, catType, cat, resName))
        
        if catType and catType not in _alllowedCategories:
            return None
    
        if catType == _realCategory:
            # Accessing /by_key/<key>
            data = _getResByKey(cat)
            if data:
                return VirtualResource(self, path, environ, data)
            return None
            
        elif resName:
            # Accessing /<catType>/<cat>/<name> or /<catType>/<cat>/<resName>/<artifactName>
            res = None
            for data in _getResListByAttr(catType, cat):
                if data["title"] == resName:
                    res = data
                    break
            if not res:
                return None
            # Accessing /<catType>/<cat>/<name>
            if artifactName in _artifactNames:
                # Accessing /<catType>/<cat>/<name>/.info.html, or similar
                return VirtualArtifact(self, path, environ, res, artifactName)
            elif artifactName:
                # Accessing /<catType>/<cat>/<name>/<file-name>
                for f in res["resPathList"]:
                    if artifactName == os.path.basename(f):
                        return VirtualResFile(self, path, environ, res, f)
                return None
            # Accessing /<catType>/<cat>/<name>
            return VirtualResource(self, path, environ, data) 
                 
        elif cat:
            # Accessing /catType/cat: return list of matching names
            resList = _getResListByAttr(catType, cat)
            nameList = [ data["title"] for data in resList ]
            return VirtualResCollection(self, path, environ, nameList)
        
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
                        
                return VirtualResCollection(self, path, environ, resList)
            # Known category type, but not browsable (e.g. 'by_key')
            raise DAVError(HTTP_FORBIDDEN)
                 
        # Accessing /: return list of categories
        return VirtualResCollection(self, path, environ, _browsableCategories)
