# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implements a property manager based on MongoDB.

Usage: add this lines to wsgidav.conf::

    from wsgidav.prop_man.mongo_property_manager import MongoPropertyManager
    prop_man_opts = {}
    property_manager = MongoPropertyManager(prop_man_opts)

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
from __future__ import print_function
from wsgidav import compat, util

import pymongo


__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)

# We use these keys internally, so they must be protected
HIDDEN_KEYS = ("_id", "_url", "_title")

# MongiDB doesn't accept '.' in key names, so we have to escape it.
# Use a key that is unlikely to occur in proprty names
DOT_ESCAPE = "^"


def encode_mongo_key(s):
    """Return an encoded version of `s` that may be used as MongoDB key."""
    assert DOT_ESCAPE not in s
    return s.replace(".", DOT_ESCAPE)


def decode_mongo_key(key):
    """Decode a string that was encoded by encode_mongo_key()."""
    return key.replace(DOT_ESCAPE, ".")


# ============================================================================
# MongoPropertyManager
# ============================================================================
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
                raise RuntimeError(
                    "Failed to logon to db %s as user %s"
                    % (self.db.name, opts.get("user"))
                )
            _logger.info(
                "Logged on to mongo db '%s' as user '%s'"
                % (self.db.name, opts.get("user"))
            )

        self.collection = self.db["properties"]
        _logger.info("MongoPropertyManager connected %r" % self.collection)
        self.collection.ensure_index("_url")

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

    def get_properties(self, norm_url, environ=None):
        _logger.debug("get_properties(%s)" % norm_url)
        doc = self.collection.find_one({"_url": norm_url})
        propNames = []
        if doc:
            for name in doc.keys():
                if name not in HIDDEN_KEYS:
                    propNames.append(decode_mongo_key(name))
        return propNames

    def get_property(self, norm_url, name, environ=None):
        _logger.debug("get_property(%s, %s)" % (norm_url, name))
        doc = self.collection.find_one({"_url": norm_url})
        if not doc:
            return None
        prop = doc.get(encode_mongo_key(name))
        return prop

    def write_property(
        self, norm_url, name, property_value, dry_run=False, environ=None
    ):
        assert norm_url and norm_url.startswith("/")
        assert name
        assert property_value is not None
        assert name not in HIDDEN_KEYS, "MongoDB key is protected: '%s'" % name

        _logger.debug(
            "write_property(%s, %s, dry_run=%s):\n\t%s"
            % (norm_url, name, dry_run, property_value)
        )
        if dry_run:
            return  # TODO: can we check anything here?

        doc = self.collection.find_one({"_url": norm_url})
        if not doc:
            doc = {"_url": norm_url, "_title": compat.quote(norm_url)}
        doc[encode_mongo_key(name)] = property_value
        self.collection.save(doc)

    def remove_property(self, norm_url, name, dry_run=False, environ=None):
        """"""
        _logger.debug("remove_property(%s, %s, dry_run=%s)" % (norm_url, name, dry_run))
        if dry_run:
            # TODO: can we check anything here?
            return
        doc = self.collection.find_one({"_url": norm_url})
        # Specifying the removal of a property that does not exist is NOT an error.
        if not doc or doc.get(encode_mongo_key(name)) is None:
            return
        del doc[encode_mongo_key(name)]
        self.collection.save(doc)

    def remove_properties(self, norm_url, environ=None):
        _logger.debug("remove_properties(%s)" % norm_url)
        doc = self.collection.find_one({"_url": norm_url})
        if doc:
            self.collection.remove(doc)
        return

    def copy_properties(self, srcUrl, destUrl, environ=None):
        doc = self.collection.find_one({"_url": srcUrl})
        if not doc:
            _logger.debug(
                "copy_properties(%s, %s): src has no properties" % (srcUrl, destUrl)
            )
            return
        _logger.debug("copy_properties(%s, %s)" % (srcUrl, destUrl))
        doc2 = doc.copy()
        self.collection.insert(doc2)

    def move_properties(self, srcUrl, destUrl, with_children, environ=None):
        _logger.debug("move_properties(%s, %s, %s)" % (srcUrl, destUrl, with_children))
        if with_children:
            # Match URLs that are equal to <srcUrl> or begin with '<srcUrl>/'
            matchBegin = "^" + srcUrl.rstrip("/") + "/"
            query = {"$or": [{"_url": srcUrl}, {"_url": {"$regex": matchBegin}}]}
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
