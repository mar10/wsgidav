# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implements a property manager based on MongoDB.

Usage: add this lines to wsgidav.conf::

    from wsgidav.addons.mongo_property_manager import MongoPropertyManager
    prop_man_opts = {} 
    propsmanager = MongoPropertyManager(prop_man_opts)

Valid options are (sample shows defaults)::

    opts = {"host": "localhost",       # MongoDB server 
            "port": 27017,             # MongoDB port
            "dbName": "wsgidav-props", # Name of DB to store the properties
            # This options are used with `mongod --auth`
            # The user must be created with db.addUser()
            "user": None,              # Authenticate with this user
            "pwd": None,               # ... and password
            }

"""
from wsgidav import util
import pymongo
from urllib import quote

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

# We use these keys internally, so they must be protected
HIDDEN_KEYS = ("_id", "_url", "_title")

### MongiDB doesn't accept '.' in key names, so we have to escape it.
# Use a key that is unlikely to occur in proprty names
DOT_ESCAPE = "^"    

def encodeMongoKey(s):
    """Return an encoded version of `s` that may be used as MongoDB key."""
    assert not DOT_ESCAPE in s
    return s.replace(".", DOT_ESCAPE)

def decodeMongoKey(key):
    """Decode a string that was encoded by encodeMongoKey()."""
    return key.replace(DOT_ESCAPE, ".")


#===============================================================================
# MongoPropertyManager
#===============================================================================
class MongoPropertyManager(object):
    """Implements a property manager based on MongoDB."""
    def __init__(self, options):
        self.options = options
        self._connect()

    def __del__(self):
        self._disconnect()
            
    def _connect(self):
        opts = self.options
        self.conn = pymongo.Connection(opts.get("host"), opts.get("port"))
        _logger.debug(self.conn.server_info())
        self.db = self.conn[opts.get("dbName", "wsgidav-props")]
        # If credentials are passed, logon to the property storage db
        if opts.get("user"):
            if not self.db.authenticate(opts.get("user"), opts.get("pwd")):
                raise RuntimeError("Failed to logon to db %s as user %s" % 
                                   (self.db.name, opts.get("user")))
            util.log("Logged on to mongo db '%s' as user '%s'" % (self.db.name, opts.get("user")))
            
        self.collection = self.db["properties"]
        util.log("MongoPropertyManager connected %r" % self.collection)
        _res = self.collection.ensure_index("_url")

    def _disconnect(self):
        if self.conn:
            self.conn.disconnect()
        self.conn = None

    def __repr__(self):
        return "MongoPropertyManager(%s)" % self.db

    def _sync(self):
        pass
    
    def _check(self, msg=""):
        pass

    def _dump(self, msg="", out=None):
        pass

    def getProperties(self, normurl):
        _logger.debug("getProperties(%s)" % normurl)
        doc = self.collection.find_one({"_url": normurl})
        propNames = []
        if doc:
            for name in doc.keys():
                if not name in HIDDEN_KEYS:
                    propNames.append(decodeMongoKey(name))
        return propNames

    def getProperty(self, normurl, propname):
        _logger.debug("getProperty(%s, %s)" % (normurl, propname))
        doc = self.collection.find_one({"_url": normurl})
        if not doc:
            return None
        prop = doc.get(encodeMongoKey(propname))
        return prop

    def writeProperty(self, normurl, propname, propertyvalue, dryRun=False):
        assert normurl and normurl.startswith("/")
        assert propname
        assert propertyvalue is not None
        assert propname not in HIDDEN_KEYS, "MongoDB key is protected: '%s'" % propname
        
        _logger.debug("writeProperty(%s, %s, dryRun=%s):\n\t%s" % (normurl, propname, dryRun, propertyvalue))
        if dryRun:
            return  # TODO: can we check anything here?

        doc = self.collection.find_one({"_url": normurl})
        if not doc:
            doc = {"_url": normurl,
                   "_title": quote(normurl),
                   }
        doc[encodeMongoKey(propname)] = propertyvalue
        self.collection.save(doc)

    def removeProperty(self, normurl, propname, dryRun=False):
        """
        """
        _logger.debug("removeProperty(%s, %s, dryRun=%s)" % (normurl, propname, dryRun))
        if dryRun:
            # TODO: can we check anything here?
            return  
        doc = self.collection.find_one({"_url": normurl})
        # Specifying the removal of a property that does not exist is NOT an error.
        if not doc or doc.get(encodeMongoKey(propname)) is None:
            return
        del doc[encodeMongoKey(propname)]
        self.collection.save(doc)

    def removeProperties(self, normurl):
        _logger.debug("removeProperties(%s)" % normurl)
        doc = self.collection.find_one({"_url": normurl})
        if doc:
            self.collection.remove(doc)
        return

    def copyProperties(self, srcUrl, destUrl):
        doc = self.collection.find_one({"_url": srcUrl})
        if not doc:
            _logger.debug("copyProperties(%s, %s): src has no properties" % (srcUrl, destUrl))
            return
        _logger.debug("copyProperties(%s, %s)" % (srcUrl, destUrl))
        doc2 = doc.copy()
        self.collection.insert(doc2)

    def moveProperties(self, srcUrl, destUrl, withChildren):
        _logger.debug("moveProperties(%s, %s, %s)" % (srcUrl, destUrl, withChildren))
        if withChildren:
            # Match URLs that are equal to <srcUrl> or begin with '<srcUrl>/'
            matchBegin = "^" + srcUrl.rstrip("/") + "/"
            query = {"$or": [{"_url": srcUrl},
                             {"_url": {"$regex": matchBegin}},
                             ]}
            docList = self.collection.find(query)
            for doc in docList:
                newDest = doc["_url"].replace(srcUrl, destUrl)
                _logger.debug("move property %s -> %s" % (doc["_url"], newDest))
                doc["_url"] = newDest 
                self.collection.save(doc)
        else:
            # Move srcUrl only      
            # TODO: use findAndModify()?
            doc = self.collection.find_one({"_url": srcUrl})
            if doc:
                _logger.debug("move property %s -> %s" % (doc["_url"], destUrl))
                doc["_url"] = destUrl 
                self.collection.save(doc)
        return
