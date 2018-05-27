# Changelog

## 3.0.0 / Unreleased

- Refactor middleware stack
  - RequestResolver and WsgiDavDirBrowser are now simple members of `middleware_stack`
    and not specially treated
  - Removed `middleware.isSuitable()` because we don't want to enforce
    a specific base class for middleware (introduced with #12)
- Improve configuration files:
  - WsgiDAVApp constructor now assumes default settings. The passed options
    override those.
  - YAML is now the preferred configuration file format.
  - #89 Add support for JSON config files (JavaScript-style comments allowed)
  - Use wsgidav.yaml or wsgidav.json by default if they exist in the local folder
  - `middleware_stack` entries can also be strings or dicts that are
    evaluated to import and instantiate middleware classes.
  - YAML and JSON config files allow to define and configure external middleware
    by strings
  - Renamed some settings. e.g. `accept_digest` => `http_authenticator.accept_digest`
  - Log format configurable
- **TODO** #94: Use utf-8 as default
- Refactor WsgiDirBrowser:
  - Removed option 'dir_browser.enabled' (modify `middleware_stack` instead)
  - Uses Jinja2 and loads static assets through own WsgiDAV provider
- MSI setup uses Python 3.6


## 2.4.0 / Unreleased

- Improve configuration files:
  - #89 Add support for JSON config files to built-in server runner
  - wsgidav.json can contain comments now (JavaScript syntax)
  - Support YAML format as well
  - Use wsgidav.yaml or wsgidav.json by default if they exist in the local folder
- Expand '~' in `--root` and `--config` command line options
- Bump Cheroot version to 6.2+ (used by MSI installer)
- #97: Fix assumption that QUERY_STRING is in environment (dir_browser)
- #99: Fix virtual_dav_provider for Py3: WSGI expects binary instead of str
- #100: Send ETags with PUT response
- #101: Fail cleanly if trying to PUT to unknown collection
- Reworked documentation on Read The Docs
- Refactor logging:
  - Re-define verbosity level range: 0..5
  - Removed usage of `print` in favor of `logging.getLogger().debug`
  - Remove util.note(), .status(), ... helpers
- Refactor code base:
  - Use `.format()` syntax instead of `%s` for string templating
  - Mandatory PEP8 compliance (checked by flake8)


## 2.3.0 / 2018-04-06

- #80: Drop support for Python 3.3 (end-of-life September 2017)
- #86: Give custom PropertyManager implementations access to the environ
- #87: Don't assume sys.stdout.encoding is not None
- #90: Custom response headers
- #93: Add support for streaming large files on Mac


## 2.2.4 / 2017-08-11

- Fix #75: Return 401 when auth method is not supported
- Fix #77: removeProperty call to not lose dryRun, otherwise removeProperty is
  called twice for real
- Fix #79: Prevent error when missing environment variable


## 2.2.2 / 2017-06-23

- #69: Rectifying naming disparity for CherryPy server
- Fix #67: lock manager returns timeout negative seconds
- Fix #71: Attempts to unlock a nonexistent resource cause an internal server error
- Fix #73: Failed on processing non-iso-8859-1 characters on Python 3
- MSI setup uses Python 3.5


## 2.2.1 / 2017-02-25

- #65: Support for Cheroot server, which is the standalone WSGI server of CherryPy
  since version 9.0.
  `--server=cheroot` is the default now.
- New option `--ssl-adapter`, used by 'cheroot' server if SSL certificates are
  configured. Defaults to 'builtin'.<br>
  Set to 'pyopenssl' to use an existing OpenSSL nstallation.
  (Note: Currently broken as of Cheroot 5.1, see cherrypy/cheroot#6)
- Deprecate cherrypy.wsgiserver.<br>
  `--server=cherrypy` was renamed to `--cherrypy-wsgiserver`
- #64: Fix LOCK without owner
- #65: Add lxml to MSI installer
- Release as Wheel


## 2.1.0 / 2016-11-13

- #42: Remove print usage in favor of logging (Sergi Almacellas Abellana)
- #43: PEP8 fixes (Sergi Almacellas Abellana, Tom Viner)
- #45 New method `_DAVResource.finalizeHeaders(environ, responseHeaders)` (Samuel Fekete)
- #55 Custom response handlers for PUT, GET etc.
- New helpers `addons.stream_tools.FileLikeQueue` and `StreamingFile` allow to
  pipe / proxy PUT requests to external consumers.


## 2.0.1 / 2016-10-07

- #46 Wrap xml libraries with the equivalent defusedxml packages (Tom Viner)


## 2.0.0 / 2016-10-02

- #4: Support Python 3
- Windows MSI Installer
- Drop support for Python 2.6
- cherrypy.wsgiserver is no longer included as source package.
  CherryPy is still the recommended standalone WSGI server, and deployed with the
  binary installation. It is also installed as dependency by `setup.py test`.
  However if a source installation is used, either install cherrypy using
  `pip install cherrypy` or choose another server using the `--server` option.
- Configuration:
  - New options `server` and `server_args`
  - Removed `ext_servers` option
- Standalone server:
  - New command line option `--server` (defaults to cherrypy)
  - New command line option `--no-config`
  - Removed command line option `-d` use `-vv` instead
- Use py.test & tox


## 1.3.0 / 2016-08-24

- #19: Add option `mutable_live_props` to support setting last modified file/directory timestamps
  (Jonas Bardino)
- #23: Fix Windows file manager and OSX Finder fails on file names with comma (Jonas Bardino)
- #27: Do not install tests (Erich Seifert)
- #28: New option `trusted_auth_header` allows reverse proxy authentication (Mageti)
- #30: API change to allow much easier per-user chrooting (Jonas Bardino)
- #32: Fix digest authentication rejected due to invalid header (Adrian Crețu)


## 1.2.0 / 2015-05-14

- #8: Unquote PATH_INFO is now optional 'unquote_path_info'; defaults to false.
  (Brian Sipos)
- #9: Fixed status codes for apache mod_wsgi (Brian Sipos)
- #10: Hotfix for file copy on GVFS (Brian Sipos)
- #12: Configurable middleware stack (Pavel Shiryaev)
- #15: Fix Finder access (Jonas Bardino)


## 1.1.0 / 2014-01-01

- New dir_browser option 'ms_sharepoint_plugin' to start MS Office documents in edit-mode
- Moved project from Google Code to GitHub
- Moved documentation to ReadTheDocs


## 1.0.0 / 2013-12-27

- **NOTE**: no longer tested with Python 2.4.
- SSL sample with bogo-cert
- Renamed 'msmount' option to 'ms_mount'.
- Files are always stored in binary mode.
- Port and hostname can now be specified in config file (before: command line only).
- New option for dir_browser: 'msSharepointUrls' will prepend 'ms-word:ofe|u|' to URL for MS Offce documents.
- New option 'add_header_MS_Author_Via = True' to support editing with Microsoft Office
- FilesystemProvider expands variables like '~', '$Name' and '%NAME%' in folder paths (i.e. '~/foo' -> '/Users/joe/foo')
- Issue #55 Failure operating with litmus test suite, Mac OS X WebDAV Client, Windows 7 (thanks to Ben Allums)
- Fixed issue #48 Allow the dirbrowser to be configured from the config file (thanks to Herman Grecco)
- Fixed issue #43 Unicode error in Ubuntu
- Allow Ctrl-C / SIGINT to stop CherryPyWSGIServer
- Made mimetype guessing more robust
- Updated CherryPy standalone WSGI server to 3.2.4
- Support 'setup.py test' which uses nosetests and includes litmus


## 0.5.0 / 2011-01-16

- Bundled with CherryPy standalone WSGI server
- Added copyright notes for original PyFileServer
- Changed signature of DAVProvider (and derived classes): provider argument was
  removed
- New method DAVResource.getMemberList() replaces getMemberNames().
- New class DAVCollection allows for more efficient implementation of custom
  providers.
- Forcing 'Connection: close', when a required Content-Length is missing.
  So it's possible now to return GET responses without knowing the size.
- New property manager based on CouchDB (addons.couch_property_manager)
- New property manager based on MongoDB (addons.mongo_property_manager)
- New sample DAV provider for MongoDBs (samples.mongo_dav_provider)
- Debug output goes to stdout (was stderr)
- Support davmount (rfc 4709).
- Added support for Microsoft FOLDER behavior.
- renamed displayType() -> getDirectoryInfo()
- Fixed RANGE response


## 0.4.0.b3

- Refactored LockManager. using separate LockStorage
- Bugfixes


## 0.4.0.b2 / 2010-02-15

- Bugfixes


## 0.4.0.b1

- Using HTTP/1.1 with keep-alive (St�phane KLEIN)
- Correctly return pre- and postconditions on lock conflicts.
- Added Sphinx docs
- Added Mercurial provider
- Changed configuration: no property manager used by default


## Until 0.4.0 alpha

See https://github.com/mar10/wsgidav/blob/master/doc/changelog04.md
