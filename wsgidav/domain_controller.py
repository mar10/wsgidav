"""
domain_controller
=================

:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Implementation of a domain controller that uses realm/username/password mappings
from the configuration file and uses the share path as realm name.

userMap is defined a follows::

    userMap = {'realm1': {
                 'John Smith': {'description': '', 
                                'password': 'YouNeverGuessMe',
                                },
                 'Dan Brown': {'description': '', 
                               'password': 'DontGuessMeEither',
                               },
                 }
               'realm2': { 
                 ... 
                 }
               }

The WsgiDAVDomainController fulfills the requirements of a DomainController as 
used for authentication with http_authenticator.HTTPAuthenticator for the 
WsgiDAV application.

Domain Controllers must provide the methods as described in 
domaincontrollerinterface_

.. _domaincontrollerinterface : interfaces/domaincontrollerinterface.py


See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
import sys
__docformat__ = "reStructuredText"

class WsgiDAVDomainController(object):

    def __init__(self, userMap):
        self.userMap = userMap
#        self.allowAnonymous = allowAnonymous
           

    def __repr__(self):
        return self.__class__.__name__


    def getDomainRealm(self, inputURL, environ):
        """Resolve a relative url to the  appropriate realm name."""
        # we don't get the realm here, its already been resolved in request_resolver
        davProvider = environ["wsgidav.provider"]
        if not davProvider:
            if environ["wsgidav.verbose"] >= 2:
                print >>sys.stderr, "getDomainRealm(%s): '%s'" %(inputURL, None)
            return None
        realm = davProvider.sharePath
        if realm == "":
            realm = "/"
#        if environ["wsgidav.verbose"] >= 2:
#            print >>sys.stderr, "getDomainRealm(%s): '%s'" %(inputURL, realm)
        return realm

    
    def requireAuthentication(self, realmname, environ):
        """Return True if this realm requires authentication or False if it is 
        available for general access."""
        # TODO: Should check for --allow_anonymous?
#        assert realmname in environ["wsgidav.config"]["user_mapping"], "Currently there must be at least on user mapping for this realm"
        return realmname in self.userMap
    
    
    def isRealmUser(self, realmname, username, environ):
        """Returns True if this username is valid for the realm, False otherwise."""
#        if environ["wsgidav.verbose"] >= 2:
#            print >>sys.stderr, "isRealmUser('%s', '%s'): %s" %(realmname, username, realmname in self.userMap and username in self.userMap[realmname])
        return realmname in self.userMap and username in self.userMap[realmname]
            
    
    def getRealmUserPassword(self, realmname, username, environ):
        """Return the password for the given username for the realm.
        
        Used for digest authentication.
        """
        return self.userMap.get(realmname, {}).get(username, {}).get("password")
      
    
    def authDomainUser(self, realmname, username, password, environ):
        """Returns True if this username/password pair is valid for the realm, 
        False otherwise. Used for basic authentication."""
        user = self.userMap.get(realmname, {}).get(username)
        return user is not None and password == user.get("password")
