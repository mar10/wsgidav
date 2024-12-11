# Changelog

## 4.3.4 / Unreleased

- Test with Python 3.13
- Use ruff instead of black/isort

## 4.3.3 / 2024-05-04

- Deprecate Python 3.8 (EOL: 2024-10-14)
- Build Windows installer with Python 3.12
- Update to Cheroot 10.8
- [#315](https://github.com/mar10/wsgidav/issues/315) CHANGELOG.md is installed into the virtualenv or prefix root directory

## 4.3.2 / 2024-03-29

- [#318](https://github.com/mar10/wsgidav/issues/318) Error when used with lxml
- Test with Python 3.12
- Update to black 24.3
- Use ruff instead of flake8

## 4.3.1 / 2024-03-24

- New option `suppress_version_info` to suppress WsgiDAV's version info in
  responses (default: false).
- #298: `--root` argument honors `fs_dav_provider` configuration.
- #301: `_DAVResource` should have `is_link()` method to avoid dir_browser issues.
- #308: remove defusedxml.lxml dependency.

## 4.3.0 / 2023-09-24

- BREAKING:
  - See option `fs_dav_provider.follow_symlinks` below.
- Deprecate Python 3.7 (EOL: 2023-06-27)
- Install pam_dc dependencies using extra syntax: `pip install wsgidav[pam]`
- #281 Requesting range off end of file does not return 416 status code
- #290 Unable to upload chunked big file using requests python library.
- Add `logging.enable` option to activate the 'wsgidav' logger when this package
  is used as a library. This replaces an explicit call to `utils.init_logging()`.
  When running as CLI, this option is on by default.
- Add `fs_dav_provider` section to options.
- Add `fs_dav_provider.follow_symlinks` option to enable symlinks (default: false)<br>
  _follow_symlinks_ is false by default, since
  [symlinks may be a security risk](https://serverfault.com/questions/244592/followsymlinks-on-apache-why-is-it-a-security-risk).<br>
  File resources that are symlinks are still enumerated and listed by the
  directory browser. However trying to access content will raise '403 Forbidden'
  Pass _follow_symlinks=True_ to the FilesystemProvider constructor or yaml configuration
  to restore the previous behavior.
- Add `fs_dav_provider.shadow_map`, which can be used to blend in a favicon
  when context is opened inline (#230)
- Remove (unused) interface definitions
- Use the [Furo](https://github.com/pradyunsg/furo) documentation theme

## 4.2.0 / 2023-02-18

- #277 Add quota-used-bytes and quota-available-bytes (RFC4331) (@NewbieOrange)
- Build MSI installer with Python 3.11, cheroot 9.0, cx_Freeze 6.3 (may fix #278)
- Official support for Python 3.11
- Stop testing Python 3.6 (EOL 2021-12-21)
- Update to black 22.12

## 4.1.0 / 2022-11-11

- #246 Add dir_browser/htdocs folder setup.cfg (for install with `pip install  .`)
- #265 Fix PAM not threadsafe
- #268 Use relative paths to support reverse proxies
- Clarify how to use WsgiDAV behind a reverse proxy
- `mount_path` option is now validated (must be empty or start with a '/')
- Add `dir_browser.directory_slash` option to force trailing slashes (default: true).
  Also use relative paths in directory listings in order to improve behavior
  when running behind a reverse proxy.
- #183 Fix MOVE for reverse proxies (experimental)
- Resolve security advisory [CVE-2022-41905](https://github.com/mar10/wsgidav/security/advisories/GHSA-xx6g-jj35-pxjv)
  Thanks @brunnjf (Jon Brunn)

## 4.0.2 / 2022-08-01

- #245 Add charset utf-8 to Content-Type header
- #246 Add dir_browser/htdocs folder to sdist (.tar.gz)
- #248 Provider does not support set_last_modified" error
- #251 Fix removing locks in recursive mode
- #255 Fix ERROR: Invalid requirement: 'cheroot~=8'
- #260 Fix Case-Sensitivity issue on MOVE/COPY actions through Windows DAV
- Add shelve support to MSI installer (persistent lock- and property storage)
- Deprecate Python 3.6 (i.e. stop testing)

## 4.0.1 / 2022-01-11

- #241: Add SSL libs to MSI installer

## 4.0.0 / 2022-01-09

**Breaking Changes**

- Drop Python 2 support
- Drop support for Python syntax in config files (wsgidav.conf)
- Drop support for Microsoft Web Folders (option `dir_browser.ms_mount`).
- API now sometimes enforces some _named_ keyword args (`fn(<args>, *, ...)`)
- Rename option `lock_manager` to `lock_storage`
- Moved `lock_manager` and `lock_storage` modules to `lock_man` package.
- Move logging options to 'logging' section
- Drop flup and CherryPy support from CLI (use cheroot instead of CherryPy)

**New Features**

- Add CORS support
- hotfixes.re_encode_path_info is true by default (null evaluates to false now!)
- Add uvicorn server support to CLI
- `lock_storage`, `property_manager`, `provider_mapping`
  can now be configured in the YAML file to use custom implementations using
  this syntax:
  `{ "class": <class_path>, "args": [<arg>, ...], "kwargs": {"<arg_name>": <val>, ... } }`

**Other changes**

- Provider root paths are evaluated relative to the location of the configuration
  file
- DAVCollection, DAVNonCollection, DAVProvider are now ABCs.
- Deprecate hotfixes.winxp_accept_root_share_login and hotfixes.win_accept_anonymous_options
- DirBrowser supports `?davmount` URLs by default (option `dir_browser.davmount`).
  The new option `dir_browser.davmount_links` controls link display (default: false).
- #185 Fix FileLikeQueue for Python 3
- #222 Discrepancy between "getetag" property and ETag header

## 3.1.2 / Unreleased

## 3.1.1 / 2021-07-11

- #201 Check also HTTP_X_FORWARDED_HOST as alternative to DESTINATION header
- #216 Build with Python 3.8 (Py3.9 doesn't work on Windows7 / Windows Server 2008 R2 / earlier)
- #220 Fix exception whenever users access unknown realm
- #225 Include changelog in PyPI package

## 3.1.0 / 2021-01-04

- #181 Fix error for UTF8 (surrogate) filename
- #183 Support reverse proxies
- #186 Add sample Redis lock manager `LockStorageRedis` (Steffen Deusch)
- #191 Add option `dir_browser.htdocs_path`
- #193 Support gunicorn
- #195 Add password to lock_storage_redis
- #198 Fix exception with verbose > 3
- Use [Yabs](https://github.com/mar10/yabs) as release tool

## 3.0.3 / 2020-04-02

- #172 Fix missing import of collections_abc (regression in 3.0.2:
  this requires six 1.13+; dependencies have been updated)
- #177 Fix allow_anonymous_access()

## 3.0.2 / 2019-12-26

- Fixes for Python 3.8
- Deprecated support for Python 3.4 (reached end of live on 2019-03-18),
  i.e. stopped testing.
- #167 Docker image reduction from 244MB to 66.4MB
- #169 Replace jsmin with json5 dependency

## 3.0.1 / 2019-10-12

(Thanks to Steffen Deusch for most of the fixes.)

- #149: Improve performance for Windows File Explorer by updating cheroot to 8.1
- Fix #152: "Allow-Ranges: bytes" is now correct "Accept-Ranges: bytes" header
- Merge #155: last_modified is now correctly cast to int when comparing conditional requests
- Merge #156: the file object returned by get_content (DAVNonCollection) is now correctly being closed when a client disconnects unexpectedly
- Merge #158: add ssl support for gevent
- #159: Display requested path with 404 errors
- Fix #164: Wrong separator on Allow values

## 3.0.0 / 2019-03-04

This release contains **BREAKING CHANGES!**

- Improve configuration:<br>
  [(See details)](http://wsgidav.readthedocs.io/en/latest/user_guide_configure.html)
  - **Rename some options**, e.g. `acceptDigest` => `http_authenticator.accept_digest`
  - WsgiDAVApp constructor now assumes default settings. The passed options
    override those.
  - Log format is configurable
  - Remove option `dir_browser.enabled` (modify `middleware_stack` instead)
  - CLI supports `--server=gevent` (gevent must be installed separately)
  - SSL paths are evaluated relative to the config file, if any
  - Refactor middleware stack
    - RequestResolver and WsgiDavDirBrowser are now simple members of `middleware_stack`
      and not specially treated
    - `middleware_stack` entries can also be strings or dicts that are
      evaluated to import and instantiate middleware classes. This allows to
      define and configure external middleware in YAML and JSON config files.
  - provider_mapping option now supports configuration of custom providers
  - Windows XP (Microsoft-WebDAV-MiniRedir/5.1.2600) had a bug
    when accessing a share '/dav/': XP sometimes sends digests for '/'.
    In v.2.4 a hotfix was also accept '/' instead of the real share.
    This is now disabled by default, but can be re-enabled with
    hotfixes.winxp_accept_root_share_login: true.
- Refactor code base:
  - **Rename methods** according to PEP 8, e.g.
    `provider.getResourceInst()` => `provider.get_resource_inst()`.
  - **Rename methods arguments** according to PEP 8, e.g.
    `provider.set_last_modified(self, destPath, timeStamp, dryRun)`
    => `provider.set_last_modified(self, dest_path, time_stamp, dry_run)`
  - Enforce [Black code style](https://github.com/ambv/black)
  - Move some modules to separate packages
  - Use utf-8 directive in source files (-_- coding: utf-8 -_-)
- Refactor domain_controller and authentication:
  - Renamed environ["http_authenticator.realm"], environ["http_authenticator.user_name"]
    => environ["wsgidav.auth.realm"], environ["wsgidav.auth.user_name"]
  - DC may define environ["wsgidav.auth.roles"] and environ["wsgidav.auth.permissions"]
  - A common base class simplifies implementation of custom DCs.
  - New [PAMDomainController](https://en.wikipedia.org/wiki/Pluggable_authentication_module)
    allows to authenticate system users on Linux and macOS, for example.
  - Digest hash generation is now delegated to DomainControllers. This allows
    to implement DomainControllers that support digest access authentication
    even if plain-text passwords are not accessible, but stored hashes are.
  - Every domain controller now has a config section of its own. E.g.
    the `user_mapping` option for `SimpleDomainController` was moved to
    `simple_dc.user_mapping`.
- `SimpleDomainController` no longer allows anonymous access by default.
  It is now required to pass `simple_dc.user_mapping: "share1": True`.
  Also a new pseudo-share `"*"` can be used to define defaults.
  A new command line option `--auth` allows quick-configuration of DCs
- Refactor WsgiDirBrowser:
  - Use Jinja2 and load static assets through own WsgiDAV provider
  - Move to `wsgidav.dir_browser` package
  - Option 'dir_browser.ms_sharepoint_support' replaces ms_sharepoint_plugin and ms_sharepoint_urls
- Automated [Docker builds](https://hub.docker.com/r/mar10/wsgidav/)
- MSI installer
  - uses Cheroot/6.4 Python 3.6
  - Includes NTDomainController
- #112: Added limited support for Microsoft's Win32LastModified property.
- Fix #123: HEAD request on DirBrowser folder
- Fix #141: issue when 'sys.stdout' is none

## 2.4.1 / 2018-06-16

- Fix some logging exceptions
- Fix exception in CLI config reader (Py2)

## 2.4.0 / 2018-05-30

- Improve configuration files:
  - YAML is now the preferred configuration file format.
  - Add support for JSON config files (JavaScript-style comments allowed) (#89)
  - Use wsgidav.yaml, wsgidav.json, or wsgidav.conf by default if they exist in the local folder
- Expand '~' in `--root` and `--config` command line options
- #97: Fix assumption that QUERY_STRING is in environment (dir_browser)
- #99: Fix virtual_dav_provider for Py3: WSGI expects binary instead of str
- #100: Send ETags with PUT response
- #101: Fail cleanly if trying to PUT to unknown collection
- Refactor logging:
  - Re-define verbosity level range: 0..5
  - Remove usage of `print` in favor of `logging.getLogger().debug`
  - Remove util.note(), .status(), ... helpers
- Refactor code base:
  - Use `.format()` syntax instead of `%s` for string templating
  - Mandatory PEP 8 compliance (checked by flake8)
- Rework documentation on Read The Docs
- MSI setup uses Cheroot version 6.2+

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
  Set to 'pyopenssl' to use an existing OpenSSL installation.
  (Note: Currently broken as of Cheroot 5.1, see cherrypy/cheroot#6)
- Deprecate cherrypy.wsgiserver.<br>
  `--server=cherrypy` was renamed to `--server=cherrypy-wsgiserver`
- #64: Fix LOCK without owner
- #65: Add lxml to MSI installer
- Release as Wheel

## 2.1.0 / 2016-11-13

- #42: Remove some print usage in favor of logging (Sergi Almacellas Abellana)
- #43: PEP 8 fixes (Sergi Almacellas Abellana, Tom Viner)
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

- Using HTTP/1.1 with keep-alive (Stéphane Kein)
- Correctly return pre- and postconditions on lock conflicts.
- Added Sphinx docs
- Added Mercurial provider
- Changed configuration: no property manager used by default

## Until 0.4.0 alpha

See https://github.com/mar10/wsgidav/blob/master/docs/source/changelog04.md
