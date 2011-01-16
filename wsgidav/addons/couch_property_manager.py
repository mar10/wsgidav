# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implements a property manager based on CouchDB.


http://wiki.apache.org/couchdb/Reference
http://packages.python.org/CouchDB/views.html


Usage: add this lines to wsgidav.conf::

    from wsgidav.addons.couch_property_manager import CouchPropertyManager
    prop_man_opts = {}
    propsmanager = CouchPropertyManager(prop_man_opts)

Valid options are (sample shows defaults)::

    opts = {"url": "http://localhost:5984/",  # CouchDB server 
            "dbName": "wsgidav-props",        # Name of DB to store the properties
            }

"""
from wsgidav import util
import couchdb
from urllib import quote
from uuid import uuid4

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

#===============================================================================
# CouchPropertyManager
#===============================================================================
class CouchPropertyManager(object):
    """Implements a property manager based on CouchDB."""
    def __init__(self, options):
        self.options = options
        self._connect()

    def __del__(self):
        self._disconnect()
            
    def _connect(self):
        opts = self.options
        if opts.get("url"):
            self.couch = couchdb.Server(opts.get("url"))
        else:
            self.couch = couchdb.Server()

        dbName = opts.get("dbName", "wsgidav_props")
        if dbName in self.couch:
            self.db = self.couch[dbName]
            util.log("CouchPropertyManager connected to %s v%s" % (self.db, self.couch.version()))
        else:
            self.db = self.couch.create(dbName)
            util.log("CouchPropertyManager created new db %s v%s" % (self.db, self.couch.version()))

        # Ensure that we have a permanent view
        if not "_design/properties" in self.db:
            map = """
            function(doc) {
                if(doc.type == 'properties') {
                    emit(doc.url, { 'id': doc._id, 'url': doc.url });
                }
            }
            """
            designDoc = {
                "_id": "_design/properties",
#                "_rev": "42351258",
                "language": "javascript",
                "views": {
                    "titles": {
                        "map": "function(doc) { emit(null, { 'id': doc._id, 'title': doc.title }); }"
                        },
                    # http://127.0.0.1:5984/wsgidav_props/_design/properties/_view/by_url
                    "by_url": {
                        "map": map
                        }
                    }
                }
            self.db.save(designDoc)

#        pprint(self.couch.stats())

    def _disconnect(self):
        pass
    
    def __repr__(self):
        return "CouchPropertyManager(%s)" % self.db

    def _sync(self):
        pass
    
    def _check(self, msg=""):
        pass

    def _dump(self, msg="", out=None):
        pass
    
    def _find(self, url):
        """Return properties document for path."""
        # Query the permanent view to find a url   
        vr = self.db.view("properties/by_url", key=url, include_docs=True)
        _logger.debug("find(%r) returned %s" % (url, len(vr)))
        assert len(vr) <= 1, "Found multiple matches for %r" % url
        for row in vr:
            assert row.doc
            return row.doc
        return None

    def _findDescendents(self, url):
        """Return properties document for url and all children."""
        # Ad-hoc query for URL starting with a prefix
        map_fun = """function(doc) {
                var url = doc.url + "/";
                if(doc.type === 'properties' && url.indexOf('%s') === 0) {
                    emit(doc.url, { 'id': doc._id, 'url': doc.url });
                }
            }""" % (url + "/")
        vr = self.db.query(map_fun, include_docs=True)    
        for row in vr:
            yield row.doc
        return

    def getProperties(self, normurl):
        _logger.debug("getProperties(%s)" % normurl)
        doc = self._find(normurl)
        propNames = []
        if doc:
            for name in doc["properties"].keys():
                propNames.append(name)
        return propNames

    def getProperty(self, normurl, propname):
        _logger.debug("getProperty(%s, %s)" % (normurl, propname))
        doc = self._find(normurl)
        if not doc:
            return None
        prop = doc["properties"].get(propname)
        return prop

    def writeProperty(self, normurl, propname, propertyvalue, dryRun=False):
        assert normurl and normurl.startswith("/")
        assert propname
        assert propertyvalue is not None
        
        _logger.debug("writeProperty(%s, %s, dryRun=%s):\n\t%s" % (normurl, propname, dryRun, propertyvalue))
        if dryRun:
            return  # TODO: can we check anything here?

        doc = self._find(normurl)
        if doc:
            doc["properties"][propname] = propertyvalue
        else:
            doc = {"_id": uuid4().hex,  # Documentation suggests to set the id
                   "url": normurl,
                   "title": quote(normurl),
                   "type": "properties",
                   "properties": {propname: propertyvalue}
                   }
        self.db.save(doc)

    def removeProperty(self, normurl, propname, dryRun=False):
        _logger.debug("removeProperty(%s, %s, dryRun=%s)" % (normurl, propname, dryRun))
        if dryRun:
            # TODO: can we check anything here?
            return  
        doc = self._find(normurl)
        # Specifying the removal of a property that does not exist is NOT an error.
        if not doc or doc["properties"].get(propname) is None:
            return
        del doc["properties"][propname]
        self.db.save(doc)

    def removeProperties(self, normurl):
        _logger.debug("removeProperties(%s)" % normurl)
        doc = self._find(normurl)
        if doc:
            self.db.delete(doc)
        return

    def copyProperties(self, srcUrl, destUrl):
        doc = self._find(srcUrl)
        if not doc:
            _logger.debug("copyProperties(%s, %s): src has no properties" % (srcUrl, destUrl))
            return
        _logger.debug("copyProperties(%s, %s)" % (srcUrl, destUrl))
        assert not self._find(destUrl)
        doc2 = {"_id": uuid4().hex,
                "url": destUrl,
                "title": quote(destUrl),
                "type": "properties",
                "properties": doc["properties"],
                }
        self.db.save(doc2)

    def moveProperties(self, srcUrl, destUrl, withChildren):
        _logger.debug("moveProperties(%s, %s, %s)" % (srcUrl, destUrl, withChildren))
        if withChildren:
            # Match URLs that are equal to <srcUrl> or begin with '<srcUrl>/'
            docList = self._findDescendents(srcUrl)
            for doc in docList:
                newDest = doc["url"].replace(srcUrl, destUrl)
                _logger.debug("move property %s -> %s" % (doc["url"], newDest))
                doc["url"] = newDest 
                self.db.save(doc)
        else:
            # Move srcUrl only      
            # TODO: use findAndModify()?
            doc = self._find(srcUrl)
            if doc:
                _logger.debug("move property %s -> %s" % (doc["url"], destUrl))
                doc["url"] = destUrl 
                self.db.save(doc)
        return

#===============================================================================
# 
#===============================================================================
def test():
    pass


if __name__ == "__main__":
    test()