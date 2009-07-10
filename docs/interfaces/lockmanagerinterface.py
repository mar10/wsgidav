
class LockManagerInterface(object):
   """
   This class is an interface for a LockManager. Implementations for the lock manager
   in PyFileServer include::
      
      pyfileserver.locklibrary.LockManager
      
   All methods must be implemented.
   
   The url variable in methods refers to the relative URL of a resource. e.g. the 
   resource http://server/share1/dir1/dir2/file3.txt would have a url of 
   '/share1/dir1/dir2/file3.txt'
   """

   def generateLock(self, username, locktype, lockscope, lockdepth, lockowner, lockheadurl, timeout):
      """
      returns a new locktoken for the following lock:
         username - username of user performing the lock
         locktype - only the locktype "write" is defined in the webdav specification
         lockscope - "shared" or "exclusive"
         lockdepth - depth of lock. "0" or "infinity"
         lockowner - a arbitrary field provided by the client at lock time
         lockheadurl - the url the lock is being performed on
         timeout - -1 for infinite, positive value for number of seconds. 
                   Could be None, fall back to a default.   
      """
   
   def deleteLock(self, locktoken):
      """
      deletes a lock specified by locktoken
      """

   def isTokenLockedByUser(self, locktoken, username):
      """
      returns True if locktoken corresponds to a lock locked by username
      """

   def isUrlLocked(self, url):
      """
      returns True if the resource at url is locked
      """

   def getUrlLockScope(self, url):
      """
      returns the lockscope of all locks on url. 'shared' or 'exclusive'
      """

   def getLockProperty(self, locktoken, lockproperty):
      """
      returns the value for the following properties for the lock specified by
      locktoken:
         'LOCKUSER', 'LOCKTYPE', 'LOCKSCOPE', 'LOCKDEPTH', 'LOCKOWNER', 'LOCKHEADURL'
         and 
         'LOCKTIME' - number of seconds left on the lock.      
      """

   def isUrlLockedByToken(self, url, locktoken):
      """
      returns True if the resource at url is locked by lock specified by locktoken
      """

   def getTokenListForUrl(self, url):
      """
      returns a list of locktokens corresponding to locks on url.
      """

   def getTokenListForUrlByUser(self, url, username):
      """
      returns a list of locktokens corresponding to locks on url by user username.
      """

   def addUrlToLock(self, url, locktoken):
      """
      adds url to be locked by lock specified by locktoken.
      
      more than one url can be locked by a lock - depth infinity locks.
      """

   def removeAllLocksFromUrl(self, url):
      """
      removes all locks from a url.
      
      This usually happens when the resource specified by url is being deleted.
      """

   def refreshLock(self, locktoken, timeout):
      """
      refreshes the lock specified by locktoken.
      
      timeout : -1 for infinite, positive value for number of seconds. 
                Could be None, fall back to a default.      
      """