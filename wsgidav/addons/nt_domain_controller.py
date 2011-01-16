# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a domain controller that allows users to authenticate against 
a Windows NT domain or a local computer (used by HTTPAuthenticator).

Purpose
-------

Usage::
   
   from wsgidav.addons.nt_domain_controller import NTDomainController
   domaincontroller = NTDomainController(presetdomain=None, presetserver=None)
   
where: 

+ domaincontroller object corresponds to that in ``wsgidav.conf`` or
  as input into ``wsgidav.http_authenticator.HTTPAuthenticator``.

+ presetdomain allows the admin to specify a domain to be used (instead of any domain that
  may come as part of the username in domain\\user). This is useful only if there
  is one domain to be authenticated against and you want to spare users from typing the
  domain name
  
+ presetserver allows the admin to specify the NETBIOS name of the domain controller to
  be used (complete with the preceding \\\\). if absent, it will look for trusted 
  domain controllers on the localhost.

This class allows the user to authenticate against a Windows NT domain or a local computer,
requires NT or beyond (2000, XP, 2003, etc).

This class requires Mark Hammond's Win32 extensions for Python at here_ or sourceforge_

.. _here : http://starship.python.net/crew/mhammond/win32/Downloads.html
.. _sourceforge : http://sourceforge.net/projects/pywin32/

Information on Win32 network authentication was from the following resources:

+ http://ejabberd.jabber.ru/node/55

+ http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/81402


Testability and caveats
-----------------------

**Digest Authentication**
   Digest authentication requires the password to be retrieve from the system to compute
   the correct digest for comparison. This is so far impossible (and indeed would be a 
   big security loophole if it was allowed), so digest authentication WILL not work
   with this class. 
   
   Highly recommend basic authentication over SSL support.

**User Login**
   Authentication will count as a user login attempt, so any security in place for
   invalid password attempts may be triggered.
   
   Also note that, even though the user is logged in, the application does not impersonate
   the user - the application will continue to run under the account and permissions it
   started with. The user has the read/write permissions to the share of the running account 
   and not his own account.

**Using on a local computer**
   This class has been tested on a local computer (Windows XP). Leave domain as None and
   do not specify domain when entering username in this case.

**Using for a network domain**
   This class is being tested for a network domain (I'm setting one up to test).

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://docs.wsgidav.googlecode.com/hg/html/develop.html  
"""
from wsgidav import util

import win32net    #@UnresolvedImport
import win32security #@UnresolvedImport
import win32netcon #@UnresolvedImport

__docformat__ = "reStructuredText"
_logger = util.getModuleLogger(__name__)


class NTDomainController(object):
      
    def __init__(self, presetdomain = None, presetserver = None):
        self._presetdomain = presetdomain
        self._presetserver = presetserver


    def __repr__(self):
        return self.__class__.__name__


    def getDomainRealm(self, inputURL, environ):
        return "Windows Domain Authentication"


    def requireAuthentication(self, realmname, environ):
        return True

                    
    def isRealmUser(self, realmname, username, environ):
        (domain, usern) = self._getDomainUsername(username)
        dcname = self._getDomainControllerName(domain)
        return self._isUser(usern, domain, dcname)

            
    def getRealmUserPassword(self, realmname, username, environ):
        (domain, user) = self._getDomainUsername(username)
        dcname = self._getDomainControllerName(domain)
        
        try: 
            userdata = win32net.NetUserGetInfo(dcname, user, 1)
        except:
            _logger.exception("NetUserGetInfo")
            userdata = {}
#        if "password" in userdata:
#            if userdata["password"] != None:
#                return userdata["password"]
#        return None
        return userdata.get("password")

      
    def authDomainUser(self, realmname, username, password, environ):
        (domain, usern) = self._getDomainUsername(username)
        dcname = self._getDomainControllerName(domain)
        return self._authUser(usern, password, domain, dcname)


    def _getDomainUsername(self, inusername):
        userdata = inusername.split("\\", 1)
        if len(userdata) == 1:
            domain = None
            username = userdata[0]
        else:
            domain = userdata[0]
            username = userdata[1]
        
        if self._presetdomain != None:
            domain = self._presetdomain

        return (domain, username)


    def _getDomainControllerName(self, domain):
        if self._presetserver != None:
            return self._presetserver
        
        try:
            # execute this on the localhost
            pdc = win32net.NetGetAnyDCName(None, domain)
        except:
            pdc = None
        
        return pdc


    def _isUser(self, username, domain, server):
        resume = "init"
        while resume:
            if resume == "init":
                resume = 0
            try:
                users, _total, resume = win32net.NetUserEnum(server, 0, win32netcon.FILTER_NORMAL_ACCOUNT, 0)
                # Make sure, we compare unicode
                un = username.decode("utf8").lower()
                for userinfo in users:
                    uiname = userinfo.get("name")
                    assert uiname
                    assert isinstance(uiname, unicode)
                    if un == userinfo["name"].lower():
                        return True
            except win32net.error, e:
                _logger.exception("NetUserEnum: %s" % e)
                return False
        _logger.info("User '%s' not found on server '%s'" % (username, server))
        return False
        

    def _authUser(self, username, password, domain, server):
        if not self._isUser(username, domain, server):
            return False
        
        try:
            htoken = win32security.LogonUser(username, domain, password, win32security.LOGON32_LOGON_NETWORK, win32security.LOGON32_PROVIDER_DEFAULT)
        except win32security.error, err:
            _logger.warning("LogonUser failed for user '%s': %s" % (username, err))
            return False
        else:
            if htoken: 
                htoken.Close() #guarantee's cleanup
                _logger.debug("User '%s' logged on." % username)
                return True
            _logger.warning("Logon failed for user '%s'." % username)
            return False    
