#   Copyright (c) 2006-2007 Open Source Applications Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# Modified 2010-11-02, Martin Wendt:
# Taken from http://chandlerproject.org/Projects/Davclient
# - Fixed set_lock, proppatch
# - Added (tag, value) syntax to object_to_etree
# - Added check_response()
#
# Modified 2015-10-20, Martin Wendt:
# - Fix for Py3: StringIO, string-exceptions, bytestring bodies
#
# Modified 2017-02-25, Martin Wendt:
# - Use requests instead of http.client / httplib

import copy
from base64 import encodebytes as base64_encodebytes
from io import BytesIO
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests

__all__ = ["DAVClient"]


def is_basestring(s):
    """Return True for any string type (for str/unicode on Py2 and bytes/str on Py3)."""
    return isinstance(s, (str, bytes))


def is_bytes(s):
    """Return True for bytestrings (for str on Py2 and bytes on Py3)."""
    return isinstance(s, bytes)


def is_str(s):
    """Return True for native strings (for str on Py2 and Py3)."""
    return isinstance(s, str)


def to_bytes(s, encoding="utf8"):
    """Convert a text string (unicode) to bytestring (str on Py2 and bytes on Py3)."""
    if type(s) is not bytes:
        s = bytes(s, encoding)
    return s


def to_str(s, encoding="utf8"):
    """Convert data to native str type (bytestring on Py2 and unicode on Py3)."""
    if type(s) is bytes:
        s = str(s, encoding)
    elif type(s) is not str:
        s = str(s)
    return s


class AppError(Exception):
    pass


def object_to_etree(parent, obj, namespace=""):
    """Takes in a python object, traverses it, and adds it to an existing etree object."""
    # TODO: Py3: this will probably brea, since str is used wrong:
    if type(obj) is int or type(obj) is float or type(obj) is str:
        # If object is a string, int, or float just add it
        obj = str(obj)
        if obj.startswith("{") is False:
            ElementTree.SubElement(parent, f"{{{namespace}}}{obj}")
        else:
            ElementTree.SubElement(parent, obj)

    elif type(obj) is dict:
        # If the object is a dictionary we"ll need to parse it and send it back
        # recursively
        for key, value in obj.items():
            if key.startswith("{") is False:
                key_etree = ElementTree.SubElement(parent, f"{{{namespace}}}{key}")
                object_to_etree(key_etree, value, namespace=namespace)
            else:
                key_etree = ElementTree.SubElement(parent, key)
                object_to_etree(key_etree, value, namespace=namespace)

    elif type(obj) is list:
        # If the object is a list parse it and send it back recursively
        for item in obj:
            object_to_etree(parent, item, namespace=namespace)

    elif type(obj) is tuple and len(obj) == 2:
        # If the object is a a tuple, assume (tag_name, value)
        # TODO: Py3: check usage of str
        ElementTree.SubElement(parent, obj[0]).text = str(obj[1])

    else:
        # If it's none of previous types then raise
        raise TypeError("%s is an unsupported type" % type(obj))


class DAVClient:
    def __init__(self, url="http://localhost:8080", logger=None):
        """Initialization"""

        self._url = urlparse(url)
        self.logger = logger
        self.logger_prefix = "DAVClient" if logger is True else str(logger)

        self.headers = {
            "Host": self._url[1],
            "User-Agent": "python.davclient.DAVClient/0.1",
        }
        self.response = None
        self.clear_basic_auth()

    def log(self, msg):
        if self.logger:
            print(f"{self.logger_prefix}: {msg}")

    def _request(self, method, path="", body=None, headers=None):
        """Internal request method"""
        self.response = None

        assert body is None or is_bytes(body)
        self.log(f"{method} - {path}")

        if headers is None:
            headers = copy.copy(self.headers)
        else:
            new_headers = copy.copy(self.headers)
            new_headers.update(headers)
            headers = new_headers

        # keep request info for later checks
        self.request = {"method": method, "path": path, "headers": headers}
        url = self._url.geturl()
        url = urljoin(url, path)
        res = requests.request(method, url, data=body, headers=headers)
        self.response = res
        assert is_bytes(self.response.content)
        # Try to parse and get an etree
        try:
            self._get_response_tree()
        except Exception as e:
            self.log(f"Could not parse response XML: {e}\n{res.text}")

    def _get_response_tree(self):
        """Parse the response body into an elementree object"""
        self.response.tree = None
        self.response.tree = ElementTree.fromstring(self.response.content)
        return self.response.tree

    def _tree_to_binary_body(self, tree):
        """Return tree content as xml bytestring."""
        # Etree won't just return a normal string, so we have to do this
        body = BytesIO()
        tree.write(body)
        body = body.getvalue()  # bytestring
        body = b'<?xml version="1.0" encoding="utf-8" ?>\n' + body
        assert is_bytes(body)
        return body

    def set_basic_auth(self, user_name, password):
        """Set basic authentication"""
        u_p = (f"{user_name}:{password}").encode()
        b64 = base64_encodebytes(u_p)
        # encodestring() returns a bytestring. We want a native str on Python 3
        if type(b64) is not str:
            b64 = b64.decode("utf8")
        auth = "Basic %s" % b64.strip()
        self._username = user_name
        self._password = password
        self.headers["Authorization"] = auth

    def clear_basic_auth(self):
        """Reset basic authentication"""
        self._username = None
        self._password = None
        self.headers.pop("Authorization", None)

    # HTTP DAV methods

    def get(self, path, headers=None):
        """Simple get request"""
        self._request("GET", path, headers=headers)
        return self.response.content

    def head(self, path, headers=None):
        """Basic HEAD request"""
        self._request("HEAD", path, headers=headers)

    def put(self, path, body=None, f=None, headers=None):
        """Put resource with body"""
        assert body is None or is_bytes(body)
        if f is not None:
            body = f.read()

        self._request("PUT", path, body=body, headers=headers)

    def post(self, path, body=None, headers=None):
        """POST resource with body"""
        assert body is None or is_bytes(body)
        self._request("POST", path, body=body, headers=headers)

    def mkcol(self, path, headers=None):
        """Make DAV collection"""
        self._request("MKCOL", path=path, headers=headers)

    make_collection = mkcol

    def delete(self, path, headers=None):
        """Delete DAV resource"""
        self._request("DELETE", path=path, headers=headers)

    def copy(
        self,
        source,
        destination,
        body=None,
        depth="infinity",
        overwrite=True,
        headers=None,
    ):
        """Copy DAV resource"""
        # Set all proper headers
        assert body is None or is_bytes(body)
        if headers is None:
            headers = {"Destination": destination}
        else:
            headers["Destination"] = self._url.geturl() + destination
        if overwrite is False:
            headers["Overwrite"] = "F"
        headers["Depth"] = depth

        self._request("COPY", source, body=body, headers=headers)

    def copy_collection(
        self, source, destination, depth="infinity", overwrite=True, headers=None
    ):
        """Copy DAV collection.

        Note: support for the "propertybehavior" request body for COPY and MOVE
              has been removed with RFC4918
        """
        body = (
            b'<?xml version="1.0" encoding="utf-8" ?>'
            b'<d:propertybehavior xmlns:d="DAV:">'
            b"<d:keepalive>*</d:keepalive></d:propertybehavior>"
        )

        # Add proper headers
        if headers is None:
            headers = {}
        headers["Content-Type"] = "application/xml; charset=utf-8"

        self.copy(
            source,
            destination,
            body=body,
            depth=depth,
            overwrite=overwrite,
            headers=headers,
        )

    def move(
        self,
        source,
        destination,
        body=None,
        depth="infinity",
        overwrite=True,
        headers=None,
    ):
        """Move DAV resource"""
        assert body is None or is_bytes(body)
        # Set all proper headers
        if headers is None:
            headers = {"Destination": destination}
        else:
            headers["Destination"] = self._url.geturl() + destination
        if overwrite is False:
            headers["Overwrite"] = "F"
        headers["Depth"] = depth

        self._request("MOVE", source, body=body, headers=headers)

    def move_collection(
        self, source, destination, depth="infinity", overwrite=True, headers=None
    ):
        """Move DAV collection and copy all properties.

        Note: support for the "propertybehavior" request body for COPY and MOVE
              has been removed with RFC4918
        """
        body = (
            b'<?xml version="1.0" encoding="utf-8" ?>'
            b'<d:propertybehavior xmlns:d="DAV:">'
            b"<d:keepalive>*</d:keepalive></d:propertybehavior>"
        )

        # Add proper headers
        if headers is None:
            headers = {}
        headers["Content-Type"] = "application/xml; charset=utf-8"

        self.move(
            source, destination, body, depth=depth, overwrite=overwrite, headers=headers
        )

    def propfind(
        self, path, properties="allprop", namespace="DAV:", depth=None, headers=None
    ):
        """Property find. If properties arg is unspecified it defaults to 'allprop'."""
        # Build propfind xml
        root = ElementTree.Element("{DAV:}propfind")
        if is_str(properties):
            ElementTree.SubElement(root, "{DAV:}%s" % properties)
        else:
            props = ElementTree.SubElement(root, "{DAV:}prop")
            object_to_etree(props, properties, namespace=namespace)
        tree = ElementTree.ElementTree(root)

        body = self._tree_to_binary_body(tree)

        # Add proper headers
        if headers is None:
            headers = {}
        if depth is not None:
            headers["Depth"] = depth
        headers["Content-Type"] = "application/xml; charset=utf-8"

        # Body encoding must be utf-8, 207 is proper response
        self._request("PROPFIND", path, body=body, headers=headers)

        if self.response is not None and hasattr(self.response, "tree") is True:
            property_responses = {}
            for response in self.response.tree:
                property_href = response.find("{DAV:}href")
                property_stat = response.find("{DAV:}propstat")

                def parse_props(props):
                    _property_dict = {}
                    for prop in props:
                        if prop.tag.find("{DAV:}") != -1:
                            name = prop.tag.split("}")[-1]
                        else:
                            name = prop.tag
                        if len(list(prop)):
                            _property_dict[name] = parse_props(prop)
                        else:
                            _property_dict[name] = prop.text
                    return _property_dict

                if property_href is not None and property_stat is not None:
                    property_dict = parse_props(property_stat.find("{DAV:}prop"))
                    property_responses[property_href.text] = property_dict
            return property_responses

    def proppatch(
        self, path, set_props=None, remove_props=None, namespace="DAV:", headers=None
    ):
        """Patch properties on a DAV resource.

        If namespace is not specified, the DAV namespace is used for all properties.
        """
        root = ElementTree.Element("{DAV:}propertyupdate")

        if set_props is not None:
            prop_set = ElementTree.SubElement(root, "{DAV:}set")
            for p in set_props:
                prop_prop = ElementTree.SubElement(prop_set, "{DAV:}prop")
                object_to_etree(prop_prop, p, namespace=namespace)
        if remove_props is not None:
            prop_remove = ElementTree.SubElement(root, "{DAV:}remove")
            for p in remove_props:
                prop_prop = ElementTree.SubElement(prop_remove, "{DAV:}prop")
                object_to_etree(prop_prop, p, namespace=namespace)

        tree = ElementTree.ElementTree(root)

        body = self._tree_to_binary_body(tree)

        # Add proper headers
        if headers is None:
            headers = {}
        headers["Content-Type"] = "application/xml; charset=utf-8"

        self._request("PROPPATCH", path, body=body, headers=headers)

    def set_lock(
        self,
        path,
        owner,
        lock_type="write",
        lock_scope="exclusive",
        depth=None,
        headers=None,
    ):
        """Set a lock on a dav resource"""
        root = ElementTree.Element("{DAV:}lockinfo")
        object_to_etree(
            root,
            {"locktype": lock_type, "lockscope": lock_scope, "owner": {"href": owner}},
            namespace="DAV:",
        )
        tree = ElementTree.ElementTree(root)

        # Add proper headers
        if headers is None:
            headers = {}
        if depth is not None:
            headers["Depth"] = depth
        headers["Content-Type"] = "application/xml; charset=utf-8"
        headers["Timeout"] = "Infinite, Second-4100000000"

        body = self._tree_to_binary_body(tree)

        self._request("LOCK", path, body=body, headers=headers)

        locks = self.response.tree.findall(".//{DAV:}locktoken")
        lock_list = []
        for lock in locks:
            lock_list.append(lock[0].text.strip().strip("\n"))
            # lock_list.append(lock.getchildren()[0].text.strip().strip("\n"))
        return lock_list

    def refresh_lock(self, path, token, headers=None):
        """Refresh lock with token"""

        if headers is None:
            headers = {}
        headers["If"] = "(<%s>)" % token
        headers["Timeout"] = "Infinite, Second-4100000000"

        self._request("LOCK", path, body=None, headers=headers)

    def unlock(self, path, token, headers=None):
        """Unlock DAV resource with token"""
        if headers is None:
            headers = {}
        headers["Lock-Token"] = "<%s>" % token

        self._request("UNLOCK", path, body=None, headers=headers)

    def check_response(self, status=None):
        """Raise an error, if self.response doesn"t match expected status.

        Inspired by paste.fixture
        """
        __tracebackhide__ = True  # pylint: disable=unused-variable
        res = self.response
        full_status = f"{res.status_code} {res.reason}"

        # Check response Content_Length
        content_length = int(res.headers.get("content-length", 0))
        if content_length and len(res.content) != content_length:
            raise AppError(
                "Mismatch: Content_Length(%s) != len(content)(%s)"
                % (content_length, len(res.content))
            )

        # From paste.fixture:
        if status == "*":
            return
        if isinstance(status, (list, tuple)):
            if res.status_code not in status:
                # TODO: Py3: check usage of str:
                raise AppError(
                    "Bad response: {} (not one of {} for {} {})\n{}".format(
                        full_status,
                        ", ".join(map(str, status)),
                        self.request["method"],
                        self.request["path"],
                        res.content,
                    )
                )
            return
        if status is None:
            if res.status_code >= 200 and res.status_code < 400:
                return
            raise AssertionError(
                "Bad response: {} (not 200 OK or 3xx redirect for {} {})\n{}".format(
                    full_status,
                    self.request["method"],
                    self.request["path"],
                    res.content,
                )
            )
        if status != res.status_code:
            raise AppError(f"Bad response: {full_status} (not {status})")

    def check_multi_status_response(self, expect_status=200):
        """ """
        if isinstance(expect_status, tuple):
            pass
        elif not isinstance(expect_status, list):
            expect_status = [expect_status]
        expect_status = [int(s) for s in expect_status]

        self.check_response(207)
        if not hasattr(self.response, "tree"):
            raise AppError("Bad response: not XML")
        responses = {}
        for response in self.response.tree:
            href = response.find("{DAV:}href")
            pstat = response.find("{DAV:}propstat")
            if pstat is not None:
                stat = pstat.find("{DAV:}status")
            else:
                stat = response.find("{DAV:}status")
            # "HTTP/1.1 200 OK" -> 200
            statuscode = int(stat.text.split(" ", 2)[1])
            responses.setdefault(statuscode, []).append(href.text)
        for statuscode, hrefs in responses.items():
            if statuscode not in expect_status:
                raise AppError(
                    f"Invalid multistatus {statuscode} for {hrefs} (expected {expect_status})\n{responses}"
                )
