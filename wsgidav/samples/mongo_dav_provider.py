# (c) 2009-2010 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a WebDAV provider that provides a very basic, read-only
resource layer emulation of a MongoDB database.

Usage: add the following entries to wsgidav.conf::

    from wsgidav.samples.mongo_dav_provider import MongoResourceProvider
    mongo_dav_opts = {}
    addShare("mongo", MongoResourceProvider(mongo_dav_opts))

Valid options are (sample shows defaults)::

    opts = {"host": "localhost",       # MongoDB server 
            "port": 27017,             # MongoDB port
            # This options are used with `mongod --auth`
            # The user must be created in the admin db with 
            # > use admin
            # > db.addUser(username, password)
            "user": None,              # Authenticate with this user
            "pwd": None,               # ... and password
            }

"""
from wsgidav.dav_provider import DAVProvider, DAVCollection, DAVResource
from wsgidav import util
import pymongo
from wsgidav.util import joinUri
from pprint import pformat
from bson.objectid import ObjectId
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)


#===============================================================================
# 
#===============================================================================
class ConnectionCollection(DAVCollection):
    """Root collection, lists all mongo databases."""
    def __init__(self, path, environ):
        DAVCollection.__init__(self, path, environ)
        self.conn = self.provider.conn
    def getMemberList(self):
        dbNames = self.conn.database_names()
        res = [ DbCollection(joinUri(self.path, name.encode("utf8")), self.environ) for name in dbNames ]
        return res
    

class DbCollection(DAVCollection):
    """Mongo database, contains mongo collections."""
    def __init__(self, path, environ):
        DAVCollection.__init__(self, path, environ)
        self.conn = self.provider.conn
        self.db = self.conn[self.name]
    def getDisplayType(self):
        return "Mongo database"
    def getMemberList(self):
        res = []
        for name in self.db.collection_names():
            coll = self.db[name]        
            res.append(CollCollection(joinUri(self.path, name).encode("utf8"), 
                                      self.environ, coll))
        return res
    

class CollCollection(DAVCollection):
    """Mongo collections, contains mongo documents."""
    def __init__(self, path, environ, coll):
        DAVCollection.__init__(self, path, environ)
        self.conn = self.provider.conn
        self.coll = coll
    def getDisplayType(self):
        return "Mongo collection"
    def _getMember(self, name):
        doc = self.coll.find_one(ObjectId(name))
        res = DocResource(joinUri(self.path, name), self.environ, doc)
        return res
    def _getMemberList(self):
        res = []
        for doc in self.coll.find():
            res.append(DocResource(joinUri(self.path, str(doc["_id"])), self.environ, doc))
        return res
    

class DocResource(DAVResource):
    """Mongo document, returned as virtual text resource."""
    def __init__(self, path, environ, doc):
        DAVResource.__init__(self, path, False, environ)
        self.doc = doc
    def getContent(self):
        html = "<pre>" + pformat(self.doc) + "</pre>"
        return StringIO(html.encode("utf8"))
    def getContentLength(self):
        return len(self.getContent().read())
    def getContentType(self):
        return "text/html"
    def supportRanges(self):
        return False
    def getDisplayName(self):
        doc = self.doc
        if doc.get("_title"):
            return doc["_title"].encode("utf8")
        elif doc.get("title"):
            return doc["title"].encode("utf8")
        elif doc.get("_id"):
            return str(doc["_id"])
        return str(doc["key"])
    def getDisplayType(self):
        return "Mongo document"


#===============================================================================
# MongoResourceProvider
#===============================================================================
class MongoResourceProvider(DAVProvider):
    """DAV provider that serves a MongoDB structure."""
    def __init__(self, options):
        super(MongoResourceProvider, self).__init__()
        self.options = options
        self.conn = pymongo.Connection(options.get("host"), options.get("port"))
        if options.get("user"):
            # If credentials are passed, acquire root access
            db = self.conn["admin"]
            res = db.authenticate(options.get("user"), options.get("pwd"))
            if not res:
                raise RuntimeError("Failed to logon to db %s as user %s" % 
                                   (db.name, options.get("user")))
            util.log("Logged on to mongo db '%s' as user '%s'" % (db.name, options.get("user")))
        util.log("MongoResourceProvider connected to %s" % self.conn)

    def getResourceInst(self, path, environ):
        """Return DAVResource object for path.

        See DAVProvider.getResourceInst()
        """
        _logger.info("getResourceInst('%s')" % path)
        self._count_getResourceInst += 1
        root = ConnectionCollection("/", environ)
        return root.resolve("/", path)


#===============================================================================
# Main 
#===============================================================================
def test():
    pass

if __name__ == "__main__":
    test()
