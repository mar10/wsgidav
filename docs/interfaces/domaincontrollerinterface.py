class DomainControllerInterface(object):
   """
   This class is an interface for a PropertyManager. Implementations for the 
   property manager in PyFileServer include::
      
      pyfileserver.pyfiledomaincontroller.PyFileServerDomainController
      pyfileserver.addons.windowsdomaincontroller.SimpleWindowsDomainController
      
   All methods must be implemented.
   
   The environ variable here is the WSGI 'environ' dictionary. It is passed to 
   all methods of the domain controller as a means for developers to pass information
   from previous middleware or server config (if required).
   """


   """
   Domain Controllers
   ------------------
   
   The HTTP basic and digest authentication schemes are based on the following 
   concept:
   
   Each requested relative URI can be resolved to a realm for authentication, 
   for example:
   /fac_eng/courses/ee5903/timetable.pdf -> might resolve to realm 'Engineering General'
   /fac_eng/examsolns/ee5903/thisyearssolns.pdf -> might resolve to realm 'Engineering Lecturers'
   /med_sci/courses/m500/surgery.htm -> might resolve to realm 'Medical Sciences General'
   and each realm would have a set of username and password pairs that would 
   allow access to the resource.
   
   A domain controller provides this information to the HTTPAuthenticator. 
   """

   def getDomainRealm(self, inputURL, environ):
      """
      resolves a relative url to the  appropriate realm name      
      """

   def requireAuthentication(self, realmname, environ):
      """
      returns True if this realm requires authentication 
      or False if it is available for general access
      """

   def isRealmUser(self, realmname, username, environ):
      """
      returns True if this username is valid for the realm, False otherwise
      """

   def getRealmUserPassword(self, realmname, username, environ):
      """
      returns the password for the given username for the realm. 
      Used for digest authentication.
      """

   def authDomainUser(self, realmname, username, password, environ):
      """
      returns True if this username/password pair is valid for the realm, 
      False otherwise. Used for basic authentication.
      """