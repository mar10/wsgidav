"""
mainappwrapper
==============

:Module: pyfileserver.mainappwrapper
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

See Running PyFileServer in ext_wsgiutils_server.py

"""

__docformat__ = 'reStructuredText'


import os
import sys
import atexit
import traceback

from extrequestserver import RequestServer
from processrequesterrorhandler import ErrorPrinter
from httpauthentication import HTTPAuthenticator, SimpleDomainController
from requestresolver import RequestResolver
from pyfiledomaincontroller import PyFileServerDomainController


from propertylibrary import PropertyManager
from locklibrary import LockManager
import websupportfuncs
import httpdatehelper
from pyfileserver.fileabstractionlayer import FilesystemAbstractionLayer

class PyFileApp(object):

    def __init__(self, specifiedconfigfile = None):

        if specifiedconfigfile is None:
            specifiedconfigfile = os.path.abspath('PyFileServer.conf')

        loadconfig = True
        try:      
            from paste import pyconfig
            servcfg = pyconfig.Config()
            servcfg.load(specifiedconfigfile)
        except ImportError:         
            try:
                import loadconfig_primitive
                servcfg = loadconfig_primitive.load(specifiedconfigfile)
            except:
                exceptioninfo = traceback.format_exception_only(sys.exc_type, sys.exc_value)
                exceptiontext = ''
                for einfo in exceptioninfo:
                    exceptiontext = exceptiontext + einfo + '\n'   
                raise RuntimeError('Failed to read PyFileServer configuration file : ' + specifiedconfigfile + '\nDue to ' + exceptiontext)
        except:
            exceptioninfo = traceback.format_exception_only(sys.exc_type, sys.exc_value)
            exceptiontext = ''
            for einfo in exceptioninfo:
                exceptiontext = exceptiontext + einfo + '\n'   
            raise RuntimeError('Failed to read PyFileServer configuration file : ' + specifiedconfigfile + '\nDue to ' + exceptiontext)


        self._srvcfg = servcfg
        
        #add default abstraction layer
        self._srvcfg['resAL_library']['*'] = FilesystemAbstractionLayer()
        
        self._infoHeader = '<a href="mailto:%s">Administrator</a> at %s' % (servcfg.get('Info_AdminEmail',''), servcfg.get('Info_Organization',''))
        self._verbose = servcfg.get('verbose', 0)

        _locksfile = servcfg.get('locksfile', os.path.abspath('PyFileServer.locks'))
        _propsfile = servcfg.get('propsfile', os.path.abspath('PyFileServer.dat'))

        _locksmanagerobj = servcfg.get('locksmanager', None) or LockManager(_locksfile)
        _propsmanagerobj = servcfg.get('propsmanager', None) or PropertyManager(_propsfile)     
        _domaincontrollerobj = servcfg.get('domaincontroller', None) or PyFileServerDomainController()


        # authentication fields
        _authacceptbasic = servcfg.get('acceptbasic', False)
        _authacceptdigest = servcfg.get('acceptdigest', True)
        _authdefaultdigest = servcfg.get('defaultdigest', True)

        application = RequestServer(_propsmanagerobj, _locksmanagerobj)      
        application = HTTPAuthenticator(application, _domaincontrollerobj, _authacceptbasic, _authacceptdigest, _authdefaultdigest)      
        application = RequestResolver(application)      
        application = ErrorPrinter(application, server_descriptor=self._infoHeader) 

        self._application = application


    def __call__(self, environ, start_response):
        environ['pyfileserver.config'] = self._srvcfg
        environ['pyfileserver.trailer'] = self._infoHeader

        if self._verbose == 1:
            print >> environ['wsgi.errors'], '[',httpdatehelper.getstrftime(),'] from ', environ.get('REMOTE_ADDR','unknown'), ' ', environ.get('REQUEST_METHOD','unknown'), ' ', environ.get('PATH_INFO','unknown'), ' ', environ.get('HTTP_DESTINATION', '')
        elif self._verbose == 2:      
            print >> environ['wsgi.errors'], "<======== Request Environ"
            for envitem in environ.keys():
                if envitem == envitem.upper():
                    print >> environ['wsgi.errors'], "\t", envitem, ":\t", repr(environ[envitem]) 
            print >> environ['wsgi.errors'], "\n"

        def _start_response(respcode, headers, excinfo=None):   
            if self._verbose == 2:
                print >> environ['wsgi.errors'], "=========> Response"
                print >> environ['wsgi.errors'], 'Response code:', respcode
                headersdict = dict(headers)
                for envitem in headersdict.keys():
                    print >> environ['wsgi.errors'], "\t", envitem, ":\t", repr(headersdict[envitem]) 
                print >> environ['wsgi.errors'], "\n"
            return start_response(respcode, headers, excinfo)

        for v in iter(self._application(environ, _start_response)):
            if self._verbose == 2 and environ['REQUEST_METHOD'] != 'GET':
                print >> environ['wsgi.errors'], v
            yield v 

        return 
        
        