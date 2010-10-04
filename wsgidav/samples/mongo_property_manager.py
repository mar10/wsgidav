# (c) 2009-2010 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implements a property manager based on MongoDB.
"""
from wsgidav import util
import pymongo

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)
    
#===============================================================================
# MongoPropertyManager
#===============================================================================
class MongoPropertyManager(object):
    """
Implements a property manager based on MongoDB.
    """
    def __init__(self, options):
        self.options = options
        self.conn = pymongo.Connection(options.get("host"), options.get("port"))
        self.db = self.conn[options.get("dbName", "wsgidav-props")]
        self.collection = self.db["properties"]
        util.log("Connected %r" % self)

    def __repr__(self):
        return "MongoPropertyManager(%s)" % self.db

    def __del__(self):
#        self.conn.close()
        pass

    def _sync(self):
        pass
    
    def _check(self, msg=""):
        pass

    def _dump(self, msg="", out=None):
        pass

    def getProperties(self, normurl):
        _logger.debug("getProperties(%s)" % normurl)
        doc = self.collection.find_one({"_url": normurl})
        if not doc:
            return []
#            for propdata in doc.keys():
#                returnlist.append(propdata)
        propNames = doc.keys()
        # Hide mongo key
        for hidden in ("_id", "_url"):
            if hidden in propNames:
                propNames.remove(hidden) 
        return propNames

    def getProperty(self, normurl, propname):
        _logger.debug("getProperty(%s, %s)" % (normurl, propname))
        doc = self.collection.find_one({"_url": normurl})
        if not doc:
            return None
        prop = doc.get(propname)
        return prop

    def writeProperty(self, normurl, propname, propertyvalue, dryRun=False):
#        self._log("writeProperty(%s, %s, dryRun=%s):\n\t%s" % (normurl, propname, dryRun, propertyvalue))
        assert normurl and normurl.startswith("/")
        assert propname #and propname.startswith("{")
        assert propname not in ("_id", "_url"), "MongoDB keys are protected (%s)" % propname
        assert propertyvalue is not None
        
        _logger.debug("writeProperty(%s, %s, dryRun=%s):\n\t%s" % (normurl, propname, dryRun, propertyvalue))
        if dryRun:
            return  # TODO: can we check anything here?

        doc = self.collection.find_one({"_url": normurl})
        if not doc:
            doc = {"_url": normurl}
        doc[propname] = propertyvalue
        self.collection.save(doc)

    def removeProperty(self, normurl, propname, dryRun=False):
        """
        Specifying the removal of a property that does not exist is NOT an error.
        """
        _logger.debug("removeProperty(%s, %s, dryRun=%s)" % (normurl, propname, dryRun))
        if dryRun:
            # TODO: can we check anything here?
            return  
        doc = self.collection.find_one({"_url": normurl})
        if not doc or doc.get(propname) is None:
            return
        del doc[propname]
        self.collection.save(doc)

    def removeProperties(self, normurl):
        _logger.debug("removeProperties(%s)" % normurl)
        doc = self.collection.find_one({"_url": normurl})
        if doc:
            self.collection.remove(doc)
        return

    def copyProperties(self, srcurl, desturl):
        _logger.debug("copyProperties(%s, %s)" % (srcurl, desturl))
        doc = self.collection.find_one({"_url": srcurl})
        raise NotImplementedError
        doc2 = doc.copy()
        self.collection.insert(doc2)

    def moveProperties(self, srcurl, desturl, withChildren):
        _logger.debug("moveProperties(%s, %s, %s)" % (srcurl, desturl, withChildren))
        raise NotImplementedError
        if withChildren:
            # Move srcurl\*      
            match = srcurl.rstrip("/") + "/*"
            docList = self.collection.find({"_url": match})
            for doc in docList:
                doc._url = desturl 
                self.collection.save(doc)
                destUrl = doc._url.replace(srcurl, desturl)
#                print "moveProperties:", url, d
        else:
            # Move srcurl only      
            doc = self.collection.find_one({"_url": srcurl})
            if doc:
                doc._url = desturl 
                self.collection.save(doc)
