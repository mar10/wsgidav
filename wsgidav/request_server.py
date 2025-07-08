# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI application that handles one single WebDAV request.
"""

from urllib.parse import unquote, urlparse

from wsgidav import util, xml_tools
from wsgidav.dav_error import (
    HTTP_BAD_GATEWAY,
    HTTP_BAD_REQUEST,
    HTTP_CONFLICT,
    HTTP_CREATED,
    HTTP_FAILED_DEPENDENCY,
    HTTP_FORBIDDEN,
    HTTP_INTERNAL_ERROR,
    HTTP_MEDIATYPE_NOT_SUPPORTED,
    HTTP_METHOD_NOT_ALLOWED,
    HTTP_NO_CONTENT,
    HTTP_NOT_FOUND,
    HTTP_NOT_IMPLEMENTED,
    HTTP_OK,
    HTTP_PRECONDITION_FAILED,
    HTTP_RANGE_NOT_SATISFIABLE,
    DAVError,
    PRECONDITION_CODE_LockTokenMismatch,
    PRECONDITION_CODE_PropfindFiniteDepth,
    as_DAVError,
    get_http_status_string,
)
from wsgidav.util import checked_etag, etree

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)

DEFAULT_BLOCK_SIZE = 8192


# ========================================================================
# RequestServer
# ========================================================================
class RequestServer:
    def __init__(self, dav_provider):
        self._davProvider = dav_provider
        self.allow_propfind_infinite = True
        self._verbose = 3
        self.block_size = DEFAULT_BLOCK_SIZE
        # _logger.debug("RequestServer: __init__")

        self._possible_methods = ["OPTIONS", "HEAD", "GET", "PROPFIND"]
        # if self._davProvider.prop_manager is not None:
        #     self._possible_methods.extend( [ "PROPFIND" ] )
        if not self._davProvider.is_readonly():
            self._possible_methods.extend(
                ["PUT", "DELETE", "COPY", "MOVE", "MKCOL", "PROPPATCH", "POST"]
            )
            # if self._davProvider.prop_manager is not None:
            #     self._possible_methods.extend( [ "PROPPATCH" ] )
            if self._davProvider.lock_manager is not None:
                self._possible_methods.extend(["LOCK", "UNLOCK"])

    # def __del__(self):
    #     # _logger.debug("RequestServer: __del__")
    #     pass

    def __call__(self, environ, start_response):
        assert "wsgidav.verbose" in environ
        provider = self._davProvider
        # TODO: allow anonymous somehow: this should run, even if http_authenticator middleware
        # is not installed
        #        assert "wsgidav.auth.user_name" in environ
        if "wsgidav.auth.user_name" not in environ:
            _logger.warning("Missing 'wsgidav.auth.user_name' in environ")

        environ["wsgidav.user_name"] = environ.get(
            "wsgidav.auth.user_name", "anonymous"
        )
        requestmethod = environ["REQUEST_METHOD"]

        self.block_size = environ["wsgidav.config"].get(
            "block_size", DEFAULT_BLOCK_SIZE
        )

        # Convert 'infinity' and 'T'/'F' to a common case
        if environ.get("HTTP_DEPTH") is not None:
            environ["HTTP_DEPTH"] = environ["HTTP_DEPTH"].lower()
        if environ.get("HTTP_OVERWRITE") is not None:
            environ["HTTP_OVERWRITE"] = environ["HTTP_OVERWRITE"].upper()

        if "HTTP_EXPECT" in environ:
            pass

        # Dispatch HTTP request methods to 'do_METHOD()' handlers
        method = None
        if requestmethod in self._possible_methods:
            method_name = f"do_{requestmethod}"
            method = getattr(self, method_name, None)
        if not method:
            _logger.error(f"Invalid HTTP method {requestmethod!r}")
            self._fail(HTTP_METHOD_NOT_ALLOWED)

        if environ.get("wsgidav.debug_break"):
            pass  # Set a break point here

        if environ.get("wsgidav.debug_profile"):
            from cProfile import Profile

            profile = Profile()
            res = profile.runcall(
                provider.custom_request_handler, environ, start_response, method
            )
            # sort: 0:"calls",1:"time", 2: "cumulative"
            profile.print_stats(sort=2)
            yield from res
            if hasattr(res, "close"):
                res.close()
            return

        # Run requesthandler (provider may override, #55)
        # _logger.warning("#1...")
        app_iter = provider.custom_request_handler(environ, start_response, method)
        # _logger.warning("#1... 2")
        try:
            # _logger.warning("#1... 3")
            yield from app_iter
            # _logger.warning("#1... 5")
        # except Exception:
        #     _logger.warning("#1... 6")
        #     _logger.exception("")
        #     status = "500 Oops"
        #     response_headers = [("content-type", "text/plain")]
        #     start_response(status, response_headers, sys.exc_info())
        #     return ["error body goes here"]
        finally:
            # _logger.warning("#1... 7")
            if hasattr(app_iter, "close"):
                # _logger.warning("#1... 8")
                app_iter.close()
        return

    def _fail(self, value, context_info=None, src_exception=None, err_condition=None):
        """Wrapper to raise (and log) DAVError."""
        util.fail(
            value,
            context_info,
            src_exception=src_exception,
            err_condition=err_condition,
        )

    def _send_response(
        self, environ, start_response, root_res, success_code, error_list
    ):
        """Send WSGI response (single or multistatus).

        - If error_list is None or [], then <success_code> is send as response.
        - If error_list contains a single error with a URL that matches root_res,
          then this error is returned.
        - If error_list contains more than one error, then '207 Multi-Status' is
          returned.
        """
        assert success_code in (HTTP_CREATED, HTTP_NO_CONTENT, HTTP_OK)
        if not error_list:
            # Status OK
            return util.send_status_response(environ, start_response, success_code)
        if len(error_list) == 1 and error_list[0][0] == root_res.get_href():
            # Only one error that occurred on the root resource
            return util.send_status_response(environ, start_response, error_list[0][1])

        # Multiple errors, or error on one single child
        multistatusEL = xml_tools.make_multistatus_el()

        for refurl, e in error_list:
            # assert refurl.startswith("http:")
            assert refurl.startswith("/")
            assert isinstance(e, DAVError)
            responseEL = etree.SubElement(multistatusEL, "{DAV:}response")
            etree.SubElement(responseEL, "{DAV:}href").text = refurl
            etree.SubElement(
                responseEL, "{DAV:}status"
            ).text = f"HTTP/1.1 {get_http_status_string(e)}"

        return util.send_multi_status_response(environ, start_response, multistatusEL)

    def _check_write_permission(self, res, depth, environ):
        """Raise DAVError(HTTP_LOCKED), if res is locked.

        If depth=='infinity', we also raise when child resources are locked.
        """
        lock_man = self._davProvider.lock_manager
        if lock_man is None or res is None:
            return True

        ref_url = res.get_ref_url()

        if "wsgidav.conditions.if" not in environ:
            util.parse_if_header_dict(environ)

        # raise HTTP_LOCKED if conflict exists
        lock_man.check_write_permission(
            url=ref_url,
            depth=depth,
            token_list=environ["wsgidav.ifLockTokenList"],
            principal=environ["wsgidav.user_name"],
        )

    def _evaluate_if_headers(self, res, environ):
        """Apply HTTP headers on <path>, raising DAVError if conditions fail.

        Add environ['wsgidav.conditions.if'] and environ['wsgidav.ifLockTokenList'].
        Handle these headers:

          - If-Match, If-Modified-Since, If-None-Match, If-Unmodified-Since:
            Raising HTTP_PRECONDITION_FAILED or HTTP_NOT_MODIFIED
          - If:
            Raising HTTP_PRECONDITION_FAILED

        @see http://www.webdav.org/specs/rfc4918.html#HEADER_If
        @see util.evaluate_http_conditionals
        """
        # Add parsed If header to environ
        if "wsgidav.conditions.if" not in environ:
            util.parse_if_header_dict(environ)

        # Bail out, if res does not exist
        if res is None:
            return

        if_dict = environ["wsgidav.conditions.if"]

        # Raise HTTP_PRECONDITION_FAILED or HTTP_NOT_MODIFIED, if standard
        # HTTP condition fails
        last_modified = -1  # nonvalid modified time
        if res.get_last_modified() is not None:
            last_modified = int(res.get_last_modified())

        etag = checked_etag(res.get_etag(), allow_none=True)
        if etag is None:
            etag = "[]"  # Non-valid entity tag

        if (
            "HTTP_IF_MODIFIED_SINCE" in environ
            or "HTTP_IF_UNMODIFIED_SINCE" in environ
            or "HTTP_IF_MATCH" in environ
            or "HTTP_IF_NONE_MATCH" in environ
        ):
            util.evaluate_http_conditionals(res, last_modified, etag, environ)

        if "HTTP_IF" not in environ:
            return

        # Raise HTTP_PRECONDITION_FAILED, if DAV 'If' condition fails
        # TODO: handle empty locked resources
        # TODO: handle unmapped locked resources
        #            isnewfile = not provider.exists(mappedpath)

        ref_url = res.get_ref_url()
        lock_man = self._davProvider.lock_manager
        locktoken_list = []
        if lock_man:
            lockList = lock_man.get_indirect_url_lock_list(
                ref_url, principal=environ["wsgidav.user_name"]
            )
            for lock in lockList:
                locktoken_list.append(lock["token"])

        if not util.test_if_header_dict(res, if_dict, ref_url, locktoken_list, etag):
            self._fail(HTTP_PRECONDITION_FAILED, "'If' header condition failed.")

        return

    def do_PROPFIND(self, environ, start_response):
        """
        TODO: does not yet support If and If HTTP Conditions
        @see http://www.webdav.org/specs/rfc4918.html#METHOD_PROPFIND
        """
        path = environ["PATH_INFO"]
        res = self._davProvider.get_resource_inst(path, environ)

        # RFC: By default, the PROPFIND method without a Depth header MUST act
        # as if a "Depth: infinity" header was included.
        environ.setdefault("HTTP_DEPTH", "infinity")
        if environ["HTTP_DEPTH"] not in ("0", "1", "infinity"):
            self._fail(
                HTTP_BAD_REQUEST,
                "Invalid Depth header: {!r}.".format(environ["HTTP_DEPTH"]),
            )

        if environ["HTTP_DEPTH"] == "infinity" and not self.allow_propfind_infinite:
            self._fail(
                HTTP_FORBIDDEN,
                "PROPFIND 'infinite' was disabled for security reasons.",
                err_condition=PRECONDITION_CODE_PropfindFiniteDepth,
            )

        if res is None:
            self._fail(HTTP_NOT_FOUND, path)

        if environ.get("wsgidav.debug_break"):
            pass  # break point

        self._evaluate_if_headers(res, environ)

        # Parse PROPFIND request
        requestEL = util.parse_xml_body(environ, allow_empty=True)
        if requestEL is None:
            # An empty PROPFIND request body MUST be treated as a request for
            # the names and values of all properties.
            requestEL = etree.XML(
                "<D:propfind xmlns:D='DAV:'><D:allprop/></D:propfind>"
            )

        if requestEL.tag != "{DAV:}propfind":
            self._fail(HTTP_BAD_REQUEST)

        propNameList = []
        propFindMode = None
        for pfnode in requestEL:
            if pfnode.tag == "{DAV:}allprop":
                if propFindMode:
                    # RFC: allprop and name are mutually exclusive
                    self._fail(HTTP_BAD_REQUEST)
                propFindMode = "allprop"
            # TODO: implement <include> option
            #            elif pfnode.tag == "{DAV:}include":
            #                if not propFindMode in (None, "allprop"):
            #                    self._fail(HTTP_BAD_REQUEST,
            #                        "<include> element is only valid with 'allprop'.")
            #                for pfpnode in pfnode:
            #                    propNameList.append(pfpnode.tag)
            elif pfnode.tag == "{DAV:}name":
                if propFindMode:  # RFC: allprop and name are mutually exclusive
                    self._fail(HTTP_BAD_REQUEST)
                propFindMode = "name"
            elif pfnode.tag == "{DAV:}prop":
                # RFC: allprop and name are mutually exclusive
                if propFindMode not in (None, "named"):
                    self._fail(HTTP_BAD_REQUEST)
                propFindMode = "named"
                for pfpnode in pfnode:
                    propNameList.append(pfpnode.tag)

        # --- Build list of resource URIs

        reslist = res.get_descendants(depth=environ["HTTP_DEPTH"], add_self=True)
        #        if environ["wsgidav.verbose"] >= 3:
        #            pprint(reslist, indent=4)

        multistatusEL = xml_tools.make_multistatus_el()
        responsedescription = []

        for child in reslist:
            if propFindMode == "allprop":
                propList = child.get_properties("allprop")
            elif propFindMode == "name":
                propList = child.get_properties("name")
            else:
                propList = child.get_properties("named", name_list=propNameList)

            href = child.get_href()
            util.add_property_response(multistatusEL, href, propList)

        if responsedescription:
            etree.SubElement(
                multistatusEL, "{DAV:}responsedescription"
            ).text = "\n".join(responsedescription)

        return util.send_multi_status_response(environ, start_response, multistatusEL)

    def do_PROPPATCH(self, environ, start_response):
        """Handle PROPPATCH request to set or remove a property.

        @see http://www.webdav.org/specs/rfc4918.html#METHOD_PROPPATCH
        """
        path = environ["PATH_INFO"]
        res = self._davProvider.get_resource_inst(path, environ)

        # Only accept Depth: 0 (but assume this, if omitted)
        environ.setdefault("HTTP_DEPTH", "0")
        if environ["HTTP_DEPTH"] != "0":
            self._fail(HTTP_BAD_REQUEST, "Depth must be '0'.")

        if res is None:
            self._fail(HTTP_NOT_FOUND, path)

        self._evaluate_if_headers(res, environ)
        self._check_write_permission(res, "0", environ)

        # Parse request
        requestEL = util.parse_xml_body(environ)

        if requestEL.tag != "{DAV:}propertyupdate":
            self._fail(HTTP_BAD_REQUEST)

        # Create a list of update request tuples: (name, value)
        propupdatelist = []

        for ppnode in requestEL:
            propupdatemethod = None
            if ppnode.tag == "{DAV:}remove":
                propupdatemethod = "remove"
            elif ppnode.tag == "{DAV:}set":
                propupdatemethod = "set"
            else:
                self._fail(
                    HTTP_BAD_REQUEST, "Unknown tag (expected 'set' or 'remove')."
                )

            for propnode in ppnode:
                if propnode.tag != "{DAV:}prop":
                    self._fail(HTTP_BAD_REQUEST, "Unknown tag (expected 'prop').")

                for propertynode in propnode:
                    propvalue = None
                    if propupdatemethod == "remove":
                        propvalue = None  # Mark as 'remove'
                        if len(propertynode) > 0:
                            # 14.23: All the XML elements in a 'prop' XML
                            # element inside of a 'remove' XML element MUST be
                            # empty
                            self._fail(
                                HTTP_BAD_REQUEST,
                                "prop element must be empty for 'remove'.",
                            )
                    else:
                        propvalue = propertynode

                    propupdatelist.append((propertynode.tag, propvalue))

        # Apply updates in SIMULATION MODE and create a result list (name,
        # result)
        successflag = True
        writeresultlist = []

        for name, propvalue in propupdatelist:
            try:
                res.set_property_value(name, propvalue, dry_run=True)
            except Exception as e:
                writeresult = as_DAVError(e)
            else:
                writeresult = "200 OK"
            writeresultlist.append((name, writeresult))
            successflag = successflag and writeresult == "200 OK"

        # Generate response list of 2-tuples (name, value)
        # <value> is None on success, or an instance of DAVError
        propResponseList = []
        responsedescription = []

        if not successflag:
            # If dry run failed: convert all OK to FAILED_DEPENDENCY.
            for name, result in writeresultlist:
                if result == "200 OK":
                    result = DAVError(HTTP_FAILED_DEPENDENCY)
                elif isinstance(result, DAVError):
                    responsedescription.append(result.get_user_info())
                propResponseList.append((name, result))

        else:
            # Dry-run succeeded: set properties again, this time in 'real' mode
            # In theory, there should be no exceptions thrown here, but this is
            # real live...
            for name, propvalue in propupdatelist:
                try:
                    res.set_property_value(name, propvalue, dry_run=False)
                    # Set value to None, so the response xml contains empty tags
                    propResponseList.append((name, None))
                except Exception as e:
                    e = as_DAVError(e)
                    propResponseList.append((name, e))
                    responsedescription.append(e.get_user_info())

        # Generate response XML
        multistatusEL = xml_tools.make_multistatus_el()
        href = res.get_href()
        util.add_property_response(multistatusEL, href, propResponseList)
        if responsedescription:
            etree.SubElement(
                multistatusEL, "{DAV:}responsedescription"
            ).text = "\n".join(responsedescription)

        # Send response
        return util.send_multi_status_response(environ, start_response, multistatusEL)

    def do_MKCOL(self, environ, start_response):
        """Handle MKCOL request to create a new collection.

        @see http://www.webdav.org/specs/rfc4918.html#METHOD_MKCOL
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        #        res = provider.get_resource_inst(path, environ)

        # Do not understand ANY request body entities
        if util.get_content_length(environ) != 0:
            self._fail(
                HTTP_MEDIATYPE_NOT_SUPPORTED,
                "The server does not handle any body content.",
            )

        # Only accept Depth: 0 (but assume this, if omitted)
        if environ.setdefault("HTTP_DEPTH", "0") != "0":
            self._fail(HTTP_BAD_REQUEST, "Depth must be '0'.")

        if provider.exists(path, environ):
            self._fail(
                HTTP_METHOD_NOT_ALLOWED,
                "MKCOL can only be executed on an unmapped URL.",
            )

        parentRes = provider.get_resource_inst(util.get_uri_parent(path), environ)
        if not parentRes or not parentRes.is_collection:
            self._fail(HTTP_CONFLICT, "Parent must be an existing collection.")

        # TODO: should we check If headers here?
        #        self._evaluate_if_headers(res, environ)
        # Check for write permissions on the PARENT
        self._check_write_permission(parentRes, "0", environ)

        parentRes.create_collection(util.get_uri_name(path))

        return util.send_status_response(environ, start_response, HTTP_CREATED)

    def do_POST(self, environ, start_response):
        """
        @see http://www.webdav.org/specs/rfc4918.html#METHOD_POST
        @see http://stackoverflow.com/a/22606899/19166
        """
        self._fail(HTTP_METHOD_NOT_ALLOWED)

    def do_DELETE(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_DELETE
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.get_resource_inst(path, environ)

        # --- Check request preconditions -------------------------------------

        if util.get_content_length(environ) != 0:
            self._fail(
                HTTP_MEDIATYPE_NOT_SUPPORTED,
                "The server does not handle any body content.",
            )
        if res is None:
            self._fail(HTTP_NOT_FOUND, path)

        if res.is_collection:
            # Delete over collection
            # "The DELETE method on a collection MUST act as if a
            # 'Depth: infinity' header was used on it. A client MUST NOT submit
            # a Depth header with a DELETE on a collection with any value but
            # infinity."
            if environ.setdefault("HTTP_DEPTH", "infinity") != "infinity":
                self._fail(
                    HTTP_BAD_REQUEST,
                    "Only Depth: infinity is supported for collections.",
                )
        else:
            if environ.setdefault("HTTP_DEPTH", "0") not in ("0", "infinity"):
                self._fail(
                    HTTP_BAD_REQUEST,
                    "Only Depth: 0 or infinity are supported for non-collections.",
                )

        self._evaluate_if_headers(res, environ)
        # We need write access on the parent collection. Also we check for
        # locked children
        parentRes = provider.get_resource_inst(util.get_uri_parent(path), environ)
        if parentRes:
            #            self._check_write_permission(parentRes, environ["HTTP_DEPTH"], environ)
            self._check_write_permission(parentRes, "0", environ)
        else:
            #            self._check_write_permission(res, environ["HTTP_DEPTH"], environ)
            self._check_write_permission(res, "0", environ)

        # --- Let provider handle the request natively ------------------------

        # Errors in deletion; [ (<ref-url>, <DAVError>), ... ]
        error_list = []

        try:
            handled = res.handle_delete()
            assert handled in (True, False) or type(handled) is list
            if type(handled) is list:
                error_list = handled
                handled = True
        except Exception as e:
            error_list = [(res.get_href(), as_DAVError(e))]
            handled = True
        if handled:
            return self._send_response(
                environ, start_response, res, HTTP_NO_CONTENT, error_list
            )

        # --- Let provider implement own recursion ----------------------------

        # Get a list of all resources (parents after children, so we can remove
        # them in that order)
        reverse_child_ist = res.get_descendants(
            depth_first=True, depth=environ["HTTP_DEPTH"], add_self=True
        )

        if res.is_collection and res.support_recursive_delete():
            has_conflicts = False
            for child_res in reverse_child_ist:
                try:
                    self._evaluate_if_headers(child_res, environ)
                    self._check_write_permission(child_res, "0", environ)
                except Exception:
                    has_conflicts = True
                    break

            if not has_conflicts:
                try:
                    error_list = res.delete()
                except Exception as e:
                    error_list = [(res.get_href(), as_DAVError(e))]
                return self._send_response(
                    environ, start_response, res, HTTP_NO_CONTENT, error_list
                )

        # --- Implement file-by-file processing -------------------------------

        # Hidden paths (ancestors of failed deletes) {<path>: True, ...}
        ignore_dict = {}
        for child_res in reverse_child_ist:
            if child_res.path in ignore_dict:
                _logger.debug(f"Skipping {child_res.path} (contains error child)")
                ignore_dict[util.get_uri_parent(child_res.path)] = ""
                continue

            try:
                # 9.6.1.: Any headers included with delete must be applied in
                #         processing every resource to be deleted
                self._evaluate_if_headers(child_res, environ)
                self._check_write_permission(child_res, "0", environ)
                child_res.delete()
                # Double-check, if deletion succeeded
                if provider.exists(child_res.path, environ):
                    raise DAVError(
                        HTTP_INTERNAL_ERROR, "Resource could not be deleted."
                    )
            except DAVError as e:
                error_list.append((child_res.get_href(), as_DAVError(e)))
                ignore_dict[util.get_uri_parent(child_res.path)] = True

        # --- Send response ---------------------------------------------------

        return self._send_response(
            environ, start_response, res, HTTP_NO_CONTENT, error_list
        )

    def _stream_data(self, environ, block_size):
        """Get the data."""
        while True:
            buf = environ["wsgi.input"].read(block_size)
            if buf == b"":
                break
            environ["wsgidav.some_input_read"] = 1
            yield buf
        environ["wsgidav.all_input_read"] = 1

    def do_PUT(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_PUT
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.get_resource_inst(path, environ)
        parentRes = provider.get_resource_inst(util.get_uri_parent(path), environ)

        isnewfile = res is None

        # Test for unsupported stuff
        if "HTTP_CONTENT_ENCODING" in environ:
            util.fail(HTTP_NOT_IMPLEMENTED, "Content-encoding header is not supported.")

        # An origin server that allows PUT on a given target resource MUST send
        # a 400 (Bad Request) response to a PUT request that contains a
        # Content-Range header field
        # (http://tools.ietf.org/html/rfc7231#section-4.3.4)
        if "HTTP_CONTENT_RANGE" in environ:
            util.fail(
                HTTP_BAD_REQUEST, "Content-range header is not allowed on PUT requests."
            )

        if res and res.is_collection:
            self._fail(HTTP_METHOD_NOT_ALLOWED, "Cannot PUT to a collection")
        elif (
            parentRes is None or not parentRes.is_collection
        ):  # TODO: allow parentRes==None?
            self._fail(HTTP_CONFLICT, "PUT parent must be a collection")

        self._evaluate_if_headers(res, environ)

        if isnewfile:
            self._check_write_permission(parentRes, "0", environ)
            res = parentRes.create_empty_resource(util.get_uri_name(path))
        else:
            self._check_write_permission(res, "0", environ)

        hasErrors = False
        try:
            data_stream = self._stream_data(environ, self.block_size)

            fileobj = res.begin_write(content_type=environ.get("CONTENT_TYPE"))

            # Process the data in the body.

            # If the fileobj has a writelines() method, give it the data stream.
            # If it doesn't, itearate the stream and call write() for each
            # iteration. This gives providers more flexibility in how they
            # consume the data.
            if getattr(fileobj, "writelines", None):
                fileobj.writelines(data_stream)
            else:
                for data in data_stream:
                    fileobj.write(data)

            fileobj.close()

        except Exception as e:
            res.end_write(with_errors=True)
            _logger.exception("PUT: byte copy failed")
            util.fail(e)

        res.end_write(with_errors=hasErrors)

        headers = None
        if res.support_etag():
            etag = checked_etag(res.get_etag(), allow_none=True)
            if etag is not None:
                headers = [("ETag", f'"{etag}"')]

        if isnewfile:
            return util.send_status_response(
                environ, start_response, HTTP_CREATED, add_headers=headers
            )
        return util.send_status_response(
            environ, start_response, HTTP_NO_CONTENT, add_headers=headers
        )

    def do_COPY(self, environ, start_response):
        return self._copy_or_move(environ, start_response, False)

    def do_MOVE(self, environ, start_response):
        return self._copy_or_move(environ, start_response, True)

    def _copy_or_move(self, environ, start_response, is_move):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_COPY
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_MOVE
        """
        src_path = environ["PATH_INFO"]
        provider = self._davProvider
        src_res = provider.get_resource_inst(src_path, environ)
        src_parent_res = provider.get_resource_inst(
            util.get_uri_parent(src_path), environ
        )

        def _debug_exception(e):
            """Log internal exceptions with stacktrace that otherwise would be hidden."""
            if isinstance(e, DAVError):
                if self._verbose >= 5:
                    _logger.exception("_debug_exception")
            else:
                if self._verbose >= 3:
                    _logger.exception("_debug_exception")
            return

        # --- Check source ----------------------------------------------------

        if src_res is None:
            self._fail(HTTP_NOT_FOUND, src_path)
        if "HTTP_DESTINATION" not in environ:
            self._fail(HTTP_BAD_REQUEST, "Missing required Destination header.")
        if environ.setdefault("HTTP_OVERWRITE", "T") not in ("T", "F"):
            # Overwrite defaults to 'T'
            self._fail(HTTP_BAD_REQUEST, "Invalid Overwrite header.")
        if util.get_content_length(environ) != 0:
            # RFC 2518 defined support for <propertybehavior>.
            # This was dropped with RFC 4918.
            # Still clients may send it (e.g. DAVExplorer 0.9.1 File-Copy) sends
            # <A:propertybehavior xmlns:A="DAV:"> <A:keepalive>*</A:keepalive>
            body = environ["wsgi.input"].read(util.get_content_length(environ))
            environ["wsgidav.all_input_read"] = 1
            _logger.info(f"Ignored copy/move  body: {body[:50]!r}...")

        if src_res.is_collection:
            # The COPY method on a collection without a Depth header MUST act as
            # if a Depth header with value "infinity" was included.
            # A client may submit a Depth header on a COPY on a collection with
            # a value of "0" or "infinity".
            environ.setdefault("HTTP_DEPTH", "infinity")
            if environ["HTTP_DEPTH"] not in ("0", "infinity"):
                self._fail(HTTP_BAD_REQUEST, "Invalid Depth header.")
            if is_move and environ["HTTP_DEPTH"] != "infinity":
                self._fail(
                    HTTP_BAD_REQUEST,
                    "Depth header for MOVE collection must be 'infinity'.",
                )
        else:
            # It's an existing non-collection: assume Depth 0
            # Note: litmus 'copymove: 3 (copy_simple)' sends 'infinity' for a
            # non-collection resource, so we accept that too
            environ.setdefault("HTTP_DEPTH", "0")
            if environ["HTTP_DEPTH"] not in ("0", "infinity"):
                self._fail(HTTP_BAD_REQUEST, "Invalid Depth header.")
            environ["HTTP_DEPTH"] = "0"

        # --- Get destination path and check for cross-realm access -----------

        # Destination header may be quoted (e.g. DAV Explorer sends unquoted,
        # Windows quoted)
        http_destination = unquote(environ["HTTP_DESTINATION"])

        # Return fragments as part of <path>
        # Fixes litmus -> running `basic': 9. delete_fragment....... WARNING:
        # DELETE removed collection resource withRequest-URI including
        # fragment; unsafe
        (
            dest_scheme,
            dest_netloc,
            dest_path,
            _dest_params,
            _dest_query,
            _dest_frag,
        ) = urlparse(http_destination, allow_fragments=False)

        if src_res.is_collection:
            dest_path = dest_path.rstrip("/") + "/"

        dest_scheme = dest_scheme.lower() if dest_scheme else ""
        url_scheme = environ["wsgi.url_scheme"].lower()
        fwd_scheme = environ.get("HTTP_X_FORWARDED_PROTO", "").lower()

        # hostnames are case-insensitive (#260)
        dest_netloc = dest_netloc.lower() if dest_netloc else ""

        url_host = environ["HTTP_HOST"].lower()
        fwd_host = environ.get("HTTP_X_FORWARDED_HOST", "").lower()

        if dest_scheme and dest_scheme not in (url_scheme, fwd_scheme):
            self._fail(
                HTTP_BAD_GATEWAY,
                "Source and destination must have the same scheme.\n"
                "If you are running behind a reverse proxy, you may have to "
                "rewrite the 'Destination' header.\n"
                "(See https://github.com/mar10/wsgidav/issues/183)",
            )
        elif dest_netloc and dest_netloc not in (url_host, fwd_host):
            # TODO: this should consider environ["SERVER_PORT"] also
            self._fail(
                HTTP_BAD_GATEWAY, "Source and destination must have the same host name."
            )

        if dest_path.startswith(provider.mount_path + provider.share_path + "/"):
            dest_path = dest_path[len(provider.mount_path + provider.share_path) :]
        else:
            # Inter-realm copying not supported, since its not possible to
            # authentication-wise

            # We might be running behind a reverse proxy.
            # If a mountpoint is defined, try to strip it, assuming the proxy
            # redirects  HOST/MOUNT/PATH -> SHARE/PATH
            if provider.mount_path and dest_path.startswith(provider.mount_path + "/"):
                _prev = dest_path
                dest_path = dest_path[len(provider.mount_path) :]
                # dest_path = provider.share_path + dest_path
                _logger.info(f"Rewrite DESTINATION path {_prev} -> {dest_path}")
            else:
                self._fail(HTTP_BAD_GATEWAY, "Inter-realm copy/move is not supported.")

        assert dest_path.startswith("/")

        # dest_path is now relative to current mount/share starting with '/'

        dest_res = provider.get_resource_inst(dest_path, environ)
        dest_exists = dest_res is not None

        dest_parent_res = provider.get_resource_inst(
            util.get_uri_parent(dest_path), environ
        )

        if not dest_parent_res or not dest_parent_res.is_collection:
            self._fail(HTTP_CONFLICT, "Destination parent must be a collection.")

        self._evaluate_if_headers(src_res, environ)
        self._evaluate_if_headers(dest_res, environ)
        # Check permissions
        # http://www.webdav.org/specs/rfc4918.html#rfc.section.7.4
        if is_move:
            self._check_write_permission(src_res, "infinity", environ)
            # Cannot remove members from locked-0 collections
            if src_parent_res:
                self._check_write_permission(src_parent_res, "0", environ)

        # Cannot create or new members in locked-0 collections
        if not dest_exists:
            self._check_write_permission(dest_parent_res, "0", environ)
        # If target exists, it must not be locked
        self._check_write_permission(dest_res, "infinity", environ)

        if src_path == dest_path:
            self._fail(HTTP_FORBIDDEN, "Cannot copy/move source onto itself")
        elif util.is_equal_or_child_uri(src_path, dest_path):
            self._fail(HTTP_FORBIDDEN, "Cannot copy/move source below itself")

        if dest_exists and environ["HTTP_OVERWRITE"] != "T":
            self._fail(
                HTTP_PRECONDITION_FAILED,
                "Destination already exists and Overwrite is set to false",
            )

        # --- Let provider handle the request natively ------------------------

        # Errors in copy/move; [ (<ref-url>, <DAVError>), ... ]
        error_list = []
        success_code = HTTP_CREATED
        if dest_exists:
            success_code = HTTP_NO_CONTENT

        try:
            if is_move:
                handled = src_res.handle_move(dest_path)
            else:
                isInfinity = environ["HTTP_DEPTH"] == "infinity"
                handled = src_res.handle_copy(dest_path, depth_infinity=isInfinity)
            assert handled in (True, False) or type(handled) is list
            if type(handled) is list:
                error_list = handled
                handled = True
        except Exception as e:
            _debug_exception(e)
            error_list = [(src_res.get_href(), as_DAVError(e))]
            handled = True
        if handled:
            return self._send_response(
                environ, start_response, src_res, HTTP_NO_CONTENT, error_list
            )

        # --- Cleanup destination before copy/move ----------------------------

        src_list = src_res.get_descendants(add_self=True)

        src_root_len = len(src_path)
        dest_root_len = len(dest_path)

        if dest_exists:
            if is_move or not dest_res.is_collection or not src_res.is_collection:
                # MOVE:
                # If a resource exists at the destination and the Overwrite
                # header is "T", then prior to performing the move, the server
                # MUST perform a DELETE with "Depth: infinity" on the
                # destination resource.
                _logger.debug(f"Remove dest before move: {dest_res!r}")
                dest_res.delete()
                dest_res = None
            else:
                # COPY collection over collection:
                # Remove destination files, that are not part of source, because
                # source and dest collections must not be merged (9.8.4).
                # This is not the same as deleting the complete dest collection
                # before copying, because that would also discard the history of
                # existing resources.
                reverse_dest_list = dest_res.get_descendants(
                    depth_first=True, add_self=False
                )
                src_path_list = [s.path for s in src_list]
                _logger.debug(f"check src_path_list: {src_path_list}")
                for dres in reverse_dest_list:
                    _logger.debug(f"check unmatched dest before copy: {dres}")
                    rel_url = dres.path[dest_root_len:]
                    sp = src_path + rel_url
                    if sp not in src_path_list:
                        _logger.debug(f"Remove unmatched dest before copy: {dres}")
                        dres.delete()

        # --- Let provider implement recursive move ---------------------------
        # We do this only, if the provider supports it, and no conflicts exist.
        # A provider can implement this very efficiently, without allocating
        # double memory as a copy/delete approach would.

        if is_move and src_res.support_recursive_move(dest_path):
            has_conflicts = False
            for s in src_list:
                try:
                    self._evaluate_if_headers(s, environ)
                except Exception as e:
                    _debug_exception(e)
                    has_conflicts = True
                    break

            if not has_conflicts:
                try:
                    _logger.debug(f"Recursive move: {src_res} -> {dest_path!r}")
                    error_list = src_res.move_recursive(dest_path)
                except Exception as e:
                    _debug_exception(e)
                    error_list = [(src_res.get_href(), as_DAVError(e))]

                return self._send_response(
                    environ, start_response, src_res, success_code, error_list
                )

        # --- Copy/move file-by-file using copy/delete ------------------------

        # We get here, if
        # - the provider does not support recursive moves
        # - this is a copy request
        #   In this case we would probably not win too much by a native provider
        #   implementation, since we had to handle single child errors anyway.
        # - the source tree is partially locked
        #   We would have to pass this information to the native provider.

        # Hidden paths (paths of failed copy/moves) {<src_path>: True, ...}
        ignore_dict = {}

        for sres in src_list:
            # Skip this resource, if there was a failure copying a parent
            parent_error = False
            for ignorePath in ignore_dict.keys():
                if util.is_equal_or_child_uri(ignorePath, sres.path):
                    parent_error = True
                    break
            if parent_error:
                _logger.debug(f"Copy: skipping {sres.path!r}, because of parent error")
                continue

            try:
                rel_url = sres.path[src_root_len:]
                dpath = dest_path + rel_url

                self._evaluate_if_headers(sres, environ)

                # We copy resources and their properties top-down.
                # Collections are simply created (without members), for
                # non-collections bytes are copied (overwriting target)
                sres.copy_move_single(dpath, is_move=is_move)

                # If copy succeeded, and it was a non-collection delete it now.
                # So the source tree shrinks while the destination grows and we
                # don't have to allocate the memory twice.
                # We cannot remove collections here, because we have not yet
                # copied all children.
                if is_move and not sres.is_collection:
                    sres.delete()

            except Exception as e:
                _debug_exception(e)
                ignore_dict[sres.path] = True
                # TODO: the error-href should be 'most appropriate of the source
                # and destination URLs'. So maybe this should be the destination
                # href sometimes.
                # http://www.webdav.org/specs/rfc4918.html#rfc.section.9.8.5
                error_list.append((sres.get_href(), as_DAVError(e)))

        # MOVE: Remove source tree (bottom-up)
        if is_move:
            reverse_src_list = src_list[:]
            reverse_src_list.reverse()
            _logger.debug(f"Delete after move, ignore_dict={ignore_dict}")
            for sres in reverse_src_list:
                # Non-collections have already been removed in the copy loop.
                if not sres.is_collection:
                    continue
                # Skip collections that contain errors (unmoved resources)
                child_error = False
                for ignorePath in ignore_dict.keys():
                    if util.is_equal_or_child_uri(sres.path, ignorePath):
                        child_error = True
                        break
                if child_error:
                    _logger.debug(
                        f"Delete after move: skipping {sres.path!r}, because of child error"
                    )
                    continue

                try:
                    _logger.debug(f"Remove collection after move: {sres}")
                    sres.delete()
                except Exception as e:
                    _debug_exception(e)
                    error_list.append((src_res.get_href(), as_DAVError(e)))

            _logger.debug(f"ErrorList: {error_list}")

        # --- Return response -------------------------------------------------

        return self._send_response(
            environ, start_response, src_res, success_code, error_list
        )

    def do_LOCK(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_LOCK
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.get_resource_inst(path, environ)
        lock_man = provider.lock_manager

        if lock_man is None:
            # http://www.webdav.org/specs/rfc4918.html#rfc.section.6.3
            self._fail(HTTP_NOT_IMPLEMENTED, "This realm does not support locking.")
        if res and res.prevent_locking():
            self._fail(HTTP_FORBIDDEN, "This resource does not support locking.")

        if environ.setdefault("HTTP_DEPTH", "infinity") not in ("0", "infinity"):
            self._fail(HTTP_BAD_REQUEST, "Expected Depth: 'infinity' or '0'.")

        self._evaluate_if_headers(res, environ)

        timeout_secs = util.read_timeout_value_header(environ.get("HTTP_TIMEOUT", ""))
        submitted_token_list = environ["wsgidav.ifLockTokenList"]

        lockinfo_el = util.parse_xml_body(environ, allow_empty=True)

        # --- Special case: empty request body --------------------------------

        if lockinfo_el is None:
            # TODO: @see 9.10.2
            # TODO: 'URL of a resource within the scope of the lock'
            #       Other (shared) locks are unaffected and don't prevent refreshing
            # TODO: check for valid user
            # TODO: check for If with single lock token
            environ["HTTP_DEPTH"] = "0"  # MUST ignore depth header on refresh

            if res is None:
                self._fail(
                    HTTP_BAD_REQUEST, "LOCK refresh must specify an existing resource."
                )
            if len(submitted_token_list) != 1:
                self._fail(
                    HTTP_BAD_REQUEST,
                    "Expected a lock token (only one lock may be refreshed at a time).",
                )
            elif not lock_man.is_url_locked_by_token(
                res.get_ref_url(), submitted_token_list[0]
            ):
                self._fail(
                    HTTP_PRECONDITION_FAILED,
                    "Lock token does not match URL.",
                    err_condition=PRECONDITION_CODE_LockTokenMismatch,
                )
            # TODO: test, if token is owned by user

            lock = lock_man.refresh(submitted_token_list[0], timeout=timeout_secs)

            # The lock root may be <path>, or a parent of <path>.
            lock_path = provider.ref_url_to_path(lock["root"])
            lock_res = provider.get_resource_inst(lock_path, environ)

            prop_el = xml_tools.make_prop_elem()
            # TODO: handle exceptions in get_property_value
            lockdiscovery_el = lock_res.get_property_value("{DAV:}lockdiscovery")
            prop_el.append(lockdiscovery_el)

            # Lock-Token header is not returned
            xml = xml_tools.xml_to_bytes(prop_el)
            start_response(
                "200 OK",
                [
                    ("Content-Type", "application/xml; charset=utf-8"),
                    ("Content-Length", str(len(xml))),
                    ("Date", util.get_rfc1123_time()),
                ],
            )
            return [xml]

        # --- Standard case: parse xml body -----------------------------------

        if lockinfo_el.tag != "{DAV:}lockinfo":
            self._fail(HTTP_BAD_REQUEST)

        lock_type = None
        lock_scope = None
        lock_owner = util.to_bytes("")
        lock_depth = environ.setdefault("HTTP_DEPTH", "infinity")

        for linode in lockinfo_el:
            if linode.tag == "{DAV:}lockscope":
                for lsnode in linode:
                    if lsnode.tag == "{DAV:}exclusive":
                        lock_scope = "exclusive"
                    elif lsnode.tag == "{DAV:}shared":
                        lock_scope = "shared"
                    break
            elif linode.tag == "{DAV:}locktype":
                for ltnode in linode:
                    if ltnode.tag == "{DAV:}write":
                        lock_type = "write"  # only type accepted
                    break

            elif linode.tag == "{DAV:}owner":
                # Store whole <owner> tag, so we can use etree.XML() later
                lock_owner = xml_tools.xml_to_bytes(linode, pretty=False)

            else:
                self._fail(HTTP_BAD_REQUEST, f"Invalid node {linode.tag!r}.")

        if not lock_scope:
            self._fail(HTTP_BAD_REQUEST, "Missing or invalid lockscope.")
        if not lock_type:
            self._fail(HTTP_BAD_REQUEST, "Missing or invalid locktype.")

        if environ.get("wsgidav.debug_break"):
            pass  # break point

        # TODO: check for locked parents BEFORE creating an empty child

        # http://www.webdav.org/specs/rfc4918.html#rfc.section.9.10.4
        # Locking unmapped URLs: must create an empty resource
        createdNewResource = False
        if res is None:
            parentRes = provider.get_resource_inst(util.get_uri_parent(path), environ)
            if not parentRes or not parentRes.is_collection:
                self._fail(HTTP_CONFLICT, "LOCK-0 parent must be a collection")
            res = parentRes.create_empty_resource(util.get_uri_name(path))
            createdNewResource = True

        # --- Check, if path is already locked --------------------------------

        # May raise DAVError(HTTP_LOCKED):
        lock = lock_man.acquire(
            url=res.get_ref_url(),
            lock_type=lock_type,
            lock_scope=lock_scope,
            lock_depth=lock_depth,
            lock_owner=lock_owner,
            timeout=timeout_secs,
            principal=environ["wsgidav.user_name"],
            token_list=submitted_token_list,
        )

        # Lock succeeded
        prop_el = xml_tools.make_prop_elem()
        # TODO: handle exceptions in get_property_value
        lockdiscovery_el = res.get_property_value("{DAV:}lockdiscovery")
        prop_el.append(lockdiscovery_el)

        respcode = "200 OK"
        if createdNewResource:
            respcode = "201 Created"

        xml = xml_tools.xml_to_bytes(prop_el)
        start_response(
            respcode,
            [
                ("Content-Type", "application; charset=utf-8"),
                ("Content-Length", str(len(xml))),
                ("Lock-Token", lock["token"]),
                ("Date", util.get_rfc1123_time()),
            ],
        )
        return [xml]

        # TODO: LOCK may also fail with HTTP_FORBIDDEN.
        #       In this case we should return 207 Multi-Status.
        #       http://www.webdav.org/specs/rfc4918.html#rfc.section.9.10.9
        #       Checking this would require to call res.prevent_locking()
        #       recursively.

    #        # --- Locking FAILED: return fault response
    #        if len(conflictList) == 1 and conflictList[0][0]["root"] == res.get_ref_url():
    #            # If there is only one error for the root URL, send as simple error response
    #            return util.send_status_response(environ, start_response, conflictList[0][1])
    #
    #        dictStatus = {}
    #
    #        for lock_dict, e in conflictList:
    #            dictStatus[lock_dict["root"]] = e
    #
    #        if not res.get_ref_url() in dictStatus:
    #            dictStatus[res.get_ref_url()] = DAVError(HTTP_FAILED_DEPENDENCY)
    #
    #        # Return multi-status fault response
    #        multistatusEL = xml_tools.make_multistatus_el()
    #        for nu, e in dictStatus.items():
    #            responseEL = etree.SubElement(multistatusEL, "{DAV:}response")
    #            etree.SubElement(responseEL, "{DAV:}href").text = nu
    #            etree.SubElement(responseEL, "{DAV:}status").text = "HTTP/1.1 %s" %
    #                get_http_status_string(e)
    #            # TODO: all responses should have this(?):
    #            if e.context_info:
    #                etree.SubElement(multistatusEL, "{DAV:}responsedescription").text = e.context_info
    #
    # if responsedescription:
    #            etree.SubElement(multistatusEL, "{DAV:}responsedescription").text = "\n".join(
    #                responsedescription)
    #
    # return util.send_multi_status_response(environ, start_response,
    # multistatusEL)

    def do_UNLOCK(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_UNLOCK
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = self._davProvider.get_resource_inst(path, environ)

        lock_man = provider.lock_manager
        if lock_man is None:
            self._fail(HTTP_NOT_IMPLEMENTED, "This share does not support locking.")
        elif util.get_content_length(environ) != 0:
            self._fail(
                HTTP_MEDIATYPE_NOT_SUPPORTED,
                "The server does not handle any body content.",
            )
        elif res is None:
            self._fail(HTTP_NOT_FOUND, path)
        elif "HTTP_LOCK_TOKEN" not in environ:
            self._fail(HTTP_BAD_REQUEST, "Missing lock token.")

        self._evaluate_if_headers(res, environ)

        lock_token = environ["HTTP_LOCK_TOKEN"].strip("<>")
        ref_url = res.get_ref_url()

        if not lock_man.is_url_locked_by_token(ref_url, lock_token):
            self._fail(
                HTTP_CONFLICT,
                "Resource is not locked by token.",
                err_condition=PRECONDITION_CODE_LockTokenMismatch,
            )

        if not lock_man.is_token_locked_by_user(
            lock_token, environ["wsgidav.user_name"]
        ):
            # TODO: there must be a way to allow this for admins.
            #       Maybe test for "remove_locks" in environ["wsgidav.roles"]
            self._fail(HTTP_FORBIDDEN, "Token was created by another user.")

        # TODO: Is this correct?: unlock(a/b/c) will remove Lock for 'a/b'
        lock_man.release(lock_token)

        return util.send_status_response(environ, start_response, HTTP_NO_CONTENT)

    def do_OPTIONS(self, environ, start_response):
        """
        @see http://www.webdav.org/specs/rfc4918.html#HEADER_DAV
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        config = environ["wsgidav.config"]
        hotfixes = util.get_dict_value(config, "hotfixes", as_dict=True)

        res = provider.get_resource_inst(path, environ)

        dav_compliance_level = "1,2"
        if provider is None or provider.is_readonly() or provider.lock_manager is None:
            dav_compliance_level = "1"

        headers = [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", "0"),
            ("DAV", dav_compliance_level),
            ("Date", util.get_rfc1123_time()),
        ]

        is_asterisk_options = path == "*"
        if path == "/":
            # Hotfix for WinXP / Vista: accept '/' for a '*'
            treat_as_asterisk = hotfixes.get("treat_root_options_as_asterisk")
            if treat_as_asterisk:
                is_asterisk_options = True  # Hotfix for WinXP
            else:
                _logger.info("Got OPTIONS '/' request")

        if is_asterisk_options:
            # Answer HTTP 'OPTIONS' method on server-level.
            # From RFC 2616
            # If the Request-URI is an asterisk ("*"), the OPTIONS request is
            # intended to apply to the server in general rather than to a specific
            # resource. Since a server's communication options typically depend on
            # the resource, the "*" request is only useful as a "ping" or "no-op"
            # type of method; it does nothing beyond allowing the client to test the
            # capabilities of the server. For example, this can be used to test a
            # proxy for HTTP/1.1 compliance (or lack thereof).
            start_response("200 OK", headers)
            return [b""]

        # Determine allowed request methods
        allow = ["OPTIONS"]
        if res and res.is_collection:
            # Existing collection
            allow.extend(["HEAD", "GET", "PROPFIND"])
            # if provider.prop_manager is not None:
            #     allow.extend( [ "PROPFIND" ] )
            if not provider.is_readonly():
                allow.extend(["DELETE", "COPY", "MOVE", "PROPPATCH"])
                # if provider.prop_manager is not None:
                #     allow.extend( [ "PROPPATCH" ] )
                if provider.lock_manager is not None:
                    allow.extend(["LOCK", "UNLOCK"])
        elif res:
            # Existing resource
            allow.extend(["HEAD", "GET", "PROPFIND"])
            # if provider.prop_manager is not None:
            #     allow.extend( [ "PROPFIND" ] )
            if not provider.is_readonly():
                allow.extend(["PUT", "DELETE", "COPY", "MOVE", "PROPPATCH"])
                # if provider.prop_manager is not None:
                #     allow.extend( [ "PROPPATCH" ] )
                if provider.lock_manager is not None:
                    allow.extend(["LOCK", "UNLOCK"])
            if res.support_ranges():
                headers.append(("Accept-Ranges", "bytes"))
        elif provider.is_collection(util.get_uri_parent(path), environ):
            # A new resource below an existing collection
            # TODO: should we allow LOCK here? I think it is allowed to lock an
            # non-existing resource
            if not provider.is_readonly():
                allow.extend(["PUT", "MKCOL"])
        else:
            self._fail(HTTP_NOT_FOUND, path)

        headers.append(("Allow", ", ".join(allow)))

        if environ["wsgidav.config"].get("add_header_MS_Author_Via", False):
            headers.append(("MS-Author-Via", "DAV"))

        start_response("200 OK", headers)
        return [b""]

    def do_GET(self, environ, start_response):
        return self._send_resource(environ, start_response, is_head_method=False)

    def do_HEAD(self, environ, start_response):
        return self._send_resource(environ, start_response, is_head_method=True)

    def _send_resource(self, environ, start_response, is_head_method):
        """
        If-Range
            If the entity is unchanged, send me the part(s) that I am missing;
            otherwise, send me the entire new entity
            If-Range: "737060cd8c284d8af7ad3082f209582d"

        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.27
        """
        path = environ["PATH_INFO"]
        res = self._davProvider.get_resource_inst(path, environ)

        if util.get_content_length(environ) != 0:
            self._fail(
                HTTP_MEDIATYPE_NOT_SUPPORTED,
                "The server does not handle any body content.",
            )
        elif environ.setdefault("HTTP_DEPTH", "0") != "0":
            self._fail(HTTP_BAD_REQUEST, "Only Depth: 0 supported.")
        elif res is None:
            self._fail(HTTP_NOT_FOUND, path)
        elif res.is_collection:
            self._fail(
                HTTP_FORBIDDEN,
                "Directory browsing is not enabled."
                "(to enable it add WsgiDavDirBrowser to the middleware_stack "
                "option and set dir_browser.enabled = True option.)",
            )

        self._evaluate_if_headers(res, environ)

        filesize = res.get_content_length()
        if filesize is None:
            filesize = -1  # flag logic to read until EOF

        last_modified = res.get_last_modified()
        if last_modified is None:
            last_modified = -1

        etag = checked_etag(res.get_etag(), allow_none=True)
        if etag is None:
            etag = "[]"

        # Ranges
        do_ignore_ranges = (
            not res.support_content_length()
            or not res.support_ranges()
            or filesize == 0
        )
        if (
            "HTTP_RANGE" in environ
            and "HTTP_IF_RANGE" in environ
            and not do_ignore_ranges
        ):
            if_range = environ["HTTP_IF_RANGE"]
            # Try as http-date first (Return None, if invalid date string)
            secstime = util.parse_time_string(if_range)
            if secstime:
                # cast to integer, as last_modified may be a floating point number
                if int(last_modified) != secstime:
                    do_ignore_ranges = True
            else:
                # Use as entity tag
                if_range = if_range.strip('" ')
                if etag is None or if_range != etag:
                    do_ignore_ranges = True

        is_partial_ranges = False
        if "HTTP_RANGE" in environ and not do_ignore_ranges:
            is_partial_ranges = True
            list_ranges, _totallength = util.obtain_content_ranges(
                environ["HTTP_RANGE"], filesize
            )
            if len(list_ranges) == 0:
                # No valid ranges present
                self._fail(HTTP_RANGE_NOT_SATISFIABLE, "No valid ranges present")

            # More than one range present -> take only the first range, since
            # multiple range returns require multipart, which is not supported
            # obtain_content_ranges supports more than one range in case the above
            # behaviour changes in future
            (range_start, range_end, range_length) = list_ranges[0]
        else:
            (range_start, range_end, range_length) = (0, filesize - 1, filesize)

        # Content Processing
        mimetype = res.get_content_type()  # provider.get_content_type(path)

        response_headers = []
        if res.support_content_length():
            # Content-length must be of type string
            response_headers.append(("Content-Length", str(range_length)))
        if res.support_modified():
            response_headers.append(
                ("Last-Modified", util.get_rfc1123_time(last_modified))
            )
        response_headers.append(("Content-Type", mimetype))
        response_headers.append(("Date", util.get_rfc1123_time()))
        if res.support_etag():
            response_headers.append(("ETag", f'"{etag}"'))

        if res.support_ranges():
            response_headers.append(("Accept-Ranges", "bytes"))

        if "response_headers" in environ["wsgidav.config"]:
            custom_headers = environ["wsgidav.config"]["response_headers"]
            for header, value in custom_headers:
                response_headers.append((header, value))

        res.finalize_headers(environ, response_headers)

        if is_partial_ranges:
            response_headers.append(
                (
                    "Content-Range",
                    f"bytes {range_start}-{range_end}/{filesize}",
                )
            )
            start_response("206 Partial Content", response_headers)
        else:
            start_response("200 OK", response_headers)

        # Return empty body for HEAD requests
        if is_head_method:
            yield b""
            return

        fileobj = res.get_content()

        if not do_ignore_ranges:
            fileobj.seek(range_start)

        contentlengthremaining = range_length
        try:
            while 1:
                if (
                    contentlengthremaining < 0
                    or contentlengthremaining > self.block_size
                ):
                    readbuffer = fileobj.read(self.block_size)
                else:
                    readbuffer = fileobj.read(contentlengthremaining)
                assert util.is_bytes(readbuffer)
                yield readbuffer
                contentlengthremaining -= len(readbuffer)
                if len(readbuffer) == 0 or contentlengthremaining == 0:
                    break
        finally:
            # yield readbuffer MAY fail with a GeneratorExit error
            # we still need to close the file
            fileobj.close()
        return


#    def do_TRACE(self, environ, start_response):
#        """ TODO: TRACE pending, but not essential."""
#        self._fail(HTTP_NOT_IMPLEMENTED)
