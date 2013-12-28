**************************
 Writing custom providers
**************************

.. note::
   This documentation is under construction.
 
.. toctree::
   :maxdepth: 1


test - automodule
-----------------
.. automodule:: wsgidav.dav_provider

test - autoclass
----------------
This 

.. autoclass:: wsgidav.dav_provider.DAVResource
   :members: getContentLanguage, getContentLength, getContentType,
             getCreationDate, getDisplayName, getEtag,
             getLastModified, displayType, supportRanges,
             getMemberNames, getPropertyNames, getPropertyValue

test - autoclass
----------------
Minimum required members to implement.

.. autoclass:: wsgidav.dav_provider.DAVProvider
   :members: getResourceInst
  