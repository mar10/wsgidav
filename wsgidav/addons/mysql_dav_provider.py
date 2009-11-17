"""
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Implementation of a DAV provider that provides a very basic, read-only
resource layer emulation of a MySQL database.

This module is specific to the WsgiDAV application. It provides a 
classes ``MySQLBrowserProvider``.

Usage::
    
    (see sample_wsgidav.conf)
    MySQLBrowserProvider(host, user, passwd, db)

    host - host of database server
    user - username to access database
    passwd - passwd to access database
    db - name of database on database server
    
The ``MySQLBrowserProvider`` provides a very basic, read-only
resource layer emulation of a MySQL database. 
It provides the following interface:

    - the root collection shared consists of collections that correspond to 
      table names
      
    - in each table collection, there is a resource called "_ENTIRE_CONTENTS".
      This is a non-collection resource that returns a csv representation of the
      entire table
         
    - if the table has a single primary key, each table record will also appear
      as a non-collection resource in the table collection using the primary key
      value as its name. This resource returns a csv representation of the record
      and will also include the record attributes as live properties with 
      attribute name as property name and table name suffixed with colon as the
      property namespace 


This is a very basic interface and below is a by no means thorough summary of 
its limitations:

    - Really only supports having numbers or strings as primary keys. The code uses
      a numeric or string comparison that may not hold up if the primary key is 
      a date or some other datatype.
    
    - There is no handling for cases like BLOBs as primary keys or such. Well, there is
      no handling for BLOBs in general.
    
    - When returning contents, it buffers the entire contents! A bad way to return
      large tables. Ideally you would have a FileMixin that reads the database even
      as the application reads the file object....
    
    - It takes too many database queries to return information. 
      Ideally there should be some sort of caching for metadata at least, to avoid
      unnecessary queries to the database.


Abstraction Layers must provide the methods as described in 
abstractionlayerinterface_

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
.. _abstractionlayerinterface : interfaces/abstractionlayerinterface.py
"""
from wsgidav.dav_provider import DAVProvider, DAVResource
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN
from wsgidav import util
import MySQLdb
import md5
import time
import csv
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)


class MySQLBrowserProvider(DAVProvider):
    
    def __init__(self, host, user, passwd, db):
        super(MySQLBrowserProvider, self).__init__()
        self._host = host
        self._user = user
        self._passwd = passwd
        self._db = db
        self.connectCount = 0
    

    def __repr__(self):
        return "%s for db '%s' on '%s' (user: '%s')'" % (self.__class__.__name__, self._db, self._host, self._user)


    def _splitPath(self, path):
        """Return (tableName, primaryKey) tuple for a request path."""
        if path.strip() in (None, "", "/"):
            return (None, None)
        tableName, primKey = util.saveSplit(path.strip("/"), "/", 1)
#        _logger.debug("'%s' -> ('%s', '%s')" % (path, tableName, primKey))
        return (tableName, primKey)


    def _initConnection(self):
        self.connectCount += 1
        return MySQLdb.connect(host=self._host,
                               user=self._user,
                               passwd=self._passwd,
                               db=self._db)


    def _getFieldList(self, conn, table_name):
        retlist = []
        cursor = conn.cursor (MySQLdb.cursors.DictCursor)
        cursor.execute ("DESCRIBE " + table_name)
        result_set = cursor.fetchall ()
        for row in result_set:
            retlist.append(row["Field"])
        cursor.close ()
        return retlist      
    
    
    def _isDataTypeNumeric(self, datatype):
        if datatype is None:
            return False
        #how many MySQL datatypes does it take to change a lig... I mean, store numbers
        numerictypes = ["BIGINT",
                        "INTT",
                        "MEDIUMINT",
                        "SMALLINT",
                        "TINYINT",
                        "BIT",
                        "DEC",
                        "DECIMAL",
                        "DOUBLE",
                        "FLOAT",
                        "REAL",
                        "DOUBLE PRECISION",
                        "INTEGER",
                        "NUMERIC"]
        datatype = datatype.upper()                
        for numtype in numerictypes:
            if datatype.startswith(numtype):
                return True                     
        return False                 
    

    def _existsRecordByPrimaryKey(self, conn, table_name, pri_key_value):
        pri_key = None
        pri_field_type = None
        cursor = conn.cursor (MySQLdb.cursors.DictCursor)
        cursor.execute ("DESCRIBE " + table_name)
        result_set = cursor.fetchall ()
        for row in result_set:
            if row["Key"] == "PRI":
                if pri_key is None:
                    pri_key = row["Field"]
                    pri_field_type = row["Type"]         
                else:
                    return False #more than one primary key - multipart key?
        cursor.close ()

        isNumType = self._isDataTypeNumeric(pri_field_type)      
        
        cursor = conn.cursor (MySQLdb.cursors.DictCursor)
        if isNumType:
            cursor.execute("SELECT " + pri_key + " FROM " + self._db + "." + table_name + " WHERE " + pri_key + " = " + pri_key_value)
        else:
            cursor.execute("SELECT " + pri_key + " FROM " + self._db + "." + table_name + " WHERE " + pri_key + " = '" + pri_key_value + "'")
        row = cursor.fetchone ()
        if row is None:
            cursor.close()
            return False
        cursor.close()
        return True            


    def _getFieldByPrimaryKey(self, conn, table_name, pri_key_value, field_name):      
        pri_key = None
        pri_field_type = None
        cursor = conn.cursor (MySQLdb.cursors.DictCursor)
        cursor.execute ("DESCRIBE " + table_name)
        result_set = cursor.fetchall ()
        for row in result_set:
            if row["Key"] == "PRI":
                if pri_key is None:
                    pri_key = row["Field"]
                    pri_field_type = row["Type"]         
                else:
                    return None #more than one primary key - multipart key?
        cursor.close ()

        isNumType = self._isDataTypeNumeric(pri_field_type)      
        
        cursor = conn.cursor (MySQLdb.cursors.DictCursor)
        if isNumType:
            cursor.execute("SELECT " + field_name + " FROM " + self._db + "." + table_name + " WHERE " + pri_key + " = " + pri_key_value)
        else:
            cursor.execute("SELECT " + field_name + " FROM " + self._db + "." + table_name + " WHERE " + pri_key + " = '" + pri_key_value + "'")
        row = cursor.fetchone ()
        if row is None:
            cursor.close()
            return None
        val = str(row[field_name])         
        cursor.close()
        return val            

                                 
    def _getRecordByPrimaryKey(self, conn, table_name, pri_key_value):      
        dictRet = {}            
        pri_key = None
        pri_field_type = None
        cursor = conn.cursor (MySQLdb.cursors.DictCursor)
        cursor.execute ("DESCRIBE " + table_name)
        result_set = cursor.fetchall ()
        for row in result_set:
            if row["Key"] == "PRI":
                if pri_key is None:
                    pri_key = row["Field"]
                    pri_field_type = row["Type"]         
                else:
                    return None #more than one primary key - multipart key?
        cursor.close ()

        isNumType = self._isDataTypeNumeric(pri_field_type)      
        
        cursor = conn.cursor (MySQLdb.cursors.DictCursor)
        if isNumType:
            cursor.execute("SELECT * FROM " + self._db + "." + table_name + " WHERE " + pri_key + " = " + pri_key_value)
        else:
            cursor.execute("SELECT * FROM " + self._db + "." + table_name + " WHERE " + pri_key + " = '" + pri_key_value + "'")
        row = cursor.fetchone ()
        if row is None:
            cursor.close()
            return None
        for fname in row.keys():
            dictRet[fname] = str(row[fname])         
        cursor.close()
        return dictRet            

    
    def _findPrimaryKey(self, conn, table_name):
        pri_key = None
        cursor = conn.cursor (MySQLdb.cursors.DictCursor)
        cursor.execute ("DESCRIBE " + table_name)
        result_set = cursor.fetchall ()
        for row in result_set:
            fieldname = row["Field"]
            keyvalue = row["Key"]
            if keyvalue == "PRI":
                if pri_key is None:
                    pri_key = fieldname         
                else:
                    return None #more than one primary key - multipart key?
        cursor.close ()
        return pri_key

                
    def _listFields(self, conn, table_name, field_name):
        retlist = []
        cursor = conn.cursor (MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT " + field_name + " FROM " + self._db + "." + table_name)
        result_set = cursor.fetchall ()
        for row in result_set:
            retlist.append(str(row[field_name]))      
        cursor.close()
        return retlist
    

    def _listTables(self, conn):
        retlist = []      
        cursor = conn.cursor ()
        cursor.execute ("SHOW TABLES")
        result_set = cursor.fetchall ()
        for row in result_set:
            retlist.append("%s" % (row[0]))
        cursor.close ()
        return retlist
        

    def getMemberNames(self, path):
        """
        path - path identifier for the resource

        returns a list of names of resources contained in the collection resource
        specified
        """
        conn = self._initConnection()
#        resdata = path.strip(":").split(":")
        tableName, primKey = self._splitPath(path)
#        if len(resdata) == 1:
        if tableName is None:
            retlist = self._listTables(conn)         
#        elif len(resdata) == 2:
        elif primKey is None:
            pri_key = self._findPrimaryKey(conn, tableName)
            if pri_key is not None:
                retlist = self._listFields(conn, tableName, pri_key)      
            else:
                retlist = []
            retlist[0:0] = ["_ENTIRE_CONTENTS"]
        else:
            retlist = []      
        conn.close()
        return retlist
        

    def getResourceInst(self, path, typeList=None):
        """Return info dictionary for path.
        
        See getResourceInst()
        """
        # TODO: calling exists() makes directory browsing VERY slow.
        #       At least compared to PyFileServer, which simply used string 
        #       functions to get displayType and displayRemarks  
        if not self.exists(path):
            # Return non-existing davresource
            return DAVResource(self, path, None, typeList)
        tableName, primKey = self._splitPath(path)

        displayType = "Unknown" 
        displayRemarks = ""
        contentType = "text/html"

#        _logger.debug("getInfoDict(%s), nc=%s" % (path, self.connectCount))
        if tableName is None:
            displayType = "Database" 
        elif primKey is None: # "database" and table name
            displayType = "Database Table"
        else: 
            contentType = "text/csv"
            if primKey == "_ENTIRE_CONTENTS":
                displayType = "Database Table Contents"
                displayRemarks = "CSV Representation of Table Contents"
            else:
                displayType = "Database Record"
                displayRemarks = "Attributes available as properties"

        # Avoid calling isCollection, since it would call isExisting -> _initConnection 
#        isCollection = self.isCollection(path)
        isCollection = primKey is None
        
        # Avoid calling getPreferredPath, since it would call isCollection -> _initConnection 
#        name = util.getUriName(self.getPreferredPath(path))
        name = util.getUriName(path)

        dict = {"contentLength": None,
                "contentType": contentType,
                "name": name,
                "displayName": name,
                "displayType": displayType,
                "modified": None,
                "created": time.time(),
                "etag": md5.new(path).hexdigest(),
                "supportRanges": False,
                "isCollection": isCollection, 
                }
        # Some resource-only infos: 
        if not isCollection:
            dict["modified"] = time.time()
#        _logger.debug("---> getInfoDict, nc=%s" % self.connectCount)
        davres = DAVResource(self, path, dict, typeList)
        return davres
    

    def exists(self, path):
        tableName, primKey = self._splitPath(path)
        if path == "/":
            return True

        try:
            conn = self._initConnection()
            # Check table existence:
            tbllist = self._listTables(conn)
            if tableName not in tbllist:
                return False
            # Check table key existence:
            if primKey and primKey != "_ENTIRE_CONTENTS":
                return self._existsRecordByPrimaryKey(conn, tableName, primKey) 
            return True 
        finally:
            conn.close()

    
    def isCollection(self, path):
        _tableName, primKey = self._splitPath(path)
        return self.exists(path) and primKey is None 
    

    def isResource(self, path):
        _tableName, primKey = self._splitPath(path)
        return self.exists(path) and primKey is not None 

            
    def createEmptyResource(self, path):
        raise DAVError(HTTP_FORBIDDEN)               
    

    def createCollection(self, path):
        raise DAVError(HTTP_FORBIDDEN)               
    

    def deleteCollection(self, path):
        raise DAVError(HTTP_FORBIDDEN)               


    def openResourceForRead(self, path, davres=None):
        """
        path - path identifier for the resource
                
        returns a file-like object / stream containing the contents of the
        resource specified.

        The application will close() the stream.      
        """
        filestream = StringIO()

#        resdata = path.strip(":").split(":")
        tableName, primKey = self._splitPath(path)
#        if len(resdata) == 3:
        if primKey is not None:
#            table_name = resdata[1] 
            conn = self._initConnection()
            listFields = self._getFieldList(conn, tableName)
            csvwriter = csv.DictWriter(filestream, listFields, extrasaction="ignore") 
            dictFields = {}
            for field_name in listFields:
                dictFields[field_name] = field_name
            csvwriter.writerow(dictFields)

            if primKey == "_ENTIRE_CONTENTS":
                cursor = conn.cursor (MySQLdb.cursors.DictCursor)            
                cursor.execute ("SELECT * from " + self._db + "." + tableName)
                result_set = cursor.fetchall ()
                for row in result_set:
                    csvwriter.writerow(row)
                cursor.close ()      
            else:
                row = self._getRecordByPrimaryKey(conn, tableName, primKey)  
                if row is not None:
                    csvwriter.writerow(row)
            conn.close()
                
        #this suffices for small dbs, but 
        #for a production big database, I imagine you would have a FileMixin that
        #does the retrieving and population even as the file object is being read 
        filestream.seek(0)
        return filestream 
        
        #filevalue = filestream.getvalue() 
        #filestream.close()
        #return StringIO.StringIO(filevalue)

    

    def openResourceForWrite(self, path, contenttype=None):
        raise DAVError(HTTP_FORBIDDEN)               
    
    
    def deleteResource(self, path):
        raise DAVError(HTTP_FORBIDDEN)               
    
    
    def copyResource(self, path, destrespath):
        raise DAVError(HTTP_FORBIDDEN)               


    def getPropertyValue(self, path, propname, davres=None):
        """Return the value of a property.
        
        The base implementation handles:
        
        - ``{DAV:}lockdiscovery`` and ``{DAV:}supportedlock`` using the 
          associated lock manager.
        - All other *live* properties (i.e. name starts with ``{DAV:}``) are 
          delegated to self.getLivePropertyValue()
        - Finally, other properties are considered *dead*, and are handled  using 
          the associated property manager, if one is present. 
        """
        # Return table field as property
#        resdata = path.strip(":").split(":")
        tableName, primKey = self._splitPath(path)
        if primKey is not None:
            ns, localName = util.splitNamespace(propname)
            if ns == tableName:
                conn = self._initConnection()
                fieldlist = self._getFieldList(conn, tableName)
                if localName in fieldlist:
                    val = self._getFieldByPrimaryKey(conn, tableName, primKey, localName)
                    conn.close()
                    return val
                conn.close()
        # else, let default implementation return supported live and dead properties
        return super(MySQLBrowserProvider, self).getPropertyValue(path, propname, davres)
    

    def getPropertyNames(self, davres, mode="allprop"):
        """Return list of supported property names in Clark Notation.
        
        Return supported live and dead properties. (See also DAVProvider.getPropertyNames().)
        
        In addition, all table field names are returned as properties.
        """
        # Let default implementation return supported live and dead properties
        propNames = super(MySQLBrowserProvider, self).getPropertyNames(davres, mode)
        # Add fieldnames as properties 
#        resdata = path.strip(":").split(":")
        tableName, primKey = self._splitPath(davres.path)
        if primKey is not None:
            conn = self._initConnection()
            fieldlist = self._getFieldList(conn, tableName)
            for fieldname in fieldlist:
                propNames.append("{%s:}%s" % (tableName, fieldname))
            conn.close()
        return propNames
