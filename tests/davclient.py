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
# - Added checkResponse()
#
# Modified 2015-10-20, Martin Wendt:
# - Fixed for Py3: StringIO, string-exceptions

import base64
import copy
import sys

PY2 = sys.version_info < (3, 0)

if PY2:
    import httplib as http_client
    from cStringIO import StringIO
    BytesIO = StringIO
    from urlparse import urlparse
    is_bytes = lambda s: isinstance(s, str)
    is_unicode = lambda s: isinstance(s, unicode)
    to_native = lambda s: s if is_bytes(s) else s.encode("utf8")
else:
    from http import client as http_client
    from io import StringIO, BytesIO
    from urllib.parse import urlparse
    xrange = range
    is_bytes = lambda s: isinstance(s, bytes)
    is_unicode = lambda s: isinstance(s, str)
    to_native = lambda s: s if is_unicode(s) else s.decode("utf8")

is_native = lambda s: isinstance(s, str)
to_bytes = lambda s: s if is_bytes(s) else s.encode("utf8")

try:
    from xml.etree import ElementTree
except:
    from elementtree import ElementTree

__all__ = ['DAVClient']

class AppError(Exception):
    pass

def object_to_etree(parent, obj, namespace=''):
    """This function takes in a python object, traverses it, and adds it to an existing etree object"""
    # TODO: Py3: this will probably brea, since str is used wrong:
    if type(obj) is int or type(obj) is float or type(obj) is str:
        # If object is a string, int, or float just add it
        obj = str(obj)
        if obj.startswith('{') is False:
            ElementTree.SubElement(parent, '{%s}%s' % (namespace, obj))
        else:
            ElementTree.SubElement(parent, obj)
        
    elif type(obj) is dict:
        # If the object is a dictionary we'll need to parse it and send it back recusively
        for key, value in obj.items():
            if key.startswith('{') is False:
                key_etree = ElementTree.SubElement(parent, '{%s}%s' % (namespace, key))
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
        raise TypeError('%s is an unsupported type' % type(obj))
        

class DAVClient(object):
    
    def __init__(self, url='http://localhost:8080'):
        """Initialization"""
        
        self._url = urlparse(url)
        
        self.headers = {'Host':self._url[1], 
                        'User-Agent': 'python.davclient.DAVClient/0.1'} 

        
    def _request(self, method, path='', body=None, headers=None):
        """Internal request method"""
        self.response = None
        # print("#"*20, (body and body[:50]), isinstance(body, str))
        # assert body is None or is_bytes(body)

        if headers is None:
            headers = copy.copy(self.headers)
        else:
            new_headers = copy.copy(self.headers)
            new_headers.update(headers)
            headers = new_headers

        # keep request info for later checks
        self.request = {"method": method,
                        "path": path,
                        "headers": headers,
                        }

        if self._url.scheme == 'http':
            self._connection = http_client.HTTPConnection(self._url[1])
        elif self._url.scheme == 'https':
            self._connection = http_client.HTTPSConnection(self._url[1])
        else:
            raise Exception('Unsupported scheme')
        
        self._connection.request(method, path, body, headers)
            
        self.response = self._connection.getresponse()

        self.response.body = self.response.read()
        
        # Try to parse and get an etree
        try:
            self._get_response_tree()
        except:
            pass
        
            
    def _get_response_tree(self):
        """Parse the response body into an elementree object"""
        self.response.tree = ElementTree.fromstring(self.response.body)
        return self.response.tree
        
    def _tree_to_body_str(self, tree):
        """Return tree content as body compatible native xml string."""
        # Etree won't just return a normal string, so we have to do this
        body = BytesIO()
        tree.write(body)
        body = body.getvalue()  # bytestring
        body = '<?xml version="1.0" encoding="utf-8" ?>\n%s' % to_native(body)
        return body
        
    def set_basic_auth(self, username, password):
        """Set basic authentication"""
        u_p = ('%s:%s' % (username, password)).encode("utf8")
        b64 = base64.encodestring(u_p)
        # encodestring() returns a bytestring. We want a native str on Python 3
        if not type(b64) is str:
            b64 = b64.decode("utf8")
        auth = 'Basic %s' % b64.strip()
        self._username = username
        self._password = password
        self.headers['Authorization'] = auth
        
    ## HTTP DAV methods ##
        
    def get(self, path, headers=None):
        """Simple get request"""
        self._request('GET', path, headers=headers)
        return self.response.body
        
    def head(self, path, headers=None):
        """Basic HEAD request"""
        self._request('HEAD', path, headers=headers)
        
    def put(self, path, body=None, f=None, headers=None):
        """Put resource with body"""
        if f is not None:
            body = f.read()
            
        self._request('PUT', path, body=body, headers=headers)
        
    def post(self, path, body=None, headers=None):
        """POST resource with body"""

        self._request('POST', path, body=body, headers=headers)
        
    def mkcol(self, path, headers=None):
        """Make DAV collection"""
        self._request('MKCOL', path=path, headers=headers)
        
    make_collection = mkcol
        
    def delete(self, path, headers=None):
        """Delete DAV resource"""
        self._request('DELETE', path=path, headers=headers)
        
    def copy(self, source, destination, body=None, depth='infinity', overwrite=True, headers=None):
        """Copy DAV resource"""
        # Set all proper headers
        if headers is None:
            headers = {'Destination':destination}
        else:
            headers['Destination'] = self._url.geturl() + destination
        if overwrite is False:
            headers['Overwrite'] = 'F'
        headers['Depth'] = depth
            
        self._request('COPY', source, body=body, headers=headers)
        
    def copy_collection(self, source, destination, depth='infinity', overwrite=True, headers=None):
        """Copy DAV collection.
        
        Note: support for the 'propertybehavior' request body for COPY and MOVE 
              has been removed with RFC4918
        """
        body = '<?xml version="1.0" encoding="utf-8" ?><d:propertybehavior xmlns:d="DAV:"><d:keepalive>*</d:keepalive></d:propertybehavior>'
        
        # Add proper headers
        if headers is None:
            headers = {}
        headers['Content-Type'] = 'text/xml; charset="utf-8"'
        
        self.copy(source, destination, body=body, depth=depth, overwrite=overwrite, headers=headers)
        
        
    def move(self, source, destination, body=None, depth='infinity', overwrite=True, headers=None):
        """Move DAV resource"""
        # Set all proper headers
        if headers is None:
            headers = {'Destination':destination}
        else:
            headers['Destination'] = self._url.geturl() + destination
        if overwrite is False:
            headers['Overwrite'] = 'F'
        headers['Depth'] = depth
            
        self._request('MOVE', source, body=body, headers=headers)
        
        
    def move_collection(self, source, destination, depth='infinity', overwrite=True, headers=None):
        """Move DAV collection and copy all properties.

        Note: support for the 'propertybehavior' request body for COPY and MOVE 
              has been removed with RFC4918
        """
        body = '<?xml version="1.0" encoding="utf-8" ?><d:propertybehavior xmlns:d="DAV:"><d:keepalive>*</d:keepalive></d:propertybehavior>'
        
        # Add proper headers
        if headers is None:
            headers = {}
        headers['Content-Type'] = 'text/xml; charset="utf-8"'

        self.move(source, destination, body, depth=depth, overwrite=overwrite, headers=headers)
        
        
    def propfind(self, path, properties='allprop', namespace='DAV:', depth=None, headers=None):
        """Property find. If properties arg is unspecified it defaults to 'allprop'"""
        # Build propfind xml
        root = ElementTree.Element('{DAV:}propfind')
        if is_native(properties):
            ElementTree.SubElement(root, '{DAV:}%s' % properties)
        else:
            props = ElementTree.SubElement(root, '{DAV:}prop')
            object_to_etree(props, properties, namespace=namespace)
        tree = ElementTree.ElementTree(root)
        
        body = self._tree_to_body_str(tree)
                
        # Add proper headers
        if headers is None:
            headers = {}
        if depth is not None:
            headers['Depth'] = depth
        headers['Content-Type'] = 'text/xml; charset="utf-8"'
        
        # Body encoding must be utf-8, 207 is proper response
        self._request('PROPFIND', path, body=body, headers=headers)
        
        if self.response is not None and hasattr(self.response, 'tree') is True:
            property_responses = {}
            for response in self.response.tree._children:
                property_href = response.find('{DAV:}href')
                property_stat = response.find('{DAV:}propstat')
                
                def parse_props(props):
                    property_dict = {}
                    for prop in props:
                        if prop.tag.find('{DAV:}') is not -1:
                            name = prop.tag.split('}')[-1]
                        else:
                            name = prop.tag
                        if len(prop._children) is not 0:
                            property_dict[name] = parse_props(prop._children)
                        else:
                            property_dict[name] = prop.text
                    return property_dict
                
                if property_href is not None and property_stat is not None:
                    property_dict = parse_props(property_stat.find('{DAV:}prop')._children)
                    property_responses[property_href.text] = property_dict
            return property_responses
        
    def proppatch(self, path, set_props=None, remove_props=None, namespace='DAV:', headers=None):
        """Patch properties on a DAV resource. If namespace is not specified the DAV namespace is used for all properties"""
        root = ElementTree.Element('{DAV:}propertyupdate')
        
        if set_props is not None:
            prop_set = ElementTree.SubElement(root, '{DAV:}set')
            for p in set_props:
                prop_prop = ElementTree.SubElement(prop_set, '{DAV:}prop')
                object_to_etree(prop_prop, p, namespace=namespace)                 
        if remove_props is not None:
            prop_remove = ElementTree.SubElement(root, '{DAV:}remove')
            for p in remove_props:
                prop_prop = ElementTree.SubElement(prop_remove, '{DAV:}prop')
                object_to_etree(prop_prop, p, namespace=namespace)                 
        
        tree = ElementTree.ElementTree(root)

        body = self._tree_to_body_str(tree)

        # Add proper headers
        if headers is None:
            headers = {}
        headers['Content-Type'] = 'text/xml; charset="utf-8"'
        
        self._request('PROPPATCH', path, body=body, headers=headers)
        
        
    def set_lock(self, path, owner, locktype='write', lockscope='exclusive', depth=None, headers=None):
        """Set a lock on a dav resource"""
        root = ElementTree.Element('{DAV:}lockinfo')
        object_to_etree(root, {'locktype':locktype, 'lockscope':lockscope, 'owner':{'href':owner}}, namespace='DAV:')
        tree = ElementTree.ElementTree(root)
        
        # Add proper headers
        if headers is None:
            headers = {}
        if depth is not None:
            headers['Depth'] = depth
        headers['Content-Type'] = 'text/xml; charset="utf-8"'
        headers['Timeout'] = 'Infinite, Second-4100000000'
        
        body = self._tree_to_body_str(tree)

        self._request('LOCK', path, body=body, headers=headers)
        
        locks = self.response.tree.findall('.//{DAV:}locktoken')
        lock_list = []
        for lock in locks:
            lock_list.append(lock.getchildren()[0].text.strip().strip('\n'))
        return lock_list
        

    def refresh_lock(self, path, token, headers=None):
        """Refresh lock with token"""
        
        if headers is None:
            headers = {}
        headers['If'] = '(<%s>)' % token
        headers['Timeout'] = 'Infinite, Second-4100000000'
        
        self._request('LOCK', path, body=None, headers=headers)
        
        
    def unlock(self, path, token, headers=None):
        """Unlock DAV resource with token"""
        if headers is None:
            headers = {}
        headers['Lock-Token'] = '<%s>' % token
        
        self._request('UNLOCK', path, body=None, headers=headers)


    def checkResponse(self, status=None):
        """Raise an error, if self.response doesn't match expected status.
        
        Inspired by paste.fixture
        """
        __tracebackhide__ = True
        res = self.response
        full_status = "%s %s" % (res.status, res.reason)

        # Check response Content_Length
        content_length = int(res.getheader("content-length", 0))
        if content_length and len(res.body) != content_length:
            raise AppError("Mismatch: Content_Length(%s) != len(body)(%s)" % (content_length, len(res.body)))

        # From paste.fixture:
        if status == '*':
            return
        if isinstance(status, (list, tuple)):
            if res.status not in status:
                # TODO: Py3: check usage of str:
                raise AppError(
                    "Bad response: %s (not one of %s for %s %s)\n%s"
                    % (full_status, ', '.join(map(str, status)),
                       self.request["method"], self.request["path"], res.body))
            return
        if status is None:
            if res.status >= 200 and res.status < 400:
                return
            raise AssertionError(
                "Bad response: %s (not 200 OK or 3xx redirect for %s %s)\n%s"
                % (full_status, self.request["method"], self.request["path"],
                   res.body))
        if status != res.status:
            raise AppError("Bad response: %s (not %s)" % (full_status, status))


    def checkMultiStatusResponse(self, expect_status=200):
        """"""
        if isinstance(expect_status, tuple):
            pass
        elif not isinstance(expect_status, list):
            expect_status = [ expect_status ]
        expect_status = [int(s) for s in expect_status]
            
        self.checkResponse(207)
        if not hasattr(self.response, 'tree'):
            raise AppError("Bad response: not XML")
        responses = {}
        for response in self.response.tree._children:
            href = response.find('{DAV:}href')
            pstat = response.find('{DAV:}propstat')
            if pstat:
                stat = pstat.find('{DAV:}status')
            else:
                stat = response.find('{DAV:}status')
            # 'HTTP/1.1 200 OK' -> 200
            statuscode = int(stat.text.split(" ", 2)[1])
            responses.setdefault(statuscode, []).append(href.text)
        for statuscode, hrefs in responses.items():
            if not statuscode in expect_status:
                raise AppError("Invalid multistatus %s for %s (expected %s)\n%s" % (statuscode, hrefs, expect_status, responses))
