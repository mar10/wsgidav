"""
etagprovider
============

:Module: pyfileserver.etagprovider
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package


Sample ETag provider for PyFileServer. ETag Providers allow developers to
implement stronger or more content specific etags to be used with 
PyFileServer, read extrequestserver.py for more details.

Functions::
   
   getETag(filePath): Returns the following as entity tags
      Non-file - md5(pathname)
      Win32 - md5(pathname)-lastmodifiedtime-filesize
      Others - inode-lastmodifiedtime-filesize


"""

__docformat__ = 'reStructuredText'

import sys
import os
import os.path
import stat
import md5
      
def getETag(filePath):
   if not os.path.isfile(filePath):
      return md5.new(filePath).hexdigest()   
   if sys.platform == 'win32':
      statresults = os.stat(filePath)
      return md5.new(filePath).hexdigest() + '-' + str(statresults[stat.ST_MTIME]) + '-' + str(statresults[stat.ST_SIZE])
   else:
      statresults = os.stat(filePath)
      return str(statresults[stat.ST_INO]) + '-' + str(statresults[stat.ST_MTIME]) + '-' + str(statresults[stat.ST_SIZE])

   