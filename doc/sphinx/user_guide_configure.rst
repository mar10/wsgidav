=============
Configuration
=============

*This document describes the configuration options of a WsgiDAV server.*


.. toctree::
   :maxdepth: 1


The configuration file uses Python syntax to specify these options:

  * Server options (hostname, port, SSL cert, ...)
  * List of share-name / WebDAV provider mappings
  * List of users for authentication
  * Optional custom DAV providers (i.e. other than `FilesystemProvider`)
  * Optional custom lock manager, property manager and domain controller
  * Advanced debugging options
  * (and more)

The options described below can be defined for the CLI either

  * in Python syntax inside a wsgidav.conf file, or
  * in JSON syntax inside a wsgidav.json file

.. note::
   The same options can be passed as native Python dict to the
   :class:`~wsgidav.wsgidav_app.WsgiDAVApp` contructor, when using the library.


Verbosity Level
---------------

.. todo:: TODO

..
  The verbosity level can have a value from 0 to 6::

      0: quiet
      1: show errors only
      2: show conflicts and 1 line summary only
      3: show write operations
      4: show equal files
      5: diff-info and benchmark summary


Sample ``wsgidav.conf``
-----------------------

.. literalinclude:: ../annotated_wsgidav.conf
    :linenos:
    :language: python


Sample ``wsgidav.json``
-----------------------

You can also use a JSON file for configuration if you don't require the
full power of python code to set everything up.

.. literalinclude:: ../../wsgidav.json.sample
    :linenos:
    :language: json
