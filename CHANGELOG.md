=======
CHANGES
=======

2.0.0 / Unreleased
==================
- #2: Support Python 3
- Drop support for Python 2.6
- Use py.test & tox


1.3.0 / 2016-08-24
==================
- #19: Add option `mutable_live_props` to support setting last modified file/directory timestamps
  (Jonas Bardino)
- #23: Fix Windows file manager and OSX Finder fails on file names with comma (Jonas Bardino)
- #27: Do not install tests (Erich Seifert)
- #28: New option `trusted_auth_header` allows reverse proxy authentication (Mageti)
- #30: API change to allow much easier per-user chrooting (Jonas Bardino)
- #32: Fix digest authentication rejected due to invalid header (Adrian Crețu)


1.2.0 / 2015-05-14
==================
- #8: Unquote PATH_INFO is now optional 'unquote_path_info'; defaults to false.
  (Brian Sipos)
- #9: Fixed status codes for apache mod_wsgi (Brian Sipos)
- #10: Hotfix for file copy on GVFS (Brian Sipos)
- #12: Configurable middleware stack (Pavel Shiryaev)
- #15: Fix Finder access (Jonas Bardino)


1.1.0 / 2014-01-01
==================
- New dir_browser option 'ms_sharepoint_plugin' to start MS Office documents in edit-mode
- Moved project from Google Code to GitHub
- Moved documentation to ReadTheDocs


1.0.0 / 2013-12-27
==================
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


0.5.0 / 2011-01-16
==================
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


0.4.0.b3
========
- Refactored LockManager. using separate LockStorage
- Bugfixes


0.4.0.b2 / 2010-02-15
=====================
- Bugfixes


0.4.0.b1
========
- Using HTTP/1.1 with keep-alive (St�phane KLEIN)
- Correctly return pre- and postconditions on lock conflicts.
- Added Sphinx docs
- Added Mercurial provider
- Changed configuration: no property manager used by default

Until 0.4.0 alpha
=================
See https://github.com/mar10/wsgidav/blob/master/doc/changelog04.md
