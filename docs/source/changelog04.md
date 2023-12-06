#summary Main changes from PyFileServer to WsgiDAV.

# Introduction

WsgiDAV is a refactored version of [PyFileServer 0.2](https://github.com/cwho/pyfileserver),
Copyright (c) 2005 Ho Chun Wei.<br>
Chun gave his approval to change the license from LGPL to MIT-License for this project.

Below a list of main changes, I made during my initial refactoring.

The [commits of the alpha phase](http://code.google.com/p/wsgidav-dev/source/list) are still available.

Starting with 0.4 beta, changes are logged in the packages [CHANGE](http://code.google.com/p/wsgidav/source/browse/CHANGES) file.

## Main changes until 0.4.alpha

<ul>
<li>
Moved to Google Code and using MIT-License instead of LGPL (with Ho Chun Wei's agreement).

<li>
Fixed indentation.

<li>
Restructured package and renamend modules and classes.

<li>
Changed WSGI stack (see <a href="http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html">DEVELOPERS.txt).</a><br>
For example dir_browser is a separate middleware now.

<li>
Based on RFC 4918, June 2007 (which obsoletes RFC 2518)

<li>
Using SCRIPT_NAME and PATH_INFO instead of custom WSGI environment variables Environ["pyfileserver.mappedpath"], ...

<li>
!RequestResolver no longer serves OPTIONS and TRACE (now in !RequestServer).
Except for `OPTIONS (*)`.

<li>
!RequestServer is no longer a static part of the WSGI stack, but instantiated
dynamically by !RequestResolver.

<li>
Dropped PyXML. Instead using lxml (or xml) to parse requests.<br>
Using lxml.etree to build the responses.

<li>
Using Clark Notation throughout; no need to pass around namespace and name separately.

<li>
Refactored some DAV method handlers to be less deeply nested.

<li>
Server:<br>
New entry point 'run_server', using cherrypy, paste, wsgiref, if they are installed.<br>
Otherwise ext_wsgiutils_server is used (comes with the WsgiDAV package).

<li>
Added mount_path option and tested running WsgiDAV as a Pylons controller. (Stéphane Klein)

<li>
Converted interface to an abstract base class DAVProvider:
<pre>
   DAVProvider
     + ReadOnlyFilesystemProvider
       + FilesystemProvider
</pre>
Replaced separate query function with davprovider.getInfoDict()
This allows to request bundled information, which providers can implement more efficiently. Also an `DAVResource` object was introduced.

<li>
All DAV providers (aka resource abstraction layers) now use URIs with '/' instead of OS dependent file names.<br>
This allows for generic implementations like .getParent() and .iter() in the common base class.<br>
!FilesystemProvider has a new constructor argument: 'rootFolderPath', so it can perform the mapping from URI to absolute file path.

<li>
Changed configuration file format.
For example local file path is now an argument to !FilesystemProvider.<br>
User_map format changed.<br>
Also, the config file is optional, i.e. the server runs also with command line only.

<li>
Property manager<br>
Removed propertylibrary helper functions (only !PropManager class left).<br>
Add property functions to davProvider
getProperties() returns (name, value) tuples, where value is etree.Element
or HTTPRequestException().<br>
setPropertyValue() accepts str or etree.Element or None (for 'remove')<br>
Added 'dryRun' mode.<br>
Store native XML<br>

<li>
Lock manager<br>
Only storing lock root (not maintaining a list of locked resources).<br>
'getCheckLock' is atomic now.

<li>
!LockManager and !PropManager are now members of the DAV provider.<br>
Also, the displaypath is no longer passed around, since it always can be constructed by provider.getNormUri()

<li>
Added in-memory versions of !LockManager and !PropManager.
Renamed the original shelve-based variants to !ShelveLockManager and !ShelvePropManager.

<li>
Support for `&lt;error&gt;` Tag and Pre-/Postcondition codes.
Also  `&lt;resultdescription&gt;`

<li>
easy_install'able

<li>
Added API documentation (epidoc)

<li>
Added unit tests

<li>
Chunked PUT action support (Stéphane Klein)

<li>
Improved console logging

<li>
Added a WebDAV provider for Mercurial repositories (experimental)

<li>
Added a sample WebDAV provider for generich virtual structures
