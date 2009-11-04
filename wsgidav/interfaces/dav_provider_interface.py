class IDAVProvider(object):
    """
    +----------------------------------------------------------------------+
    | TODO: document this interface                                        |
    | For now, see wsgidav.DAVProvider instead.                            |
    +----------------------------------------------------------------------+ 

    This class is an interface for a WebDAV provider.
    Implementations in WsgiDAV include::
      
        wsgidav.DAVProvider  (abstract base class)
        wsgidav.fs_dav_provider.ReadOnlyFilesystemProvider
        wsgidav.fs_dav_provider.FilesystemProvider
        wsgidav.addons.mysql_dav_provider.MySQLBrowserProvider
        wsgidav.addons.VirtualResourceProvider
      
    All methods must be implemented.
   
    """
