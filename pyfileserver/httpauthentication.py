"""
httpauthentication
==================

:Module: pyfileserver.httpauthentication
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

WSGI middleware for HTTP basic and digest authentication.

Usage::
   from httpauthentication import HTTPAuthenticator
   
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
     be sent a digest authentication required response, else the unathenticated 
     request will be sent a basic authentication required response 
     (default = True)

The HTTPAuthenticator will put the following authenticated information in the 
environ dictionary::
   
   environ['httpauthentication.realm'] = realm name
   environ['httpauthentication.username'] = username
   

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
This allows developers to write their own domain controllers, that might,
for example, interface with their own user database.

for simple applications, a SimpleDomainController is provided that will take
in a single realm name (for display) and a single dictionary of username (key)
and password (value) string pairs 

Usage::
   from httpauthentication import SimpleDomainController
   users = dict(({'John Smith': 'YouNeverGuessMe', 'Dan Brown': 'DontGuessMeEither'})
   realm = 'Sample Realm'
   domain_controller = SimpleDomainController(users, realm)


Domain Controllers must provide the methods as described in 
``pyfileserver.interfaces.domaincontrollerinterface`` (interface_)

.. _interface : interfaces/domaincontrollerinterface.py

The environ variable here is the WSGI 'environ' dictionary. It is passed to 
all methods of the domain controller as a means for developers to pass information
from previous middleware or server config (if required).


Interface
---------

Classes

+ HTTPAuthenticator : WSGI Middleware for basic and digest authenticator.

+ SimpleDomainController : Simple domain controller for HTTPAuthenticator.

"""
__docformat__ = 'reStructuredText'

import random
import base64
import md5
import time
import re

class SimpleDomainController(object):
    def __init__(self, dictusers = None, realmname = 'SimpleDomain'):
        if dictusers is None:
            self._users = dict({'John Smith': 'YouNeverGuessMe'})
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
        else:
            return None
            
    def authRealmUser(self, realmname, username, password, environ):
        if username in self._users:
            return self._users[username] == password
        else:
            return False        
              
       
class HTTPAuthenticator(object):

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
        realmname = self._domaincontroller.getDomainRealm(environ['PATH_INFO'], environ)
        if not self._domaincontroller.requireAuthentication(realmname, environ):       # no authentication needed
            environ['httpauthentication.realm'] = realmname
            environ['httpauthentication.username'] = ''
            return self._application(environ, start_response)
        
        if 'HTTP_AUTHORIZATION' in environ:
            authheader = environ['HTTP_AUTHORIZATION'] 
            authmatch = self._headermethod.search(authheader)          
            authmethod = "None"
            if authmatch:
                authmethod = authmatch.group(1).lower()
            if authmethod == 'digest' and self._acceptdigest:
                return self.authDigestAuthRequest(environ, start_response)
            elif authmethod == 'basic' and self._acceptbasic:
                return self.authBasicAuthRequest(environ, start_response)
            else:
                start_response("400 Bad Request", [('Content-Length', 0)])
                return ['']                           
        else:
            if self._defaultdigest:
                return self.sendDigestAuthResponse(environ, start_response)
            else:
                return self.sendBasicAuthResponse(environ, start_response)

        return ['']        

    def sendBasicAuthResponse(self, environ, start_response):
        realmname = self._domaincontroller.getDomainRealm(environ['PATH_INFO'] , environ)
        wwwauthheaders = "Basic realm=\"" + realmname + "\"" 
        start_response("401 Not Authorized", [('WWW-Authenticate', wwwauthheaders)])
        return [self.getErrorMessage()]

    def authBasicAuthRequest(self, environ, start_response):
        realmname = self._domaincontroller.getDomainRealm(environ['PATH_INFO'] , environ)
        authheader = environ['HTTP_AUTHORIZATION']
        authvalue = ''
        try:
            authvalue = authheader[len("Basic "):]
        except:
            authvalue = ''
        authvalue = authvalue.strip().decode('base64')
        username, password = authvalue.split(':',1)
        
        if self._domaincontroller.authRealmUser(realmname, username, password, environ):
            environ['httpauthentication.realm'] = realmname
            environ['httpauthentication.username'] = username
            return self._application(environ, start_response)
        else:
            return self.sendBasicAuthResponse(environ, start_response)
        
    def sendDigestAuthResponse(self, environ, start_response):    
        realmname = self._domaincontroller.getDomainRealm(environ['PATH_INFO'] , environ)
        random.seed()
        serverkey = hex(random.getrandbits(32))[2:]
        etagkey = md5.new(environ['PATH_INFO']).hexdigest()
        timekey = str(time.time())  
        nonce = base64.b64encode(timekey + md5.new(timekey + ":" + etagkey + ":" + serverkey).hexdigest())
        wwwauthheaders = "Digest realm=\"" + realmname + "\", nonce=\"" + nonce + \
            "\", algorithm=\"MD5\", qop=\"auth\""                 
        start_response("401 Not Authorized", [('WWW-Authenticate', wwwauthheaders)])
        return [self.getErrorMessage()]
        
    def authDigestAuthRequest(self, environ, start_response):  

        realmname = self._domaincontroller.getDomainRealm(environ['PATH_INFO'] , environ)
        
        isinvalidreq = False
         
        authheaderdict = dict([])
        authheaders = environ['HTTP_AUTHORIZATION'] + ','
        if not authheaders.lower().strip().startswith("digest"):
            isinvalidreq = True
        authheaderlist = self._headerparser.findall(authheaders)
        for authheader in authheaderlist:
            authheaderkey = authheader[0]
            authheadervalue = authheader[1].strip().strip("\"")
            authheaderdict[authheaderkey] = authheadervalue
         
        if 'username' in authheaderdict:
            req_username = authheaderdict['username']
            if not self._domaincontroller.isRealmUser(realmname, req_username, environ):   
                isinvalidreq = True
        else:
            isinvalidreq = True

        # Do not do realm checking - a hotfix for WinXP using some other realm's
        # auth details for this realm - if user/password match
        #if 'realm' in authheaderdict:
        #    if authheaderdict['realm'].upper() != realmname.upper():
        #        isinvalidreq = True
        
        if 'algorithm' in authheaderdict:
            if authheaderdict['algorithm'].upper() != "MD5":
                isinvalidreq = True         # only MD5 supported
        
        if 'uri' in authheaderdict:
            req_uri = authheaderdict['uri']

        if 'nonce' in authheaderdict:
            req_nonce = authheaderdict['nonce']
        else:
            isinvalidreq = True

        req_hasqop = False
        if 'qop' in authheaderdict:
            req_hasqop = True
            req_qop = authheaderdict['qop']     
            if req_qop.lower() != "auth":
                isinvalidreq = True   # only auth supported, auth-int not supported        
        else:
            req_qop = None

        if 'cnonce' in authheaderdict:
            req_cnonce = authheaderdict['cnonce']
        else:
            req_cnonce = None
            if req_hasqop:
                isinvalidreq = True
         
        if 'nc' in authheaderdict:    # is read but nonce-count checking not implemented
            req_nc = authheaderdict['nc']
        else:
            req_nc = None
            if req_hasqop:
                isinvalidreq = True

        if 'response' in authheaderdict:
            req_response = authheaderdict['response']
        else:
            isinvalidreq = True
             
        if not isinvalidreq:
            req_password = self._domaincontroller.getRealmUserPassword(realmname, req_username, environ)
            req_method = environ['REQUEST_METHOD']
             
            required_digest = self.computeDigestResponse(req_username, realmname, req_password, req_method, req_uri, req_nonce, req_cnonce, req_qop, req_nc)
            if required_digest != req_response:
                isinvalidreq = True

        if not isinvalidreq:
            environ['httpauthentication.realm'] = realmname
            environ['httpauthentication.username'] = req_username
            return self._application(environ, start_response)                
     
        return self.sendDigestAuthResponse(environ, start_response)

    def computeDigestResponse(self, username, realm, password, method, uri, nonce, cnonce, qop, nc):
        A1 = username + ":" + realm + ":" + password
        A2 = method + ":" + uri
        if qop:
            digestresp = self.md5kd( self.md5h(A1), nonce + ":" + nc + ":" + cnonce + ":" + qop + ":" + self.md5h(A2))
        else:
            digestresp = self.md5kd( self.md5h(A1), nonce + ":" + self.md5h(A2))
        return digestresp
                
    def md5h(self, data):
        return md5.new(data).hexdigest()
        
    def md5kd(self, secret, data):
        return self.md5h(secret + ':' + data)

    def getErrorMessage(self):
        message = """\
<html><head><title>401 Access not authorized</title></head>
<body>
<h1>401 Access not authorized</h1>
</body>        
</html>        
        """
        return message