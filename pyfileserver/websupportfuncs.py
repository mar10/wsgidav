"""
websupportfuncs
===============

:Module: pyfileserver.websupportfuncs
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

This module consists of miscellaneous support functions for PyFileServer::

   resource list functions
      recursiveGetPath(resourceAL, dirtorecurs, displaypath, recursfurther, liststore, preadd=True)
      getDepthActionList(resourceAL, mappedpath, displaypath, depthlevel, preadd=True)
      getCopyDepthActionList(depthactionlist, origpath, origdisplaypath, destpath, destdisplaypath)

   URL functions
      getLevelUpURL(displayPath)
      cleanUpURL(displayURL)
      cleanUpURLWithoutQuote(displayURL)
      constructFullURL(displaypath, environ)
      getRelativeURL(fullurl, environ)

   interpret content range header
      obtainContentRanges(rangetext, filesize)
   
   evaluate HTTP If-Match, if-None-Match, If-Modified-Since, If-Unmodified-Since headers   
      evaluateHTTPConditionals(lastmodifiedsecs, entitytag, environ, isnewfile=False)
   
   evaluate webDAV if header   
      getIfHeaderDict(iftext)
      testIfHeaderDict(dictIf, url, locktokenlist, entitytag, returnlocklist, environ)
      testForLockTokenInIfHeaderDict(dictIf, locktoken, fullurl, headurl)

*author note*: More documentation here required

This module is specific to the PyFileServer application.


"""

__docformat__ = 'reStructuredText'

import re
import urllib

import httpdatehelper
from processrequesterrorhandler import HTTPRequestException
import processrequesterrorhandler


def recursiveGetPath(resourceAL, dirtorecurs, displaypath, recursfurther, liststore, preadd=True):   
    filelist = resourceAL.getCollectionContents(dirtorecurs)
    for f in filelist:
        filename = resourceAL.joinPath(dirtorecurs, f)
        if resourceAL.isCollection(filename):
            filedisplaypath = displaypath + f + "/"
            if preadd:
                liststore.append( (filename , filedisplaypath) )
            if recursfurther:
                recursiveGetPath(resourceAL, filename, filedisplaypath, recursfurther, liststore, preadd)
            if not preadd:
                liststore.append( (filename , filedisplaypath) )
        else: #file
            filedisplaypath = displaypath + f
            liststore.append( (filename , filedisplaypath) )

# note it must return [(mappedpath, displaypath)] even if mappedpath does not exist
def getDepthActionList(resourceAL, mappedpath, displaypath, depthlevel, preadd=True):
    if resourceAL.isCollection(mappedpath) and depthlevel != '0':
        liststore = [] 
        if preadd:
            liststore.append((mappedpath,displaypath))
        recursiveGetPath(resourceAL, mappedpath, displaypath, depthlevel == 'infinity', liststore, preadd)
        if not preadd:
            liststore.append((mappedpath,displaypath))
        return liststore         
    else:
        return [(mappedpath, displaypath)]


def getCopyDepthActionList(depthactionlist, origpath, origdisplaypath, destpath, destdisplaypath):
    listReturn = []

    origdisplaypathL = origdisplaypath
    origdisplaypathL = origdisplaypathL.rstrip('/')

    destdisplaypathL = destdisplaypath
    destdisplaypathL = destdisplaypathL.rstrip('/')

    for (filepath, filedisplaypath) in depthactionlist:
        listReturn.append( ( destpath + filepath[len(origpath):] , destdisplaypathL + filedisplaypath[len(origdisplaypathL):] )  )      
    return listReturn

def getLevelUpURL(displayPath):
    listItems = displayPath.split("/")
    listItems2 = []
    for item in listItems:
        if item!="":
            listItems2.append(item)
    listItems2.pop()
    return "/" + urllib.quote("/".join(listItems2)) + "/"

def cleanUpURL(displayURL):
    listItems = displayURL.split("/")
    listItems2 = []
    for item in listItems:
        if item!="":
            listItems2.append(item)
    return "/" + urllib.quote("/".join(listItems2))

def cleanUpURLWithoutQuote(displayURL):
    listItems = displayURL.split("/")
    listItems2 = []
    for item in listItems:
        if item!="":
            listItems2.append(item)
    return "/" + "/".join(listItems2) 

# Range Specifiers
reByteRangeSpecifier = re.compile("(([0-9]+)\-([0-9]*))")
reSuffixByteRangeSpecifier = re.compile("(\-([0-9]+))")

def obtainContentRanges(rangetext, filesize):
    """
   returns tuple
   list: content ranges as values to their parsed components in the tuple (seek_position/abs position of first byte, abs position of last byte, num_of_bytes_to_read)
   value: total length for Content-Length
   """
    listReturn = []
    seqRanges = rangetext.split(",")
    for subrange in seqRanges:
        matched = False
        if not matched:
            mObj = reByteRangeSpecifier.search(subrange)
            if mObj:
                firstpos = long(mObj.group(2))
                if mObj.group(3) == '':
                    lastpos = filesize - 1
                else:
                    lastpos = long(mObj.group(3))
                if firstpos <= lastpos and firstpos < filesize:
                    if lastpos >= filesize:
                        lastpos = filesize - 1
                    listReturn.append( (firstpos , lastpos) )
                    matched = True
        if not matched:      
            mObj = reSuffixByteRangeSpecifier.search(subrange)
            if mObj:
                firstpos = filesize - long(mObj.group(2))
                if firstpos < 0:
                    firstpos = 0
                lastpos = filesize - 1
                listReturn.append( (firstpos , lastpos) )

                matched = True

    # consolidate ranges
    listReturn.sort()
    listReturn2 = []
    totallength = 0
    while(len(listReturn) > 0):
        (rfirstpos, rlastpos) = listReturn.pop()
        counter = len(listReturn)
        while counter > 0:
            (nfirstpos, nlastpos) = listReturn[counter-1]
            if nlastpos < rfirstpos - 1 or nfirstpos > nlastpos + 1:
                pass
            else: 
                rfirstpos = min(rfirstpos, nfirstpos)
                rlastpos = max(rlastpos, nlastpos)
                del listReturn[counter-1]
            counter = counter - 1
        listReturn2.append((rfirstpos,rlastpos,rlastpos - rfirstpos + 1 ))            
        totallength = totallength + rlastpos - rfirstpos + 1

    return (listReturn2, totallength)

#
#def evaluateHTTPConditionalsWithoutExceptions(lastmodified, entitytag, environ, isnewfile=False):
#    ## Conditions
#
#    # An HTTP/1.1 origin server, upon receiving a conditional request that includes both a Last-Modified date
#    # (e.g., in an If-Modified-Since or If-Unmodified-Since header field) and one or more entity tags (e.g., 
#    # in an If-Match, If-None-Match, or If-Range header field) as cache validators, MUST NOT return a response 
#    # status of 304 (Not Modified) unless doing so is consistent with all of the conditional header fields in 
#    # the request.
#
#    if 'HTTP_IF_MATCH' in environ:
#        if isnewfile:
#            return '412 Precondition Failed'
#        else:
#            ifmatchlist = environ['HTTP_IF_MATCH'].split(",")
#            for ifmatchtag in ifmatchlist:
#                ifmatchtag = ifmatchtag.strip(" \"\t")
#                if ifmatchtag == entitytag or ifmatchtag == '*':
#                    break   
#                return '412 Precondition Failed'
#
#    # If-None-Match 
#    # If none of the entity tags match, then the server MAY perform the requested method as if the 
#    # If-None-Match header field did not exist, but MUST also ignore any If-Modified-Since header field
#    # (s) in the request. That is, if no entity tags match, then the server MUST NOT return a 304 (Not Modified) 
#    # response.
#    ignoreifmodifiedsince = False         
#    if 'HTTP_IF_NONE_MATCH' in environ:         
#        if isnewfile:
#            ignoreifmodifiedsince = True
#        else:
#            ifmatchlist = environ['HTTP_IF_NONE_MATCH'].split(",")
#            for ifmatchtag in ifmatchlist:
#                ifmatchtag = ifmatchtag.strip(" \"\t")
#                if ifmatchtag == entitytag or ifmatchtag == '*':
#                    return '412 Precondition Failed'
#            ignoreifmodifiedsince = True
#
#    if not isnewfile and 'HTTP_IF_UNMODIFIED_SINCE' in environ:
#        ifunmodtime = httpdatehelper.getsecstime(environ['HTTP_IF_UNMODIFIED_SINCE'])
#        if ifunmodtime:
#            if ifunmodtime <= lastmodified:
#                return '412 Precondition Failed'
#
#    if not isnewfile and 'HTTP_IF_MODIFIED_SINCE' in environ and not ignoreifmodifiedsince:
#        ifmodtime = httpdatehelper.getsecstime(environ['HTTP_IF_MODIFIED_SINCE'])
#        if ifmodtime:
#            if ifmodtime > lastmodified:
#                return '304 Not Modified'
#
#    return '200 OK'


def evaluateHTTPConditionals(resourceAL, respath, lastmodified, entitytag, environ, isnewfile=False):
    ## Conditions

    # An HTTP/1.1 origin server, upon receiving a conditional request that includes both a Last-Modified date
    # (e.g., in an If-Modified-Since or If-Unmodified-Since header field) and one or more entity tags (e.g., 
    # in an If-Match, If-None-Match, or If-Range header field) as cache validators, MUST NOT return a response 
    # status of 304 (Not Modified) unless doing so is consistent with all of the conditional header fields in 
    # the request.

    if 'HTTP_IF_MATCH' in environ and resourceAL.supportEntityTag(respath):
        if isnewfile:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_PRECONDITION_FAILED)
        else:
            ifmatchlist = environ['HTTP_IF_MATCH'].split(",")
            for ifmatchtag in ifmatchlist:
                ifmatchtag = ifmatchtag.strip(" \"\t")
                if ifmatchtag == entitytag or ifmatchtag == '*':
                    break   
                raise HTTPRequestException(processrequesterrorhandler.HTTP_PRECONDITION_FAILED)

    # If-None-Match 
    # If none of the entity tags match, then the server MAY perform the requested method as if the 
    # If-None-Match header field did not exist, but MUST also ignore any If-Modified-Since header field
    # (s) in the request. That is, if no entity tags match, then the server MUST NOT return a 304 (Not Modified) 
    # response.
    ignoreifmodifiedsince = False         
    if 'HTTP_IF_NONE_MATCH' in environ and resourceAL.supportEntityTag(respath):         
        if isnewfile:
            ignoreifmodifiedsince = True
        else:
            ifmatchlist = environ['HTTP_IF_NONE_MATCH'].split(",")
            for ifmatchtag in ifmatchlist:
                ifmatchtag = ifmatchtag.strip(" \"\t")
                if ifmatchtag == entitytag or ifmatchtag == '*':
                    raise HTTPRequestException(processrequesterrorhandler.HTTP_PRECONDITION_FAILED)
            ignoreifmodifiedsince = True

    if not isnewfile and 'HTTP_IF_UNMODIFIED_SINCE' in environ and resourceAL.supportLastModified(respath):
        ifunmodtime = httpdatehelper.getsecstime(environ['HTTP_IF_UNMODIFIED_SINCE'])
        if ifunmodtime:
            if ifunmodtime <= lastmodified:
                raise HTTPRequestException(processrequesterrorhandler.HTTP_PRECONDITION_FAILED)

    if not isnewfile and 'HTTP_IF_MODIFIED_SINCE' in environ and not ignoreifmodifiedsince and resourceAL.supportLastModified(respath):
        ifmodtime = httpdatehelper.getsecstime(environ['HTTP_IF_MODIFIED_SINCE'])
        if ifmodtime:
            if ifmodtime > lastmodified:
                raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_MODIFIED)

def constructFullURL(displaypath, environ):
    return "http://" + environ['HTTP_HOST'] + displaypath

def getRelativeURL(fullurl, environ):
    return fullurl[len("http://" + environ['HTTP_HOST']):]

reIfSeparator = re.compile(r'(\<([^>]+)\>)|(\(([^\)]+)\))')
reIfHeader = re.compile(r'\<([^>]+)\>([^<]+)')
reIfTagList = re.compile(r'\(([^)]+)\)')
reIfTagListContents = re.compile(r'(\S+)')

def getIfHeaderDict(iftext):
    iftext = iftext.strip()
    if not iftext.startswith('<'):
        iftext = '<*>' + iftext   

    returnDict = dict([])
    resource1 = '*'
    for (tmpURLVar, URLVar, tmpContentVar, contentVar) in reIfSeparator.findall(iftext):
        if tmpURLVar != '':
            resource1 = URLVar         
        else:
            listTagContents = []
            testflag = True
            for listitem in reIfTagListContents.findall(contentVar):            
                if listitem.upper() != 'NOT':
                    if listitem.startswith('['):
                        listTagContents.append((testflag,'entity',listitem.strip('\"[]')))   
                    else:
                        listTagContents.append((testflag,'locktoken',listitem.strip('<>')))            
                testflag = listitem.upper() != 'NOT'

            if resource1 in returnDict:
                listTag = returnDict[resource1]
            else:
                listTag = []
                returnDict[resource1] = listTag
            listTag.append(listTagContents)
    return returnDict

def _lookForLockTokenInSubDict(locktoken, listTest):
    for listTestConds in listTest:
        for (testflag, checkstyle, checkvalue) in listTestConds:
            if checkstyle == 'locktoken' and testflag:
                if locktoken == checkvalue:  
                    return True
    return False   

def testForLockTokenInIfHeaderDict(dictIf, locktoken, fullurl, headurl):
    if '*' in dictIf:
        if _lookForLockTokenInSubDict(locktoken, dictIf['*']):
            return True

    if fullurl in dictIf:
        if _lookForLockTokenInSubDict(locktoken, dictIf[fullurl]):
            return True

    if headurl in dictIf:
        if _lookForLockTokenInSubDict(locktoken, dictIf[headurl]):
            return True


def testIfHeaderDict(resourceAL, respath, dictIf, fullurl, locktokenlist, entitytag):

    if fullurl in dictIf:
        listTest = dictIf[fullurl]
    elif '*' in dictIf:
        listTest = dictIf['*']
    else:
        return True   

    for listTestConds in listTest:
        matchfailed = False

        for (testflag, checkstyle, checkvalue) in listTestConds:
            if checkstyle == 'entity' and resourceAL.supportEntityTag(respath):
                testresult = entitytag == checkvalue  
            elif checkstyle == 'entity':
                testresult = testflag
            elif checkstyle == 'locktoken':
                testresult = checkvalue in locktokenlist
            else: # unknown
                testresult = True
            checkresult = testresult == testflag
            if not checkresult:
                matchfailed = True         
                break
        if not matchfailed:
            return True
    return False


