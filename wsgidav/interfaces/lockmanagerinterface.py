class LockManagerInterface(object):
    """
    +----------------------------------------------------------------------+
    | TODO: document this interface                                        |
    | For now, see wsgidav.lock_manager instead                            |
    +----------------------------------------------------------------------+ 

    This class is an interface for a LockManager.
    Implementations for the lock manager in WsgiDAV include::
      
        wsgidav.lock_manager.LockManager
        wsgidav.lock_manager.ShelveLockManager
      
    All methods must be implemented.
   
    The url variable in methods refers to the relative URL of a resource. e.g. the 
    resource http://server/share1/dir1/dir2/file3.txt would have a url of 
    '/share1/dir1/dir2/file3.txt'
    """
