# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Implements two property managers: one in-memory (dict-based), and one
persistent low performance variant using shelve.

The properties dictionaray is built like::

    { ref-url1: {propname1: value1,
                 propname2: value2,
                 },
      ref-url2: {propname1: value1,
                 propname2: value2,
                 },
      }

"""
from wsgidav import util
from wsgidav.rw_lock import ReadWriteLock

import os
import shelve


# TODO: comment's from Ian Bicking (2005)
# @@: Use of shelve means this is only really useful in a threaded environment.
#    And if you have just a single-process threaded environment, you could get
#    nearly the same effect with a dictionary of threading.Lock() objects.  Of course,
#    it would be better to move off shelve anyway, probably to a system with
#    a directory of per-file locks, using the file locking primitives (which,
#    sadly, are not quite portable).
# @@: It would probably be easy to store the properties as pickle objects
# in a parallel directory structure to the files you are describing.
# Pickle is expedient, but later you could use something more readable
# (pickles aren't particularly readable)

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)


# ========================================================================
# PropertyManager
# ========================================================================
class PropertyManager(object):
    """
    An in-memory property manager implementation using a dictionary.

    This is obviously not persistent, but should be enough in some cases.
    For a persistent implementation, see property_manager.ShelvePropertyManager().
    """

    def __init__(self):
        self._dict = None
        self._loaded = False
        self._lock = ReadWriteLock()
        self._verbose = 3

    def __repr__(self):
        return "PropertyManager"

    def __del__(self):
        if __debug__ and self._verbose >= 4:
            self._check()
        self._close()

    def _lazy_open(self):
        _logger.debug("_lazy_open()")
        self._lock.acquire_write()
        try:
            self._dict = {}
            self._loaded = True
        finally:
            self._lock.release()

    def _sync(self):
        pass

    def _close(self):
        _logger.debug("_close()")
        self._lock.acquire_write()
        try:
            self._dict = None
            self._loaded = False
        finally:
            self._lock.release()

    def _check(self, msg=""):
        try:
            if not self._loaded:
                return True
            for k, v in self._dict.items():
                _dummy = "{}, {}".format(k, v)  # noqa
            #            _logger.debug("{} checks ok {}".format(self.__class__.__name__, msg))
            return True
        except Exception:
            _logger.exception(
                "{} _check: ERROR {}".format(self.__class__.__name__, msg)
            )
            return False

    def _dump(self, msg=""):
        _logger.info("{}({}): {}".format(self.__class__.__name__, self.__repr__(), msg))
        if not self._loaded:
            self._lazy_open()
            if self._verbose >= 4:
                return  # Already dumped in _lazy_open
        try:
            for k, v in self._dict.items():
                _logger.info("    {}".format(k))
                for k2, v2 in v.items():
                    try:
                        _logger.info("        {}: '{}'".format(k2, v2))
                    except Exception as e:
                        _logger.info("        {}: ERROR {}".format(k2, e))
            # _logger.flush()
        except Exception as e:
            _logger.error("PropertyManager._dump()  ERROR: {}".format(e))

    def get_properties(self, norm_url, environ=None):
        _logger.debug("get_properties({})".format(norm_url))
        self._lock.acquire_read()
        try:
            if not self._loaded:
                self._lazy_open()
            returnlist = []
            if norm_url in self._dict:
                for propdata in self._dict[norm_url].keys():
                    returnlist.append(propdata)
            return returnlist
        finally:
            self._lock.release()

    def get_property(self, norm_url, name, environ=None):
        _logger.debug("get_property({}, {})".format(norm_url, name))
        self._lock.acquire_read()
        try:
            if not self._loaded:
                self._lazy_open()
            if norm_url not in self._dict:
                return None
            # TODO: sometimes we get exceptions here: (catch or otherwise make
            # more robust?)
            try:
                resourceprops = self._dict[norm_url]
            except Exception as e:
                _logger.exception(
                    "get_property({}, {}) failed : {}".format(norm_url, name, e)
                )
                raise
            return resourceprops.get(name)
        finally:
            self._lock.release()

    def write_property(
        self, norm_url, name, property_value, dry_run=False, environ=None
    ):
        assert norm_url and norm_url.startswith("/")
        assert name  # and name.startswith("{")
        assert property_value is not None

        _logger.debug(
            "write_property({}, {}, dry_run={}):\n\t{}".format(
                norm_url, name, dry_run, property_value
            )
        )
        if dry_run:
            return  # TODO: can we check anything here?

        self._lock.acquire_write()
        try:
            if not self._loaded:
                self._lazy_open()
            if norm_url in self._dict:
                locatordict = self._dict[norm_url]
            else:
                locatordict = {}  # dict([])
            locatordict[name] = property_value
            # This re-assignment is important, so Shelve realizes the change:
            self._dict[norm_url] = locatordict
            self._sync()
            if __debug__ and self._verbose >= 4:
                self._check()
        finally:
            self._lock.release()

    def remove_property(self, norm_url, name, dry_run=False, environ=None):
        """
        Specifying the removal of a property that does not exist is NOT an error.
        """
        _logger.debug(
            "remove_property({}, {}, dry_run={})".format(norm_url, name, dry_run)
        )
        if dry_run:
            # TODO: can we check anything here?
            return
        self._lock.acquire_write()
        try:
            if not self._loaded:
                self._lazy_open()
            if norm_url in self._dict:
                locatordict = self._dict[norm_url]
                if name in locatordict:
                    del locatordict[name]
                    # This re-assignment is important, so Shelve realizes the
                    # change:
                    self._dict[norm_url] = locatordict
                    self._sync()
            if __debug__ and self._verbose >= 4:
                self._check()
        finally:
            self._lock.release()

    def remove_properties(self, norm_url, environ=None):
        _logger.debug("remove_properties({})".format(norm_url))
        self._lock.acquire_write()
        try:
            if not self._loaded:
                self._lazy_open()
            if norm_url in self._dict:
                del self._dict[norm_url]
                self._sync()
        finally:
            self._lock.release()

    def copy_properties(self, src_url, dest_url, environ=None):
        _logger.debug("copy_properties({}, {})".format(src_url, dest_url))
        self._lock.acquire_write()
        try:
            if __debug__ and self._verbose >= 4:
                self._check()
            if not self._loaded:
                self._lazy_open()
            if src_url in self._dict:
                self._dict[dest_url] = self._dict[src_url].copy()
                self._sync()
            if __debug__ and self._verbose >= 4:
                self._check("after copy")
        finally:
            self._lock.release()

    def move_properties(self, src_url, dest_url, with_children, environ=None):
        _logger.debug(
            "move_properties({}, {}, {})".format(src_url, dest_url, with_children)
        )
        self._lock.acquire_write()
        try:
            if __debug__ and self._verbose >= 4:
                self._check()
            if not self._loaded:
                self._lazy_open()
            if with_children:
                # Move src_url\*
                for url in list(self._dict.keys()):
                    if util.is_equal_or_child_uri(src_url, url):
                        d = url.replace(src_url, dest_url)
                        self._dict[d] = self._dict[url]
                        del self._dict[url]
            elif src_url in self._dict:
                # Move src_url only
                self._dict[dest_url] = self._dict[src_url]
                del self._dict[src_url]
            self._sync()
            if __debug__ and self._verbose >= 4:
                self._check("after move")
        finally:
            self._lock.release()


# ========================================================================
# ShelvePropertyManager
# ========================================================================


class ShelvePropertyManager(PropertyManager):
    """
    A low performance property manager implementation using shelve
    """

    def __init__(self, storage_path):
        self._storage_path = os.path.abspath(storage_path)
        super(ShelvePropertyManager, self).__init__()

    def __repr__(self):
        return "ShelvePropertyManager({})".format(self._storage_path)

    def _lazy_open(self):
        _logger.debug("_lazy_open({})".format(self._storage_path))
        self._lock.acquire_write()
        try:
            # Test again within the critical section
            if self._loaded:
                return True
            # Open with writeback=False, which is faster, but we have to be
            # careful to re-assign values to _dict after modifying them
            self._dict = shelve.open(self._storage_path, writeback=False)
            self._loaded = True
            if __debug__ and self._verbose >= 4:
                self._check("After shelve.open()")
                self._dump("After shelve.open()")
        finally:
            self._lock.release()

    def _sync(self):
        """Write persistent dictionary to disc."""
        _logger.debug("_sync()")
        self._lock.acquire_write()  # TODO: read access is enough?
        try:
            if self._loaded:
                self._dict.sync()
        finally:
            self._lock.release()

    def _close(self):
        _logger.debug("_close()")
        self._lock.acquire_write()
        try:
            if self._loaded:
                self._dict.close()
                self._dict = None
                self._loaded = False
        finally:
            self._lock.release()

    def clear(self):
        """Delete all entries."""
        self._lock.acquire_write()
        try:
            was_closed = self._dict is None
            if was_closed:
                self.open()
            if len(self._dict):
                self._dict.clear()
                self._dict.sync()
            if was_closed:
                self.close()
        finally:
            self._lock.release()
