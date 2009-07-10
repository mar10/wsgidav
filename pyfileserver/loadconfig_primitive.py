
"""
loadconfig_primitive
====================

:Module: pyfileserver.loadconfig_primitive
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Loads a python module file returning its module namespace as a dictionary, 
except all variables starting with '__' (excluding system and built-in objects).
A compiled module with the filename suffixed with a 'c' may be created as a 
byproduct.  

If Paste <http://pythonpaste.org> is installed, then paste.pyconfig should be 
used as a safer and better variant.

functions::   

   load(filename)

"""

__docformat__ = 'reStructuredText'

import imp

def load(filename):
    returnDict = dict([])
    configmodule = imp.load_source('configuration_module', filename)
    for configkey in configmodule.__dict__.keys():
        if not configkey.startswith('__'):
            returnDict[configkey] = configmodule.__dict__[configkey]               
    return returnDict
