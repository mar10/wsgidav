"""
pyfiledomaincontroller
======================

:Module: pyfileserver.pyfiledomaincontroller
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

This module is specific to the PyFileServer application.

The PyFileServerDomainController fulfills the requirements of a 
DomainController as used for authentication with 
httpauthentication.HTTPAuthenticator for the PyFileServer application

Domain Controllers must provide the methods as described in 
domaincontrollerinterface_

.. _domaincontrollerinterface : interfaces/domaincontrollerinterface.py


See requestresolver.py for more information about user mappings in 
PyFileServer

"""
__docformat__ = 'reStructuredText'

class PyFileServerDomainController(object):
    def __init__(self):
        pass
           
    def getDomainRealm(self, inputURL, environ):
        # we don't get the realm here, its already been resolved in requestresolve 
        return environ['pyfileserver.mappedrealm']   


    def requireAuthentication(self, realmname, environ):
        return realmname in environ['pyfileserver.config']['user_mapping']
    
    def isRealmUser(self, realmname, username, environ):
        if realmname in environ['pyfileserver.config']['user_mapping']:
            return username in environ['pyfileserver.config']['user_mapping'][realmname]
        else:
            return False
            
    def getRealmUserPassword(self, realmname, username, environ):
        if realmname in environ['pyfileserver.config']['user_mapping']:
            if username in environ['pyfileserver.config']['user_mapping'][realmname]:
               return environ['pyfileserver.config']['user_mapping'][realmname][username]
            else:
               return None
        else:
            return None
      
    def authDomainUser(self, realmname, username, password, environ):
        if realmname in environ['pyfileserver.config']['user_mapping']:
            if username in environ['pyfileserver.config']['user_mapping'][realmname]:
                if environ['pyfileserver.config']['user_mapping'][realmname][username] == password:
                    return True
            return False
        else:
            return True
            