"""
httpdatehelper
==============

:Module: pyfileserver.httpdatehelper
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

HTTP dates helper - an assorted library of helpful date functions:

* getstrftime(secs) - returns the rfc 1123 date/time format of secs, where secs is the number
  of seconds since the epoch. if secs is not given, the current system time is used

* getsecstime(timetypestring) - returns as the number of seconds since the epoch, the date/time
  described in timetypestring. Returns None for invalid input

* getgmtime(timetypestring) -  returns as a standard time tuple (see time and calendar), the date/time
  described in timetypestring. Returns None for invalid input

The following time type strings are supported by getsecstime() and getgmtime()::

   Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
   Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
   Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format  

"""
__docformat__ = 'reStructuredText'

import calendar
import time


def getstrftime(secs=None):   
   # rfc 1123 date/time format
   return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(secs))


def getsecstime(timeformat):
   result = getgmtime(timeformat)
   if result:
      return calendar.timegm(result)
   else:
      return None

def getgmtime(timeformat):

   # Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
   try:
      vtime = time.strptime(timeformat, "%a, %d %b %Y %H:%M:%S GMT")   
      return vtime
   except:
      pass

   # Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
   try:
      vtime = time.strptime(timeformat, "%A %d-%b-%y %H:%M:%S GMT")
      return vtime
   except:
      pass   

   # Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format  
   try:
      vtime = time.strptime(timeformat, "%a %b %d %H:%M:%S %Y")
      return vtime
   
   except:
      pass
      
   return None



