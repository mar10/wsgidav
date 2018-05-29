# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implements a property manager based on CouchDB.


http://wiki.apache.org/couchdb/Reference
http://packages.python.org/CouchDB/views.html


Usage: add this lines to wsgidav.conf::

    from wsgidav.addons.couch_property_manager import CouchPropertyManager
    prop_man_opts = {}
    property_manager = CouchPropertyManager(prop_man_opts)

Valid options are (sample shows defaults)::

    opts = {"url": "http://localhost:5984/",  # CouchDB server
            "dbName": "wsgidav-props",        # Name of DB to store the properties
            }

"""
from __future__ import print_function

from uuid import uuid4

import couchdb
from wsgidav import compat, util

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)

# ============================================================================
# CouchPropertyManager
# ============================================================================


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
            _logger.info("CouchPropertyManager connected to %s v%s" %
                         (self.db, self.couch.version()))
        else:
            self.db = self.couch.create(dbName)
            _logger.info("CouchPropertyManager created new db %s v%s" %
                         (self.db, self.couch.version()))

        # Ensure that we have a permanent view
        if "_design/properties" not in self.db:
            map = """
            function(doc) {
                if(doc.type == 'properties') {
                    emit(doc.url, { 'id': doc._id, 'url': doc.url });
                }
            }
            """
            designDoc = {
                "_id": "_design/properties",
                # "_rev": "42351258",
                "language": "javascript",
                "views": {
                    "titles": {
                        "map": ("function(doc) { emit(null, { 'id': doc._id, "
                                "'title': doc.title }); }")
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

    def _find_descendents(self, url):
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

    def get_properties(self, normurl, environ=None):
        _logger.debug("get_properties(%s)" % normurl)
        doc = self._find(normurl)
        propNames = []
        if doc:
            for name in doc["properties"].keys():
                propNames.append(name)
        return propNames

    def get_property(self, normurl, propname, environ=None):
        _logger.debug("get_property(%s, %s)" % (normurl, propname))
        doc = self._find(normurl)
        if not doc:
            return None
        prop = doc["properties"].get(propname)
        return prop

    def write_property(self, normurl, propname, propertyvalue, dryRun=False, environ=None):
        assert normurl and normurl.startswith("/")
        assert propname
        assert propertyvalue is not None

        _logger.debug("write_property(%s, %s, dryRun=%s):\n\t%s" %
                      (normurl, propname, dryRun, propertyvalue))
        if dryRun:
            return  # TODO: can we check anything here?

        doc = self._find(normurl)
        if doc:
            doc["properties"][propname] = propertyvalue
        else:
            doc = {"_id": uuid4().hex,  # Documentation suggests to set the id
                   "url": normurl,
                   "title": compat.quote(normurl),
                   "type": "properties",
                   "properties": {propname: propertyvalue}
                   }
        self.db.save(doc)

    def remove_property(self, normurl, propname, dryRun=False, environ=None):
        _logger.debug("remove_property(%s, %s, dryRun=%s)" % (normurl, propname, dryRun))
        if dryRun:
            # TODO: can we check anything here?
            return
        doc = self._find(normurl)
        # Specifying the removal of a property that does not exist is NOT an error.
        if not doc or doc["properties"].get(propname) is None:
            return
        del doc["properties"][propname]
        self.db.save(doc)

    def remove_properties(self, normurl, environ=None):
        _logger.debug("remove_properties(%s)" % normurl)
        doc = self._find(normurl)
        if doc:
            self.db.delete(doc)
        return

    def copy_properties(self, srcUrl, destUrl, environ=None):
        doc = self._find(srcUrl)
        if not doc:
            _logger.debug("copy_properties(%s, %s): src has no properties" % (srcUrl, destUrl))
            return
        _logger.debug("copy_properties(%s, %s)" % (srcUrl, destUrl))
        assert not self._find(destUrl)
        doc2 = {"_id": uuid4().hex,
                "url": destUrl,
                "title": compat.quote(destUrl),
                "type": "properties",
                "properties": doc["properties"],
                }
        self.db.save(doc2)

    def move_properties(self, srcUrl, destUrl, withChildren, environ=None):
        _logger.debug("move_properties(%s, %s, %s)" % (srcUrl, destUrl, withChildren))
        if withChildren:
            # Match URLs that are equal to <srcUrl> or begin with '<srcUrl>/'
            docList = self._find_descendents(srcUrl)
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

# ============================================================================
#
# ============================================================================


def test():
    pass


if __name__ == "__main__":
    test()
