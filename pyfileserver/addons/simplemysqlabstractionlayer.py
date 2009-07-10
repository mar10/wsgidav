"""
simplemysqlabstractionlayer
===========================

:Module: pyfileserver.addons.simplemysqlabstractionlayer
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

This module is specific to the PyFileServer application. It provides a 
classes ``SimpleMySQLResourceAbstractionLayer``.

Usage::
   
   (see PyFileServer-example.conf)
   SimpleMySQLResourceAbstractionLayer(host, user, passwd, db)

   host - host of database server
   user - username to access database
   passwd - passwd to access database
   db - name of database on database server
   
The ``SimpleMySQLResourceAbstractionLayer`` provides a very basic, read-only
resource layer emulation of a MySQL database. It provides the following interface:

+ the root collection shared consists of collections that correspond to table
  names
  
+ in each table collection, there is a resource called "_ENTIRE_CONTENTS".
  This is a non-collection resource that returns a csv representation of the
  entire table   

+ if the table has a single primary key, each table record will also appear
  as a non-collection resource in the table collection using the primary key
  value as its name. This resource returns a csv representation of the record
  and will also include the record attributes as live properties with 
  attribute name as property name and table name suffixed with colon as the
  property namespace 


This is a very basic interface and below is a by no means thorough summary of 
its limitations:

+ Really only supports having numbers or strings as primary keys. The code uses
  a numeric or string comparison that may not hold up if the primary key is 
  a date or some other datatype.

+ There is no handling for cases like BLOBs as primary keys or such. Well, there is
  no handling for BLOBs in general.

+ When returning contents, it buffers the entire contents! A bad way to return
  large tables. Ideally you would have a FileMixin that reads the database even
  as the application reads the file object....

+ It takes too many database queries to return information. 
  Ideally there should be some sort of caching for metadata at least, to avoid
  unnecessary queries to the database.


Abstraction Layers must provide the methods as described in 
abstractionlayerinterface_

.. _abstractionlayerinterface : interfaces/abstractionlayerinterface.py

See extrequestserver.py for more information about resource abstraction layers in 
PyFileServer

"""
import MySQLdb
import MySQLdb.cursors
import md5
import time
import StringIO
import csv

class SimpleMySQLResourceAbstractionLayer(object):
   
   def __init__(self, host, user, passwd, db):
      self._host = host
      self._user = user
      self._passwd = passwd
      self._db = db
   
   def _initConnection(self):
      return MySQLdb.connect (host = self._host,
                              user = self._user,
                              passwd = self._passwd,
                              db = self._db)

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
      numerictypes = ['BIGINT',\
                      'INTT',
                      'MEDIUMINT',
                      'SMALLINT',
                      'TINYINT',
                      'BIT',
                      'DEC',
                      'DECIMAL',
                      'DOUBLE',
                      'FLOAT',
                      'REAL',
                      'DOUBLE PRECISION',
                      'INTEGER',
                      'NUMERIC']
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
      cursor.execute('SELECT ' + field_name + " FROM " + self._db + "." + table_name)
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
      
   def resolvePath(self, resheadpath, urlelementlist):
      """ 
      resheadpath should always be "database"
      """ 
      if len(urlelementlist) == 0:
         return resheadpath
      return resheadpath + ":" + ":".join(urlelementlist)

   def breakPath(self, resheadpath, respath):      
      residue = respath[len(resheadpath):].strip(":")
      return residue.split(":")


   def getResourceDescriptor(self, respath):
      resdata = respath.strip(":").split(":")
      if len(resdata) == 1:
         return ["Database", ""]
      elif len(resdata) == 2: # "database" and table name
         return ["Database Table", ""]
      elif len(resdata) == 3: 
         if resdata[2] == "_ENTIRE_CONTENTS":
            return ["Database Table Contents", "CSV Representation of Table Contents"]
         else:
            return ["Database Record", "Attributes available as properties"]
      else:
         return ["Unknown", "Unknown"]
   
   def getResourceDescription(self, respath):
      resdata = respath.strip(":").split(":")
      if len(resdata) == 1:
         return "Database"
      elif len(resdata) == 2: # "database" and table name
         return "Database Table"
      elif len(resdata) == 3: 
         if resdata[2] == "_ENTIRE_CONTENTS":
            return "Database Table Contents"
         else:
            return "Database Record"
      else:
         return "Unknown"
      
   def getContentType(self, respath):
      resdata = respath.strip(":").split(":")
      if len(resdata) == 3:
         return "text/csv"
      else: 
         return "text/html"

   def getLastModified(self, respath):
      return time.time()
   
   def supportContentLength(self, respath):
      return False
   
   def getContentLength(self, respath):
      return 0
         
   def getEntityTag(self, respath):
      return md5.new(respath).hexdigest()

   def isCollection(self, respath):
      if self.exists(respath):
         resdata = respath.strip(":").split(":")
         return len(resdata) <= 2
      else:
         return False   
   
   def isResource(self, respath):
      if self.exists(respath):
         resdata = respath.strip(":").split(":")
         return len(resdata) == 3
      else:
         return False   
         
   def exists(self, respath):
      resdata = respath.strip(":").split(":")
      if len(resdata) >= 2:     #database:table_name check
         conn = self._initConnection()
         tbllist = self._listTables(conn)
         conn.close()
         if resdata[1] not in tbllist:
            return False

      if len(resdata) == 3:     #database:table_name:value check
         if resdata[2] == "_ENTIRE_CONTENTS":
            return True
         else:
            conn = self._initConnection()            
            val =  self._existsRecordByPrimaryKey(conn, resdata[1], resdata[2]) 
            conn.close()
            return val
      return True 
   
   def createCollection(self, respath):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)               
   
   def deleteCollection(self, respath):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)               

   def supportEntityTag(self, respath):
      return False

   def supportLastModified(self, respath):
      return False
   
   def supportRanges(self, respath):
      return False
         
   def openResourceForRead(self, respath):
      """
      respath - path identifier for the resource
            
      returns a file-like object / stream containing the contents of the
      resource specified.

      The application will close() the stream.      
      """
      filestream = StringIO.StringIO()

      resdata = respath.strip(":").split(":")
      if len(resdata) == 3:
         table_name = resdata[1] 
         conn = self._initConnection()
         listFields = self._getFieldList(conn, table_name)
         csvwriter = csv.DictWriter(filestream, listFields, extrasaction='ignore') 
         dictFields = {}
         for field_name in listFields:
            dictFields[field_name] = field_name
         csvwriter.writerow(dictFields)

         if resdata[2] == "_ENTIRE_CONTENTS":
            cursor = conn.cursor (MySQLdb.cursors.DictCursor)            
            cursor.execute ("SELECT * from " + self._db + "." + table_name)
            result_set = cursor.fetchall ()
            for row in result_set:
               csvwriter.writerow(row)
            cursor.close ()      
         else:
            row = self._getRecordByPrimaryKey(conn, table_name, resdata[2])  
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
   
   def openResourceForWrite(self, respath, contenttype=None):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)               
   
   def deleteResource(self, respath):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)               
   
   def copyResource(self, respath, destrespath):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)               
   
   def getContainingCollection(self, respath):
      dsplit = respath.rsplit(":",1)
      return dsplit[0]
   
   def getCollectionContents(self, respath):
      """
      respath - path identifier for the resource

      returns a list of names of resources contained in the collection resource
      specified
      """
      conn = self._initConnection()
      resdata = respath.strip(":").split(":")
      if len(resdata) == 1:
         retlist = self._listTables(conn)         
      elif len(resdata) == 2:
         pri_key = self._findPrimaryKey(conn, resdata[1])
         if pri_key is not None:
            retlist = self._listFields(conn, resdata[1], pri_key)      
         else:
            retlist = []
         retlist[0:0] = ["_ENTIRE_CONTENTS"]
      else:
         retlist = []      
      conn.close()
      return retlist
      
   def joinPath(self, rescollectionpath, resname):
      return rescollectionpath + ":" + resname 
      
   def splitPath(self, respath):
      dsplit = respath.rsplit(":",1)
      return (dsplit[0],dsplit[1])


   """
   Properties and PyFileServer
   ---------------------------
   Properties of a resource refers to the attributes of the resource. A property
   is referenced by the property name and the property namespace. We usually
   refer to the property as ``{property namespace}property name`` 
   
   Properties of resources as defined in webdav falls under three categories:
   
   Live properties
      These properties are attributes actively maintained by the server, such as 
      file size, or read permissions. if you are sharing a database record as a 
      resource, for example, the attributes of the record could become the live 
      properties of the resource.

      The webdav specification defines the following properties that could be
      live properties (refer to webdav specification for details):
      {DAV:}creationdate
      {DAV:}displayname
      {DAV:}getcontentlanguage
      {DAV:}getcontentlength
      {DAV:}getcontenttype
      {DAV:}getetag
      {DAV:}getlastmodified
      {DAV:}resourcetype
      {DAV:}source
   
      These properties are implemented by the abstraction layer.
   
   Locking properties 
      They refer to the two webdav-defined properties 
      {DAV:}supportedlock and {DAV:}lockdiscovery
       
      These properties are implemented by the locking library in
      ``pyfileserver.locklibrary`` and dead properties library in
      ``pyfileserver.propertylibrary``
         
   Dead properties
      They refer to arbitrarily assigned properties not actively maintained. 
   
      These properties are implemented by the dead properties library in
      ``pyfileserver.propertylibrary``
   
   """

   def writeProperty(self, respath, propertyname, propertyns, propertyvalue):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_CONFLICT)               

   def removeProperty(self, respath, propertyname, propertyns):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_CONFLICT)               

   def getProperty(self, respath, propertyname, propertyns):
      if propertyns == 'DAV:':
         if propertyname == 'creationdate':
             return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(0))
         elif propertyname == 'getcontenttype':
             return self.getContentType(respath)
         elif propertyname == 'resourcetype':
            if self.isCollection(respath):
               return '<D:collection />'            
            else:
               return ''   

      resdata = respath.strip(":").split(":")
      if len(resdata) == 3:
         if propertyns == resdata[1] + ":":
            conn = self._initConnection()
            fieldlist = self._getFieldList(conn, resdata[1])
            if propertyname in fieldlist:
               val = self._getFieldByPrimaryKey(conn, resdata[1], resdata[2], propertyname)
               conn.close()
               return val
            conn.close()
      raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)               
   
   def isPropertySupported(self, respath, propertyname, propertyns):
      supportedliveprops = ['creationdate', 'getcontenttype','resourcetype']
      if propertyns == "DAV:" and propertyname in supportedliveprops:
         return True      

      resdata = respath.strip(":").split(":")
      if len(resdata) == 3:
         conn = self._initConnection()
         fieldlist = self._getFieldList(conn, resdata[1])
         conn.close()
         ns = resdata[1] + ":"
         if propertyns == ns and propertyname in fieldlist:
            return True

      return False
   
   def getSupportedPropertyNames(self, respath):
      appProps = []
      #DAV properties for all resources
      appProps.append( ('DAV:','creationdate') )
      appProps.append( ('DAV:','getcontenttype') )
      appProps.append( ('DAV:','resourcetype') )

      resdata = respath.strip(":").split(":")
      if len(resdata) == 3:
         conn = self._initConnection()
         fieldlist = self._getFieldList(conn, resdata[1])
         ns = resdata[1] + ":"
         for fieldname in fieldlist:
            appProps.append( (ns,fieldname) )
         conn.close()
      return appProps
