# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware for HTTP basic and digest authentication.

Usage::

   from http_authenticator import HTTPAuthenticator
   
   WSGIApp = HTTPAuthenticator(ProtectedWSGIApp, domain_controller, acceptbasic,
                               acceptdigest, defaultdigest)

   where:
     ProtectedWSGIApp is the application requiring authenticated access
     
     domain_controller is a domain controller object meeting specific 
     requirements (below)
     
     acceptbasic is a boolean indicating whether to accept requests using
     the basic authentication scheme (default = True)
     
     acceptdigest is a boolean indicating whether to accept requests using
     the digest authentication scheme (default = True)
     
     defaultdigest is a boolean. if True, an unauthenticated request will 
     be sent a digest authentication required response, else the unauthenticated 
     request will be sent a basic authentication required response 
     (default = True)

The HTTPAuthenticator will put the following authenticated information in the 
environ dictionary::
   
   environ["http_authenticator.realm"] = realm name
   environ["http_authenticator.username"] = username
   

**Domain Controllers**

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
This allows developers to write their own domain controllers, that might,
for example, interface with their own user database.

for simple applications, a SimpleDomainController is provided that will take
in a single realm name (for display) and a single dictionary of username (key)
and password (value) string pairs 

Usage::

   from http_authenticator import SimpleDomainController
   users = dict(({'John Smith': 'YouNeverGuessMe', 'Dan Brown': 'DontGuessMeEither'})
   realm = 'Sample Realm'
   domain_controller = SimpleDomainController(users, realm)


Domain Controllers must provide the methods as described in 
``wsgidav.interfaces.domaincontrollerinterface`` (interface_)

.. _interface : interfaces/domaincontrollerinterface.py

The environ variable here is the WSGI 'environ' dictionary. It is passed to 
all methods of the domain controller as a means for developers to pass information
from previous middleware or server config (if required).

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://docs.wsgidav.googlecode.com/hg/html/develop.html  
"""
__docformat__ = "reStructuredText"

import random
import base64
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import time
import re
import util

_logger = util.getModuleLogger(__name__, True)

# HOTFIX for Windows XP (Microsoft-WebDAV-MiniRedir/5.1.2600):
# When accessing a share '/dav/', XP sometimes sends digests for '/'.
# With this fix turned on, we allow '/' digests, when a matching '/dav' account
# is present. 
HOTFIX_WINXP_AcceptRootShareLogin = True


class SimpleDomainController(object):
    """SimpleDomainController : Simple domain controller for HTTPAuthenticator."""
    def __init__(self, dictusers = None, realmname = "SimpleDomain"):
        if dictusers is None:
            self._users = dict({"John Smith": "YouNeverGuessMe"})
        else:
            self._users = dictusers
        self._realmname = realmname
           
    def getDomainRealm(self, inputRelativeURL, environ):
        return self._realmname 
    
    def requireAuthentication(self, realmname, environ):
        return True
    
    def isRealmUser(self, realmname, username, environ):
        return username in self._users
            
    def getRealmUserPassword(self, realmname, username, environ):
        if username in self._users:
            return self._users[username]
        return None
            
    def authDomainUser(self, realmname, username, password, environ):
        if username in self._users:
            return self._users[username] == password
        return False        
              
       
#===============================================================================
# HTTPAuthenticator
#===============================================================================
class HTTPAuthenticator(object):
    """WSGI Middleware for basic and digest authenticator."""
    def __init__(self, application, domaincontroller, acceptbasic=True, acceptdigest=True, defaultdigest=True):
        self._domaincontroller = domaincontroller
        self._application = application
        self._noncedict = dict([])

        self._headerparser = re.compile(r"([\w]+)=([^,]*),")
        self._headermethod = re.compile(r"^([\w]+)")
        
        self._acceptbasic = acceptbasic
        self._acceptdigest = acceptdigest
        self._defaultdigest = defaultdigest

   
    def __call__(self, environ, start_response):
        realmname = self._domaincontroller.getDomainRealm(environ["PATH_INFO"], environ)
        
        if not self._domaincontroller.requireAuthentication(realmname, environ):
            # no authentication needed
            _logger.debug("No authorization required for realm '%s'" % realmname)
            environ["http_authenticator.realm"] = realmname
            environ["http_authenticator.username"] = ""
            return self._application(environ, start_response)
        
        if "HTTP_AUTHORIZATION" in environ:
            authheader = environ["HTTP_AUTHORIZATION"] 
            authmatch = self._headermethod.search(authheader)          
            authmethod = "None"
            if authmatch:
                authmethod = authmatch.group(1).lower()
                
            if authmethod == "digest" and self._acceptdigest:
                return self.authDigestAuthRequest(environ, start_response)
            elif authmethod == "digest" and self._acceptbasic:
                return self.sendBasicAuthResponse(environ, start_response)
            elif authmethod == "basic" and self._acceptbasic:
                return self.authBasicAuthRequest(environ, start_response)

            util.log("HTTPAuthenticator: respond with 400 Bad request; Auth-Method: %s" % authmethod)
            
            start_response("400 Bad Request", [("Content-Length", "0"),
                                               ("Date", util.getRfc1123Time()),
                                               ])
            return [""]
        
                                   
        if self._defaultdigest:
            return self.sendDigestAuthResponse(environ, start_response)
        return self.sendBasicAuthResponse(environ, start_response)


    def sendBasicAuthResponse(self, environ, start_response):
        realmname = self._domaincontroller.getDomainRealm(environ["PATH_INFO"] , environ)
        _logger.debug("401 Not Authorized for realm '%s' (basic)" % realmname)
        wwwauthheaders = "Basic realm=\"" + realmname + "\"" 
        
        body = self.getErrorMessage()
        start_response("401 Not Authorized", [("WWW-Authenticate", wwwauthheaders),
                                              ("Content-Type", "text/html"),
                                              ("Content-Length", str(len(body))),
                                              ("Date", util.getRfc1123Time()),
                                              ])
        return [ body ]


    def authBasicAuthRequest(self, environ, start_response):
        realmname = self._domaincontroller.getDomainRealm(environ["PATH_INFO"] , environ)
        authheader = environ["HTTP_AUTHORIZATION"]
        authvalue = ""
        try:
            authvalue = authheader[len("Basic "):]
        except:
            authvalue = ""
        authvalue = authvalue.strip().decode("base64")
        username, password = authvalue.split(":",1)
        
        if self._domaincontroller.authDomainUser(realmname, username, password, environ):
            environ["http_authenticator.realm"] = realmname
            environ["http_authenticator.username"] = username
            return self._application(environ, start_response)
        return self.sendBasicAuthResponse(environ, start_response)
        

    def sendDigestAuthResponse(self, environ, start_response):    
        realmname = self._domaincontroller.getDomainRealm(environ["PATH_INFO"] , environ)
        random.seed()
        serverkey = hex(random.getrandbits(32))[2:]
        etagkey = md5(environ["PATH_INFO"]).hexdigest()
        timekey = str(time.time())  
        nonce = base64.b64encode(timekey + md5(timekey + ":" + etagkey + ":" + serverkey).hexdigest())
        wwwauthheaders = "Digest realm=\"" + realmname + "\", nonce=\"" + nonce + \
            "\", algorithm=\"MD5\", qop=\"auth\""                 
        _logger.debug("401 Not Authorized for realm '%s' (digest): %s" % (realmname, wwwauthheaders))

        body = self.getErrorMessage()
#        start_response("403 Forbidden", [("WWW-Authenticate", wwwauthheaders),
        start_response("401 Not Authorized", [("WWW-Authenticate", wwwauthheaders),
                                              ("Content-Type", "text/html"),
                                              ("Content-Length", str(len(body))),
                                              ("Date", util.getRfc1123Time()),
                                              ])
        return [ body ]
        

    def authDigestAuthRequest(self, environ, start_response):  

        realmname = self._domaincontroller.getDomainRealm(environ["PATH_INFO"] , environ)
        
        isinvalidreq = False
         
        authheaderdict = dict([])
        authheaders = environ["HTTP_AUTHORIZATION"] + ","
        if not authheaders.lower().strip().startswith("digest"):
            isinvalidreq = True
        authheaderlist = self._headerparser.findall(authheaders)
        for authheader in authheaderlist:
            authheaderkey = authheader[0]
            authheadervalue = authheader[1].strip().strip("\"")
            authheaderdict[authheaderkey] = authheadervalue

        _logger.debug("authDigestAuthRequest: %s" % environ["HTTP_AUTHORIZATION"])
        _logger.debug("  -> %s" % authheaderdict)
         
        if "username" in authheaderdict:
            req_username = authheaderdict["username"]
            req_username_org = req_username 
            # Hotfix for Windows XP:
            #   net use W: http://127.0.0.1/dav /USER:DOMAIN\tester tester
            # will send the name with double backslashes ('DOMAIN\\tester')
            # but send the digest for the simple name ('DOMAIN\tester').  
            if r"\\" in req_username:
                req_username = req_username.replace("\\\\", "\\")
                _logger.info("Fixing Windows name with double backslash: '%s' --> '%s'" % (req_username_org, req_username))

            if not self._domaincontroller.isRealmUser(realmname, req_username, environ):   
                isinvalidreq = True
        else:
            isinvalidreq = True

        # TODO: Chun added this comments, but code was commented out
        # Do not do realm checking - a hotfix for WinXP using some other realm's
        # auth details for this realm - if user/password match
#        print authheaderdict.get("realm"), realmname
        if 'realm' in authheaderdict:
            if authheaderdict["realm"].upper() != realmname.upper():
                if HOTFIX_WINXP_AcceptRootShareLogin:
                    # Hotfix: also accept '/'
                    if authheaderdict["realm"].upper() != "/":
                        isinvalidreq = True
                else:  
                    isinvalidreq = True
        
        if "algorithm" in authheaderdict:
            if authheaderdict["algorithm"].upper() != "MD5":
                isinvalidreq = True         # only MD5 supported
        
        if "uri" in authheaderdict:
            req_uri = authheaderdict["uri"]

        if "nonce" in authheaderdict:
            req_nonce = authheaderdict["nonce"]
        else:
            isinvalidreq = True

        req_hasqop = False
        if "qop" in authheaderdict:
            req_hasqop = True
            req_qop = authheaderdict["qop"]     
            if req_qop.lower() != "auth":
                isinvalidreq = True   # only auth supported, auth-int not supported        
        else:
            req_qop = None

        if "cnonce" in authheaderdict:
            req_cnonce = authheaderdict["cnonce"]
        else:
            req_cnonce = None
            if req_hasqop:
                isinvalidreq = True
         
        if "nc" in authheaderdict:    # is read but nonce-count checking not implemented
            req_nc = authheaderdict["nc"]
        else:
            req_nc = None
            if req_hasqop:
                isinvalidreq = True

        if "response" in authheaderdict:
            req_response = authheaderdict["response"]
        else:
            isinvalidreq = True
             
        if not isinvalidreq:
            req_password = self._domaincontroller.getRealmUserPassword(realmname, req_username, environ)

            req_method = environ["REQUEST_METHOD"]
            
            required_digest = self.computeDigestResponse(req_username, realmname, req_password, req_method, req_uri, req_nonce, req_cnonce, req_qop, req_nc)
            
            if required_digest != req_response:
                _logger.warning("computeDigestResponse('%s', '%s', ...): %s != %s" % (realmname, req_username, required_digest, req_response))
                if HOTFIX_WINXP_AcceptRootShareLogin:
                    # Hotfix: also accept '/' digest
                    root_digest = self.computeDigestResponse(req_username, "/", req_password, req_method, req_uri, req_nonce, req_cnonce, req_qop, req_nc)
                    if root_digest == req_response:
                        _logger.warning("authDigestAuthRequest: HOTFIX: accepting '/' login for '%s'." % realmname)
                    else:
                        isinvalidreq = True
                else:
                    isinvalidreq = True
            else:
#                _logger.debug("digest succeeded for realm '%s', user '%s'" % (realmname, req_username))
                pass

        if isinvalidreq:
            _logger.warning("Authentication failed for user '%s', realm '%s'" % (req_username, realmname))
            return self.sendDigestAuthResponse(environ, start_response)

        environ["http_authenticator.realm"] = realmname
        environ["http_authenticator.username"] = req_username
        return self._application(environ, start_response)                


    def computeDigestResponse(self, username, realm, password, method, uri, nonce, cnonce, qop, nc):
        A1 = username + ":" + realm + ":" + password
        A2 = method + ":" + uri
        if qop:
            digestresp = self.md5kd( self.md5h(A1), nonce + ":" + nc + ":" + cnonce + ":" + qop + ":" + self.md5h(A2))
        else:
            digestresp = self.md5kd( self.md5h(A1), nonce + ":" + self.md5h(A2))
        return digestresp
                
    
    def md5h(self, data):
        return md5(data).hexdigest()
        
    
    def md5kd(self, secret, data):
        return self.md5h(secret + ":" + data)

    
    def getErrorMessage(self):
        message = """\
<html><head><title>401 Access not authorized</title></head>
<body>
<h1>401 Access not authorized</h1>
</body>        
</html>        
        """
        return message
