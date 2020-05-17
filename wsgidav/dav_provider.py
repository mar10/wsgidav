# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Abstract base class for DAV resource providers.

This module serves these purposes:

  1. Documentation of the DAVProvider interface
  2. Common base class for all DAV providers
  3. Default implementation for most functionality that a resource provider must
     deliver.

If no default implementation can be provided, then all write actions generate
FORBIDDEN errors. Read requests generate NOT_IMPLEMENTED errors.


**_DAVResource, DAVCollection, DAVNonCollection**

Represents an existing (i.e. mapped) WebDAV resource or collection.

A _DAVResource object is created by a call to the DAVProvider.

The resource may then be used to query different attributes like ``res.name``,
``res.is_collection``, ``res.get_content_length()``, and ``res.support_etag()``.

It also implements operations, that require an *existing* resource, like:
``get_preferred_path()``, ``create_collection()``, or ``get_property_value()``.

Usage::

    res = provider.get_resource_inst(path, environ)
    if res is not None:
        print(res.getName())



**DAVProvider**

A DAV provider represents a shared WebDAV system.

There is only one provider instance per share, which is created during
server start-up. After that, the dispatcher (``request_resolver.RequestResolver``)
parses the request URL and adds it to the WSGI environment, so it
can be accessed like this::

    provider = environ["wsgidav.provider"]

The main purpose of the provider is to create _DAVResource objects for URLs::

    res = provider.get_resource_inst(path, environ)


**Supporting Objects**
The DAVProvider takes two supporting objects:

propertyManager
   An object that provides storage for dead properties assigned for webDAV resources.

   PropertyManagers must provide the methods as described in
   ``wsgidav.interfaces.propertymanagerinterface``

   See prop_man.property_manager.PropertyManager for a sample implementation
   using shelve.

lockManager
   An object that provides storage for locks made on webDAV resources.

   LockManagers must provide the methods as described in
   ``wsgidav.interfaces.lockmanagerinterface``

   See lock_manager.LockManager for a sample implementation
   using shelve.

See :doc:`reference_guide` for more information about the WsgiDAV architecture.
"""
from wsgidav import compat, util, xml_tools
from wsgidav.dav_error import (
    as_DAVError,
    DAVError,
    HTTP_FORBIDDEN,
    HTTP_NOT_FOUND,
    PRECONDITION_CODE_ProtectedProperty,
)
from wsgidav.util import etree

import os
import sys
import time
import traceback


__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)

_standardLivePropNames = [
    "{DAV:}creationdate",
    "{DAV:}displayname",
    "{DAV:}getcontenttype",
    "{DAV:}resourcetype",
    "{DAV:}getlastmodified",
    "{DAV:}getcontentlength",
    "{DAV:}getetag",
    "{DAV:}getcontentlanguage",
    # "{DAV:}source", # removed in rfc4918
]
_lockPropertyNames = ["{DAV:}lockdiscovery", "{DAV:}supportedlock"]


# ========================================================================
# _DAVResource
# ========================================================================


class _DAVResource(object):
    r"""Represents a single existing DAV resource instance.

    A resource may be a collection (aka 'folder') or a non-collection (aka
    'file').
    _DAVResource is the common base class for the specialized classes::

        _DAVResource
          +- DAVCollection
          \- DAVNonCollection

    Instances of this class are created through the DAVProvider::

        res = provider.get_resource_inst(path, environ)
        if res and res.is_collection():
            print(res.get_display_name())

    In the example above, res will be ``None``, if the path cannot be mapped to
    an existing resource.
    The following attributes and methods are considered 'cheap'::

        res.path
        res.provider
        res.name
        res.is_collection
        res.environ

    Querying other attributes is considered 'expensive' and may be delayed until
    the first access.

        get_content_length()
        get_content_type()
        get_creation_date()
        get_display_name()
        get_etag()
        get_last_modified()
        support_ranges()

        support_etag()
        support_modified()
        support_content_length()

    These functions return ``None``, if the property is not available, or
    not supported.

    See also DAVProvider.get_resource_inst().
    """

    def __init__(self, path, is_collection, environ):
        assert compat.is_native(path)
        assert path == "" or path.startswith("/")
        self.provider = environ["wsgidav.provider"]
        self.path = path
        self.is_collection = is_collection
        self.environ = environ
        self.name = util.get_uri_name(self.path)

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.path)

    #    def getContentLanguage(self):
    #        """Contains the Content-Language header returned by a GET without accept
    #        headers.
    #
    #        The getcontentlanguage property MUST be defined on any DAV compliant
    #        resource that returns the Content-Language header on a GET.
    #        """
    #        raise NotImplementedError

    def get_content_length(self):
        """Contains the Content-Length header returned by a GET without accept
        headers.

        The getcontentlength property MUST be defined on any DAV compliant
        resource that returns the Content-Length header in response to a GET.

        This method MUST be implemented by non-collections only.
        """
        if self.is_collection:
            return None
        raise NotImplementedError

    def get_content_type(self):
        """Contains the Content-Type header returned by a GET without accept
        headers.

        This getcontenttype property MUST be defined on any DAV compliant
        resource that returns the Content-Type header in response to a GET.
        See http://www.webdav.org/specs/rfc4918.html#PROPERTY_getcontenttype

        This method MUST be implemented by non-collections only.
        """
        if self.is_collection:
            return None
        raise NotImplementedError

    def get_creation_date(self):
        """Records the time and date the resource was created.

        The creationdate property should be defined on all DAV compliant
        resources. If present, it contains a timestamp of the moment when the
        resource was created (i.e., the moment it had non-null state).

        This method SHOULD be implemented, especially by non-collections.
        """
        return None

    def get_directory_info(self):
        """Return a list of dictionaries with information for directory
        rendering.

        This default implementation return None, so the dir browser will
        traverse all members.

        This method COULD be implemented for collection resources.
        """
        assert self.is_collection
        return None

    def get_display_name(self):
        """Provides a name for the resource that is suitable for presentation to
        a user.

        The displayname property should be defined on all DAV compliant
        resources. If present, the property contains a description of the
        resource that is suitable for presentation to a user.

        This default implementation returns `name`, which is the last path
        segment.
        """
        return self.name

    def get_display_info(self):
        """Return additional info dictionary for displaying (optional).

        This information is not part of the DAV specification, but meant for use
        by the dir browser middleware.

        This default implementation returns ``{'type': '...'}``
        """
        if self.is_collection:
            return {"type": "Directory"}
        elif os.extsep in self.name:
            ext = self.name.split(os.extsep)[-1].upper()
            if len(ext) < 5:
                return {"type": "{}-File".format(ext)}
        return {"type": "File"}

    def get_etag(self):
        """
        See http://www.webdav.org/specs/rfc4918.html#PROPERTY_getetag

        This method SHOULD be implemented, especially by non-collections.
        """
        return None

    def get_last_modified(self):
        """Contains the Last-Modified header returned by a GET method without
        accept headers.

        Return None, if this live property is not supported.

        Note that the last-modified date on a resource may reflect changes in
        any part of the state of the resource, not necessarily just a change to
        the response to the GET method. For example, a change in a property may
        cause the last-modified date to change. The getlastmodified property
        MUST be defined on any DAV compliant resource that returns the
        Last-Modified header in response to a GET.

        This method SHOULD be implemented, especially by non-collections.
        """
        return None

    def set_last_modified(self, dest_path, time_stamp, dry_run):
        """Set last modified time for destPath to timeStamp on epoch-format"""
        raise NotImplementedError

    def support_ranges(self):
        """Return True, if this non-resource supports Range on GET requests.

        This method MUST be implemented by non-collections only.
        """
        raise NotImplementedError

    def support_content_length(self):
        """Return True, if this resource supports Content-Length.

        This default implementation checks `self.get_content_length() is None`.
        """
        return self.get_content_length() is not None

    def support_etag(self):
        """Return True, if this resource supports ETags.

        This default implementation checks `self.get_etag() is None`.
        """
        return self.get_etag() is not None

    def support_modified(self):
        """Return True, if this resource supports last modified dates.

        This default implementation checks `self.get_last_modified() is None`.
        """
        return self.get_last_modified() is not None

    def get_preferred_path(self):
        """Return preferred mapping for a resource mapping.

        Different URLs may map to the same resource, e.g.:
            '/a/b' == '/A/b' == '/a/b/'
        get_preferred_path() returns the same value for all these variants, e.g.:
            '/a/b/'   (assuming resource names considered case insensitive)

        @param path: a UTF-8 encoded, unquoted byte string.
        @return: a UTF-8 encoded, unquoted byte string.
        """
        if self.path in ("", "/"):
            return "/"
        # Append '/' for collections
        if self.is_collection and not self.path.endswith("/"):
            return self.path + "/"
        # TODO: handle case-sensitivity, depending on OS
        # (FileSystemProvider could do this with os.path:
        # (?) on unix we can assume that the path already matches exactly the case of filepath
        # on windows we could use path.lower() or get the real case from the
        # file system
        return self.path

    def get_ref_url(self):
        """Return the quoted, absolute, unique URL of a resource, relative to appRoot.

        Byte string, UTF-8 encoded, quoted.
        Starts with a '/'. Collections also have a trailing '/'.

        This is basically the same as get_preferred_path, but deals with
        'virtual locations' as well.

        e.g. '/a/b' == '/A/b' == '/bykey/123' == '/byguid/abc532'

        get_ref_url() returns the same value for all these URLs, so it can be
        used as a key for locking and persistence storage.

        DAV providers that allow virtual-mappings must override this method.

        See also comments in DEVELOPERS.txt glossary.
        """
        return compat.quote(self.provider.share_path + self.get_preferred_path())

    #    def getRefKey(self):
    #        """Return an unambigous identifier string for a resource.
    #
    #        Since it is always unique for one resource, <refKey> is used as key for
    #        the lock- and property storage dictionaries.
    #
    #        This default implementation calls get_ref_url(), and strips a possible
    #        trailing '/'.
    #        """
    #        refKey = self.get_ref_url(path)
    #        if refKey == "/":
    #            return refKey
    #        return refKey.rstrip("/")

    def get_href(self):
        """Convert path to a URL that can be passed to XML responses.

        Byte string, UTF-8 encoded, quoted.

        See http://www.webdav.org/specs/rfc4918.html#rfc.section.8.3
        We are using the path-absolute option. i.e. starting with '/'.
        URI ; See section 3.2.1 of [RFC2068]
        """
        # Nautilus chokes, if href encodes '(' as '%28'
        # So we don't encode 'extra' and 'safe' characters (see rfc2068 3.2.1)
        safe = "/" + "!*'()," + "$-_|."
        return compat.quote(
            self.provider.mount_path
            + self.provider.share_path
            + self.get_preferred_path(),
            safe=safe,
        )

    #    def getParent(self):
    #        """Return parent _DAVResource or None.
    #
    #        There is NO checking, if the parent is really a mapped collection.
    #        """
    #        parentpath = util.get_uri_parent(self.path)
    #        if not parentpath:
    #            return None
    #        return self.provider.get_resource_inst(parentpath)

    def get_member_list(self):
        """Return a list of direct members (_DAVResource or derived objects).

        This default implementation calls self.get_member_names() and
        self.get_member() for each of them.
        A provider COULD overwrite this for performance reasons.
        """
        if not self.is_collection:
            raise NotImplementedError
        memberList = []
        for name in self.get_member_names():
            member = self.get_member(name)
            assert member is not None
            memberList.append(member)
        return memberList

    def get_member_names(self):
        """Return list of (direct) collection member names (UTF-8 byte strings).

        Every provider MUST provide this method for collection resources.
        """
        raise NotImplementedError

    def get_descendants(
        self,
        collections=True,
        resources=True,
        depth_first=False,
        depth="infinity",
        add_self=False,
    ):
        """Return a list _DAVResource objects of a collection (children,
        grand-children, ...).

        This default implementation calls self.get_member_list() recursively.

        This function may also be called for non-collections (with add_self=True).

        :Parameters:
            depth_first : bool
                use <False>, to list containers before content.
                (e.g. when moving / copying branches.)
                Use <True>, to list content before containers.
                (e.g. when deleting branches.)
            depth : string
                '0' | '1' | 'infinity'
        """
        assert depth in ("0", "1", "infinity")
        res = []
        if add_self and not depth_first:
            res.append(self)
        if depth != "0" and self.is_collection:
            for child in self.get_member_list():
                if not child:
                    self.get_member_list()
                want = (collections and child.is_collection) or (
                    resources and not child.is_collection
                )
                if want and not depth_first:
                    res.append(child)
                if child.is_collection and depth == "infinity":
                    res.extend(
                        child.get_descendants(
                            collections, resources, depth_first, depth, add_self=False
                        )
                    )
                if want and depth_first:
                    res.append(child)
        if add_self and depth_first:
            res.append(self)
        return res

    # --- Properties ---------------------------------------------------------

    def get_property_names(self, is_allprop):
        """Return list of supported property names in Clark Notation.

        Note that 'allprop', despite its name, which remains for
        backward-compatibility, does not return every property, but only dead
        properties and the live properties defined in RFC4918.

        This default implementation returns a combination of:

        - Supported standard live properties in the {DAV:} namespace, if the
          related getter method returns not None.
        - {DAV:}lockdiscovery and {DAV:}supportedlock, if a lock manager is
          present
        - If a property manager is present, then a list of dead properties is
          appended

        A resource provider may override this method, to add a list of
        supported custom live property names.
        """
        # Live properties
        propNameList = []

        propNameList.append("{DAV:}resourcetype")

        if self.get_creation_date() is not None:
            propNameList.append("{DAV:}creationdate")
        if self.get_content_length() is not None:
            assert not self.is_collection
            propNameList.append("{DAV:}getcontentlength")
        if self.get_content_type() is not None:
            propNameList.append("{DAV:}getcontenttype")
        if self.get_last_modified() is not None:
            propNameList.append("{DAV:}getlastmodified")
        if self.get_display_name() is not None:
            propNameList.append("{DAV:}displayname")
        if self.get_etag() is not None:
            propNameList.append("{DAV:}getetag")

        # Locking properties
        if self.provider.lock_manager and not self.prevent_locking():
            propNameList.extend(_lockPropertyNames)

        # Dead properties
        if self.provider.prop_manager:
            refUrl = self.get_ref_url()
            propNameList.extend(
                self.provider.prop_manager.get_properties(refUrl, self.environ)
            )

        return propNameList

    def get_properties(self, mode, name_list=None):
        """Return properties as list of 2-tuples (name, value).

        If mode is 'name', then None is returned for the value.

        name
            the property name in Clark notation.
        value
            may have different types, depending on the status:
            - string or unicode: for standard property values.
            - etree.Element: for complex values.
            - DAVError in case of errors.
            - None: if mode == 'name'.

        @param mode: "allprop", "name", or "named"
        @param name_list: list of property names in Clark Notation (required for mode 'named')

        This default implementation basically calls self.get_property_names() to
        get the list of names, then call self.get_property_value on each of them.
        """
        assert mode in ("allprop", "name", "named")

        if mode in ("allprop", "name"):
            # TODO: 'allprop' could have nameList, when <include> option is
            # implemented
            assert name_list is None
            name_list = self.get_property_names(mode == "allprop")
        else:
            assert name_list is not None

        propList = []
        namesOnly = mode == "name"
        for name in name_list:
            try:
                if namesOnly:
                    propList.append((name, None))
                else:
                    value = self.get_property_value(name)
                    propList.append((name, value))
            except DAVError as e:
                propList.append((name, e))
            except Exception as e:
                propList.append((name, as_DAVError(e)))
                if self.provider.verbose >= 2:
                    traceback.print_exc(10, sys.stdout)

        return propList

    def get_property_value(self, name):
        """Return the value of a property.

        name:
            the property name in Clark notation.
        return value:
            may have different types, depending on the status:

            - string or unicode: for standard property values.
            - lxml.etree.Element: for complex values.

            If the property is not available, a DAVError is raised.

        This default implementation handles ``{DAV:}lockdiscovery`` and
        ``{DAV:}supportedlock`` using the associated lock manager.

        All other *live* properties (i.e. name starts with ``{DAV:}``) are
        delegated to the self.xxx() getters.

        Finally, other properties are considered *dead*, and are handled  by
        the associated property manager.
        """
        refUrl = self.get_ref_url()

        # lock properties
        lm = self.provider.lock_manager
        if lm and name == "{DAV:}lockdiscovery":
            # TODO: we return HTTP_NOT_FOUND if no lockmanager is present.
            # Correct?
            activelocklist = lm.get_url_lock_list(refUrl)
            lockdiscoveryEL = etree.Element(name)
            for lock in activelocklist:
                activelockEL = etree.SubElement(lockdiscoveryEL, "{DAV:}activelock")

                locktypeEL = etree.SubElement(activelockEL, "{DAV:}locktype")
                # Note: make sure `{DAV:}` is not handled as format tag:
                etree.SubElement(locktypeEL, "{}{}".format("{DAV:}", lock["type"]))

                lockscopeEL = etree.SubElement(activelockEL, "{DAV:}lockscope")
                # Note: make sure `{DAV:}` is not handled as format tag:
                etree.SubElement(lockscopeEL, "{}{}".format("{DAV:}", lock["scope"]))

                etree.SubElement(activelockEL, "{DAV:}depth").text = lock["depth"]
                if lock["owner"]:
                    # lock["owner"] is an XML string
                    # owner may be empty (#64)
                    ownerEL = xml_tools.string_to_xml(lock["owner"])
                    activelockEL.append(ownerEL)

                timeout = lock["timeout"]
                if timeout < 0:
                    timeout = "Infinite"
                else:
                    # The time remaining on the lock
                    expire = lock["expire"]
                    timeout = "Second-" + str(int(expire - time.time()))
                etree.SubElement(activelockEL, "{DAV:}timeout").text = timeout

                locktokenEL = etree.SubElement(activelockEL, "{DAV:}locktoken")
                etree.SubElement(locktokenEL, "{DAV:}href").text = lock["token"]

                # TODO: this is ugly:
                #       res.get_property_value("{DAV:}lockdiscovery")
                #
                #                lockRoot = self.get_href(self.provider.ref_url_to_path(lock["root"]))
                lockPath = self.provider.ref_url_to_path(lock["root"])
                lockRes = self.provider.get_resource_inst(lockPath, self.environ)
                # FIXME: test for None
                lockHref = lockRes.get_href()

                lockrootEL = etree.SubElement(activelockEL, "{DAV:}lockroot")
                etree.SubElement(lockrootEL, "{DAV:}href").text = lockHref

            return lockdiscoveryEL

        elif lm and name == "{DAV:}supportedlock":
            # TODO: we return HTTP_NOT_FOUND if no lockmanager is present. Correct?
            # TODO: the lockmanager should decide about it's features
            supportedlockEL = etree.Element(name)

            lockentryEL = etree.SubElement(supportedlockEL, "{DAV:}lockentry")
            lockscopeEL = etree.SubElement(lockentryEL, "{DAV:}lockscope")
            etree.SubElement(lockscopeEL, "{DAV:}exclusive")
            locktypeEL = etree.SubElement(lockentryEL, "{DAV:}locktype")
            etree.SubElement(locktypeEL, "{DAV:}write")

            lockentryEL = etree.SubElement(supportedlockEL, "{DAV:}lockentry")
            lockscopeEL = etree.SubElement(lockentryEL, "{DAV:}lockscope")
            etree.SubElement(lockscopeEL, "{DAV:}shared")
            locktypeEL = etree.SubElement(lockentryEL, "{DAV:}locktype")
            etree.SubElement(locktypeEL, "{DAV:}write")

            return supportedlockEL

        elif name.startswith("{DAV:}"):
            # Standard live property (raises HTTP_NOT_FOUND if not supported)
            if name == "{DAV:}creationdate" and self.get_creation_date() is not None:
                # Note: uses RFC3339 format (ISO 8601)
                return util.get_rfc3339_time(self.get_creation_date())
            elif name == "{DAV:}getcontenttype" and self.get_content_type() is not None:
                return self.get_content_type()
            elif name == "{DAV:}resourcetype":
                if self.is_collection:
                    resourcetypeEL = etree.Element(name)
                    etree.SubElement(resourcetypeEL, "{DAV:}collection")
                    return resourcetypeEL
                return ""
            elif (
                name == "{DAV:}getlastmodified" and self.get_last_modified() is not None
            ):
                # Note: uses RFC1123 format
                return util.get_rfc1123_time(self.get_last_modified())
            elif (
                name == "{DAV:}getcontentlength"
                and self.get_content_length() is not None
            ):
                # Note: must be a numeric string
                return str(self.get_content_length())
            elif name == "{DAV:}getetag" and self.get_etag() is not None:
                return self.get_etag()
            elif name == "{DAV:}displayname" and self.get_display_name() is not None:
                return self.get_display_name()

            # Unsupported, no persistence available, or property not found
            raise DAVError(HTTP_NOT_FOUND)

        # Dead property
        pm = self.provider.prop_manager
        if pm:
            value = pm.get_property(refUrl, name, self.environ)
            if value is not None:
                return xml_tools.string_to_xml(value)

        # No persistence available, or property not found
        raise DAVError(HTTP_NOT_FOUND)

    def set_property_value(self, name, value, dry_run=False):
        """Set a property value or remove a property.

        value == None means 'remove property'.
        Raise HTTP_FORBIDDEN if property is read-only, or not supported.

        When dry_run is True, this function should raise errors, as in a real
        run, but MUST NOT change any data.

        This default implementation

        - raises HTTP_FORBIDDEN, if trying to modify a locking property
        - raises HTTP_FORBIDDEN, if trying to modify an immutable {DAV:}
          property
        - handles Windows' Win32LastModifiedTime to set the getlastmodified
          property, if enabled
        - stores everything else as dead property, if a property manager is
          present.
        - raises HTTP_FORBIDDEN, else

        Removing a non-existing prop is NOT an error.

        Note: RFC 4918 states that {DAV:}displayname 'SHOULD NOT be protected'

        A resource provider may override this method, to update supported custom
        live properties.
        """
        assert value is None or xml_tools.is_etree_element(value)

        if name in _lockPropertyNames:
            # Locking properties are always read-only
            raise DAVError(
                HTTP_FORBIDDEN, err_condition=PRECONDITION_CODE_ProtectedProperty
            )

        # Live property
        config = self.environ["wsgidav.config"]
        # hotfixes = config.get("hotfixes", {})
        mutableLiveProps = config.get("mutable_live_props", [])
        # Accept custom live property updates on resources if configured.
        if (
            name.startswith("{DAV:}")
            and name in _standardLivePropNames
            and name in mutableLiveProps
        ):
            # Please note that some properties should not be mutable according
            # to RFC4918. This includes the 'getlastmodified' property, which
            # it may still make sense to make mutable in order to support time
            # stamp changes from e.g. utime calls or the touch or rsync -a
            # commands.
            if name in ("{DAV:}getlastmodified", "{DAV:}last_modified"):
                try:
                    return self.set_last_modified(self.path, value.text, dry_run)
                except Exception:
                    _logger.warning(
                        "Provider does not support set_last_modified on {}.".format(
                            self.path
                        )
                    )

            # Unsupported or not allowed
            raise DAVError(HTTP_FORBIDDEN)

        # Handle MS Windows Win32LastModifiedTime, if enabled.
        # Note that the WebDAV client in Win7 and earler has issues and can't be used
        # with this so we ignore older clients. Others pre-Win10 should be tested.
        if name.startswith("{urn:schemas-microsoft-com:}"):
            agent = self.environ.get("HTTP_USER_AGENT", "None")
            win32_emu = config.get("hotfixes", {}).get("emulate_win32_lastmod", False)
            if win32_emu and "MiniRedir/6.1" not in agent:
                if "Win32LastModifiedTime" in name:
                    return self.set_last_modified(self.path, value.text, dry_run)
                elif "Win32FileAttributes" in name:
                    return True
                elif "Win32CreationTime" in name:
                    return True
                elif "Win32LastAccessTime" in name:
                    return True

        # Dead property
        pm = self.provider.prop_manager
        if pm and not name.startswith("{DAV:}"):
            refUrl = self.get_ref_url()
            if value is None:
                return pm.remove_property(refUrl, name, dry_run, self.environ)
            else:
                value = etree.tostring(value)
                return pm.write_property(refUrl, name, value, dry_run, self.environ)

        raise DAVError(HTTP_FORBIDDEN)

    def remove_all_properties(self, recursive):
        """Remove all associated dead properties."""
        if self.provider.prop_manager:
            self.provider.prop_manager.remove_properties(
                self.get_ref_url(), self.environ
            )

    # --- Locking ------------------------------------------------------------

    def prevent_locking(self):
        """Return True, to prevent locking.

        This default implementation returns ``False``, so standard processing
        takes place: locking (and refreshing of locks) is implemented using
        the lock manager, if one is configured.
        """
        return False

    def is_locked(self):
        """Return True, if URI is locked."""
        if self.provider.lock_manager is None:
            return False
        return self.provider.lock_manager.is_url_locked(self.get_ref_url())

    def remove_all_locks(self, recursive):
        if self.provider.lock_manager:
            self.provider.lock_manager.remove_all_locks_from_url(self.get_ref_url())

    # --- Read / write -------------------------------------------------------

    def create_empty_resource(self, name):
        """Create and return an empty (length-0) resource as member of self.

        Called for LOCK requests on unmapped URLs.

        Preconditions (to be ensured by caller):

          - this must be a collection
          - <self.path + name> must not exist
          - there must be no conflicting locks

        Returns a DAVResuource.

        This method MUST be implemented by all providers that support write
        access.
        This default implementation simply raises HTTP_FORBIDDEN.
        """
        assert self.is_collection
        raise DAVError(HTTP_FORBIDDEN)

    def create_collection(self, name):
        """Create a new collection as member of self.

        Preconditions (to be ensured by caller):

          - this must be a collection
          - <self.path + name> must not exist
          - there must be no conflicting locks

        This method MUST be implemented by all providers that support write
        access.
        This default implementation raises HTTP_FORBIDDEN.
        """
        assert self.is_collection
        raise DAVError(HTTP_FORBIDDEN)

    def get_content(self):
        """Open content as a stream for reading.

        Returns a file-like object / stream containing the contents of the
        resource specified.
        The calling application will close() the stream.

        This method MUST be implemented by all providers.
        """
        assert not self.is_collection
        raise NotImplementedError

    def begin_write(self, content_type=None):
        """Open content as a stream for writing.

        This method MUST be implemented by all providers that support write
        access.
        """
        assert not self.is_collection
        raise DAVError(HTTP_FORBIDDEN)

    def end_write(self, with_errors):
        """Called when PUT has finished writing.

        This is only a notification. that MAY be handled.
        """
        pass

    def handle_delete(self):
        """Handle a DELETE request natively.

        This method is called by the DELETE handler after checking for valid
        request syntax and making sure that there are no conflicting locks and
        If-headers.
        Depending on the return value, this provider can control further
        processing:

        False:
            handle_delete() did not do anything. WsgiDAV will process the request
            by calling delete() for every resource, bottom-up.
        True:
            handle_delete() has successfully performed the DELETE request.
            HTTP_NO_CONTENT will be reported to the DAV client.
        List of errors:
            handle_delete() tried to perform the delete request, but failed
            completely or partially. A list of errors is returned like
            ``[ (<ref-url>, <DAVError>), ... ]``
            These errors will be reported to the client.
        DAVError raised:
            handle_delete() refuses to perform the delete request. The DAVError
            will be reported to the client.

        An implementation may choose to apply other semantics and return True.
        For example deleting '/by_tag/cool/myres' may simply remove the 'cool'
        tag from 'my_res'.
        In this case, the resource might still be available by other URLs, so
        locks and properties are not removed.

        This default implementation returns ``False``, so standard processing
        takes place.

        Implementation of this method is OPTIONAL.
        """
        return False

    def support_recursive_delete(self):
        """Return True, if delete() may be called on non-empty collections
        (see comments there).

        This method MUST be implemented for collections (not called on
        non-collections).
        """
        assert self.is_collection
        raise NotImplementedError

    def delete(self):
        """Remove this resource (recursive).

        Preconditions (ensured by caller):

          - there are no conflicting locks or If-headers
          - if support_recursive_delete() is False, and this is a collection,
            all members have already been deleted.

        When support_recursive_delete is True, this method must be prepared to
        handle recursive deletes. This implies that child errors must be
        reported as tuple list [ (<ref-url>, <DAVError>), ... ].
        See http://www.webdav.org/specs/rfc4918.html#delete-collections

        This function

          - removes this resource
          - if this is a non-empty collection, also removes all members.
            Note that this may only occur, if support_recursive_delete is True.
          - For recursive deletes, return a list of error tuples for all failed
            resource paths.
          - removes associated direct locks
          - removes associated dead properties
          - raises HTTP_FORBIDDEN for read-only resources
          - raises HTTP_INTERNAL_ERROR on error

        This method MUST be implemented by all providers that support write
        access.
        """
        raise NotImplementedError

    def handle_copy(self, dest_path, depth_infinity):
        """Handle a COPY request natively.

        This method is called by the COPY handler after checking for valid
        request syntax and making sure that there are no conflicting locks and
        If-headers.
        Depending on the return value, this provider can control further
        processing:

        False:
            handle_copy() did not do anything. WsgiDAV will process the request
            by calling copy_move_single() for every resource, bottom-up.
        True:
            handle_copy() has successfully performed the COPY request.
            HTTP_NO_CONTENT/HTTP_CREATED will be reported to the DAV client.
        List of errors:
            handle_copy() tried to perform the copy request, but failed
            completely or partially. A list of errors is returned like
            ``[ (<ref-url>, <DAVError>), ... ]``
            These errors will be reported to the client.
        DAVError raised:
            handle_copy() refuses to perform the copy request. The DAVError
            will be reported to the client.

        An implementation may choose to apply other semantics and return True.
        For example copying '/by_tag/cool/myres' to '/by_tag/hot/myres' may
        simply add a 'hot' tag.
        In this case, the resource might still be available by other URLs, so
        locks and properties are not removed.

        This default implementation returns ``False``, so standard processing
        takes place.

        Implementation of this method is OPTIONAL.
        """
        return False

    def copy_move_single(self, dest_path, is_move):
        """Copy or move this resource to destPath (non-recursive).

        Preconditions (ensured by caller):

          - there must not be any conflicting locks on destination
          - overwriting is only allowed (i.e. destPath exists), when source and
            dest are of the same type ((non-)collections) and a Overwrite='T'
            was passed
          - destPath must not be a child path of this resource

        This function

          - Overwrites non-collections content, if destination exists.
          - MUST NOT copy collection members.
          - MUST NOT copy locks.
          - SHOULD copy live properties, when appropriate.
            E.g. displayname should be copied, but creationdate should be
            reset if the target did not exist before.
            See http://www.webdav.org/specs/rfc4918.html#dav.properties
          - SHOULD copy dead properties.
          - raises HTTP_FORBIDDEN for read-only providers
          - raises HTTP_INTERNAL_ERROR on error

        When is_move is True,

          - Live properties should be moved too (e.g. creationdate)
          - Non-collections must be moved, not copied
          - For collections, this function behaves like in copy-mode:
            detination collection must be created and properties are copied.
            Members are NOT created.
            The source collection MUST NOT be removed.

        This method MUST be implemented by all providers that support write
        access.
        """
        raise NotImplementedError

    def handle_move(self, dest_path):
        """Handle a MOVE request natively.

        This method is called by the MOVE handler after checking for valid
        request syntax and making sure that there are no conflicting locks and
        If-headers.
        Depending on the return value, this provider can control further
        processing:

        False:
            handle_move() did not do anything. WsgiDAV will process the request
            by calling delete() and copy_move_single() for every resource,
            bottom-up.
        True:
            handle_move() has successfully performed the MOVE request.
            HTTP_NO_CONTENT/HTTP_CREATED will be reported to the DAV client.
        List of errors:
            handle_move() tried to perform the move request, but failed
            completely or partially. A list of errors is returned like
            ``[ (<ref-url>, <DAVError>), ... ]``
            These errors will be reported to the client.
        DAVError raised:
            handle_move() refuses to perform the move request. The DAVError
            will be reported to the client.

        An implementation may choose to apply other semantics and return True.
        For example moving '/by_tag/cool/myres' to '/by_tag/hot/myres' may
        simply remove the 'cool' tag from 'my_res' and add a 'hot' tag instead.
        In this case, the resource might still be available by other URLs, so
        locks and properties are not removed.

        This default implementation returns ``False``, so standard processing
        takes place.

        Implementation of this method is OPTIONAL.
        """
        return False

    def support_recursive_move(self, dest_path):
        """Return True, if move_recursive() is available (see comments there)."""
        assert self.is_collection
        raise NotImplementedError

    def move_recursive(self, dest_path):
        """Move this resource and members to destPath.

        This method is only called, when support_recursive_move() returns True.

        MOVE is frequently used by clients to rename a file without changing its
        parent collection, so it's not appropriate to reset all live properties
        that are set at resource creation. For example, the DAV:creationdate
        property value SHOULD remain the same after a MOVE.

        Preconditions (ensured by caller):

          - there must not be any conflicting locks or If-header on source
          - there must not be any conflicting locks or If-header on destination
          - destPath must not exist
          - destPath must not be a member of this resource

        This method must be prepared to handle recursive moves. This implies
        that child errors must be reported as tuple list
        [ (<ref-url>, <DAVError>), ... ].
        See http://www.webdav.org/specs/rfc4918.html#move-collections

        This function

          - moves this resource and all members to destPath.
          - MUST NOT move associated locks.
            Instead, if the source (or children thereof) have locks, then
            these locks should be removed.
          - SHOULD maintain associated live properties, when applicable
            See http://www.webdav.org/specs/rfc4918.html#dav.properties
          - MUST maintain associated dead properties
          - raises HTTP_FORBIDDEN for read-only resources
          - raises HTTP_INTERNAL_ERROR on error

        An implementation may choose to apply other semantics.
        For example copying '/by_tag/cool/myres' to '/by_tag/new/myres' may
        simply add a 'new' tag to 'my_res'.

        This method is only called, when self.support_recursive_move() returns
        True. Otherwise, the request server implements MOVE using delete/copy.

        This method MAY be implemented in order to improve performance.
        """
        raise DAVError(HTTP_FORBIDDEN)

    def resolve(self, script_name, path_info):
        """Return a _DAVResource object for the path (None, if not found).

        `path_info`: is a URL relative to this object.

        DAVCollection.resolve() provides an implementation.
        """
        raise NotImplementedError

    def finalize_headers(self, environ, response_headers):
        """Perform custom operations on the response headers.

        This gets called before the response is started.
        It enables adding additional headers or modifying the default ones.
        """
        pass


# ========================================================================
# DAVNonCollection
# ========================================================================
class DAVNonCollection(_DAVResource):
    """
    A DAVNonCollection is a _DAVResource, that has content (like a 'file' on
    a filesystem).

    A DAVNonCollecion is able to read and write file content.

    See also _DAVResource
    """

    def __init__(self, path, environ):
        _DAVResource.__init__(self, path, False, environ)

    def get_content_length(self):
        """Returns the byte length of the content.

        MUST be implemented.

        See also _DAVResource.get_content_length()
        """
        raise NotImplementedError

    def get_content_type(self):
        """Contains the Content-Type header returned by a GET without accept
        headers.

        This getcontenttype property MUST be defined on any DAV compliant
        resource that returns the Content-Type header in response to a GET.
        See http://www.webdav.org/specs/rfc4918.html#PROPERTY_getcontenttype
        """
        raise NotImplementedError

    def get_content(self):
        """Open content as a stream for reading.

        Returns a file-like object / stream containing the contents of the
        resource specified.
        The application will close() the stream.

        This method MUST be implemented by all providers.
        """
        raise NotImplementedError

    def support_ranges(self):
        """Return True, if this non-resource supports Range on GET requests.

        This default implementation returns False.
        """
        return False

    def begin_write(self, content_type=None):
        """Open content as a stream for writing.

        This method MUST be implemented by all providers that support write
        access.
        """
        raise DAVError(HTTP_FORBIDDEN)

    def end_write(self, with_errors):
        """Called when PUT has finished writing.

        This is only a notification that MAY be handled.
        """
        pass

    def resolve(self, script_name, path_info):
        """Return a _DAVResource object for the path (None, if not found).

        Since non-collection don't have members, we return None if path is not
        empty.
        """
        if path_info in ("", "/"):
            return self
        return None


# ========================================================================
# DAVCollection
# ========================================================================
class DAVCollection(_DAVResource):
    """
    A DAVCollection is a _DAVResource, that has members (like a 'folder' on
    a filesystem).

    A DAVCollecion 'knows' its members, and how to obtain them from the backend
    storage.
    There is also optional built-in support for member caching.

    See also _DAVResource
    """

    def __init__(self, path, environ):
        _DAVResource.__init__(self, path, True, environ)

        # Allow caching of members

    #        self.memberCache = {"enabled": False,
    #                            "expire": 10,  # Purge, if not used for n seconds
    #                            "maxAge": 60,  # Force purge, if older than n seconds
    #                            "created": None,
    #                            "lastUsed": None,
    #                            "members": None,
    #                            }

    #    def _cacheSet(self, members):
    #        if self.memberCache["enabled"]:
    #            if not members:
    #                # We cannot cache None, because _cacheGet() == None means 'not in cache'
    #                members = []
    #            self.memberCache["created"] = self.memberCache["lastUsed"] = datetime.now()
    #            self.memberCache["members"] = members
    #
    #    def _cacheGet(self):
    #        if not self.memberCache["enabled"]:
    #            return None
    #        now = datetime.now()
    #        if (now - self.memberCache["lastUsed"]) > self.memberCache["expire"]:
    #            return None
    #        elif (now - self.memberCache["created"]) > self.memberCache["maxAge"]:
    #            return None
    #        self.memberCache["lastUsed"] = datetime.now()
    #        return self.memberCache["members"]
    #
    #    def _cachePurge(self):
    #        self.memberCache["created"] = self.memberCache["lastUsed"] = None
    #        self.memberCache["members"] = None

    #    def getContentLanguage(self):
    #        return None

    def get_content_length(self):
        return None

    def get_content_type(self):
        return None

    def create_empty_resource(self, name):
        """Create and return an empty (length-0) resource as member of self.

        Called for LOCK requests on unmapped URLs.

        Preconditions (to be ensured by caller):

          - this must be a collection
          - <self.path + name> must not exist
          - there must be no conflicting locks

        Returns a DAVResuource.

        This method MUST be implemented by all providers that support write
        access.
        This default implementation simply raises HTTP_FORBIDDEN.
        """
        raise DAVError(HTTP_FORBIDDEN)

    def create_collection(self, name):
        """Create a new collection as member of self.

        Preconditions (to be ensured by caller):

          - this must be a collection
          - <self.path + name> must not exist
          - there must be no conflicting locks

        This method MUST be implemented by all providers that support write
        access.
        This default implementation raises HTTP_FORBIDDEN.
        """
        assert self.is_collection
        raise DAVError(HTTP_FORBIDDEN)

    def get_member(self, name):
        """Return child resource with a given name (None, if not found).

        This method COULD be overridden by a derived class, for performance
        reasons.
        This default implementation calls self.provider.get_resource_inst().
        """
        assert self.is_collection
        return self.provider.get_resource_inst(
            util.join_uri(self.path, name), self.environ
        )

    def get_member_names(self):
        """Return list of (direct) collection member names (UTF-8 byte strings).

        This method MUST be implemented.
        """
        assert self.is_collection
        raise NotImplementedError

    def support_recursive_delete(self):
        """Return True, if delete() may be called on non-empty collections
        (see comments there).

        This default implementation returns False.
        """
        return False

    def delete(self):
        """Remove this resource (possibly recursive).

        This method MUST be implemented if resource allows write access.

        See _DAVResource.delete()
        """
        raise DAVError(HTTP_FORBIDDEN)

    def copy_move_single(self, dest_path, is_move):
        """Copy or move this resource to destPath (non-recursive).

        This method MUST be implemented if resource allows write access.

        See _DAVResource.copy_move_single()
        """
        raise DAVError(HTTP_FORBIDDEN)

    def support_recursive_move(self, dest_path):
        """Return True, if move_recursive() is available (see comments there)."""
        return False

    def move_recursive(self, dest_path):
        """Move this resource and members to destPath.

        This method MAY be implemented in order to improve performance.
        """
        raise DAVError(HTTP_FORBIDDEN)

    def resolve(self, script_name, path_info):
        """Return a _DAVResource object for the path (None, if not found).

        `path_info`: is a URL relative to this object.
        """
        if path_info in ("", "/"):
            return self
        assert path_info.startswith("/")
        name, rest = util.pop_path(path_info)
        res = self.get_member(name)
        if res is None or rest in ("", "/"):
            return res
        return res.resolve(util.join_uri(script_name, name), rest)


# ========================================================================
# DAVProvider
# ========================================================================


class DAVProvider(object):
    """Abstract base class for DAV resource providers.

    There will be only one DAVProvider instance per share (not per request).
    """

    def __init__(self):
        self.mount_path = ""
        self.share_path = None
        self.lock_manager = None
        self.prop_manager = None
        self.verbose = 3

        self._count_get_resource_inst = 0
        self._count_get_resource_inst_init = 0

    #        self.caseSensitiveUrls = True

    def __repr__(self):
        return self.__class__.__name__

    def is_readonly(self):
        return False

    def set_mount_path(self, mount_path):
        """Set application root for this resource provider.

        This is the value of SCRIPT_NAME, when WsgiDAVApp is called.
        """
        assert mount_path in ("", "/") or not mount_path.endswith("/")
        self.mount_path = mount_path

    def set_share_path(self, share_path):
        """Set application location for this resource provider.

        @param share_path: a UTF-8 encoded, unquoted byte string.
        """
        # if isinstance(share_path, unicode):
        #     share_path = share_path.encode("utf8")
        assert share_path == "" or share_path.startswith("/")
        if share_path == "/":
            share_path = ""  # This allows to code 'absPath = share_path + path'
        assert share_path in ("", "/") or not share_path.endswith("/")
        self.share_path = share_path

    def set_lock_manager(self, lock_manager):
        assert not lock_manager or hasattr(
            lock_manager, "check_write_permission"
        ), "Must be compatible with wsgidav.lock_manager.LockManager"
        self.lock_manager = lock_manager

    def set_prop_manager(self, prop_manager):
        assert not prop_manager or hasattr(
            prop_manager, "copy_properties"
        ), "Must be compatible with wsgidav.prop_man.property_manager.PropertyManager"
        self.prop_manager = prop_manager

    def ref_url_to_path(self, ref_url):
        """Convert a refUrl to a path, by stripping the share prefix.

        Used to calculate the <path> from a storage key by inverting get_ref_url().
        """
        return "/" + compat.unquote(util.lstripstr(ref_url, self.share_path)).lstrip(
            "/"
        )

    def get_resource_inst(self, path, environ):
        """Return a _DAVResource object for path.

        Should be called only once per request and resource::

            res = provider.get_resource_inst(path, environ)
            if res and not res.is_collection:
                print(res.get_content_type())

        If <path> does not exist, None is returned.
        <environ> may be used by the provider to implement per-request caching.

        See _DAVResource for details.

        This method MUST be implemented.
        """
        raise NotImplementedError

    def exists(self, path, environ):
        """Return True, if path maps to an existing resource.

        This method should only be used, if no other information is queried
        for <path>. Otherwise a _DAVResource should be created first.

        This method SHOULD be overridden by a more efficient implementation.
        """
        return self.get_resource_inst(path, environ) is not None

    def is_collection(self, path, environ):
        """Return True, if path maps to an existing collection resource.

        This method should only be used, if no other information is queried
        for <path>. Otherwise a _DAVResource should be created first.
        """
        res = self.get_resource_inst(path, environ)
        return res and res.is_collection

    def custom_request_handler(self, environ, start_response, default_handler):
        """Optionally implement custom request handling.

        requestmethod = environ["REQUEST_METHOD"]
        Either

        - handle the request completely
        - do additional processing and call default_handler(environ, start_response)
        """
        return default_handler(environ, start_response)
