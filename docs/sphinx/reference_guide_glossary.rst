Glossary
========

*This document defines some terms gives a brief introduction to the WsgiDAV application package
(targeted to developers).*

.. seealso::
   You can find more information about WebDAV terms and naming convention
   in `official WebDAV specification documentation <http://www.webdav.org/specs/rfc4918.html#rfc.section.3>`_.


You will find this terms / naming conventions in the source:


*URL*:
  In general URLs follow these rules:

  - Byte strings, using ISO-8859-1 encoding
  - Case sensitive
  - Quoted, i.e. special characters are escaped
  - Collections have a trailing '/'
    (but we also accept request URLs, that omit them.)

  When we use the term *URL* in WsgiDAV variables, we typically mean **absolute** URLs:
      ``/<mount>/<path>``
  When we use the term *full URL*, we typically mean **complete** URLs:
      ``http://<server>:<port>/<mount>/<path>``

  Constructed like
      fullUrl = util.makeCompleteURL(environ)
  Example
      "http://example.com:8080/dav/public/my%20nice%20doc.txt"


*Path* (in general):
  When we use the term *Path* in WsgiDAV variables, we typically mean
  **unquoted** URLs, relative to the *mount point*.

  Example
      "/public/my nice doc.txt"


*mount point* (also 'mount path', 'approot'):
  Unquoted, ISO-8859-1 encoded byte string.

  The application's mount point. Starts with a '/' (if not empty).

  This is the virtual directory, where the web server mounted the WsgiDAV
  application.
  So it is the environ[SCRIPT_NAME] that the server had set, before calling
  WsgiDAVApp.

  Example
      ""


*share path* (also 'share', 'domain'):
  Unquoted, ISO-8859-1 encoded byte string.

  The application's share path, relative to the mount point. Starts with a '/'
  (if not empty).

  For every request, WsgiDAVApp tries to find the registered provider for the
  URL (after the mount path was popped).
  The share path is the common URL prefix of this URL.

  TODO: do we need to ditinguish between server mount points ('mount path') and
  WsgiDAV mount points ('share path')?

  Constructed like
      mount_path = environ[SCRIPT_NAME]
  Example
      "/dav"


*realm*:
  Unquoted, ISO-8859-1 encoded byte string.

  The domain name, that a resource belongs to.

  This string is used for HTTP authentication.

  Each realm would have a set of username and password pairs that would allow
  access to the resources.

  Examples
      "Marketing Department"
      "Windows Domain Authentication"

  The ``dc.simple_dc.SimpleDomainController`` implementation uses the
  mount path as realm name.


*path*
  Unquoted, ISO-8859-1 encoded byte string.

  The resource URL, relative to the application's mount point.
  Starts with a '/'. Collections also should have a trailing '/'.

  Constructed like:
      path = environ[PATH_INFO]
  Examples:
      "/public/my nice doc.txt"
      "/public/"


*preferred path*:
  Unquoted, ISO-8859-1 encoded byte string.

  The preferred or normalized *path*.

  Depending on case sensitivity of the OS file system, all these paths
  may map to the same collection resource::

    /public/my folder/
    /public/my folder   (missing '/')
    /public/MY FOLDER/  (on a Windows server, which is not case sensitive)

  provider.get_preferred_path(path) will return::

    /public/my folder/

  for all of these variants.


*reference URL*:
  Quoted, UTF-8 encoded byte string.

  This is basically the same as an URL, that was build from the *preferred path*.
  But this deals with 'virtual locations' as well.

  Since it is always unique for one resource, <refUrl> is used as key for the
  lock- and property storage.

  A resource has always one 'real location' and may have 0..n 'virtual locations'.

  For example::

    /dav/public/my%20folder/file1.txt
    /dav/by_key/1234
    /dav/by_status/approved/file1.txt

  may map to the same resource, but only::

    /dav/by_key/1234

  is the refUrl.

  Constructed like:
      realUrl = quote(mount_path + reference path)
  Examples:
      "/dav/by_key/1234"


*href*:
  **Quoted**,  UTF-8 encoded byte string.

  Used in XML responses. We are using the path-absolute option. i.e. starting
  with '/'.  (See http://www.webdav.org/specs/rfc4918.html#rfc.section.8.3)

  Constructed like:
      href = quote(mount_path + preferredPath)
  Example:
      "/dav/public/my%20nice%20doc.txt"


*filePath*:
  Unicode

  Used by fs_dav_provider when serving files from the file system.
  (At least on Vista) os.path.exists(filePath) returns False, if a file name contains
  special characters, even if it is correctly UTF-8 encoded.
  So we convert to unicode.
