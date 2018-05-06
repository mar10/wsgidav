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

  * in `YAML <http://yaml.org/spec/1.2/spec.html>`_ syntax inside a wsgidav.yaml file,
  * in `JSON <http://www.json.org>`_ syntax inside a wsgidav.json file, or
  * in Python syntax inside a wsgidav.conf file.

.. note::
   The three supported file formats are just different ways for the CLI to
   generate a Python dict that is then passed to the
   :class:`~wsgidav.wsgidav_app.WsgiDAVApp` constructor.

   See the :ref:`annotated_wsgidav.conf`

   For a start, you should copy
   :download:`Sample Configuration<../../wsgidav.conf.sample>` or
   :download:`Annotated Sample Configuration<../annotated_wsgidav.conf>`
   and edit it to your needs.
   You can also start with a
   (:download:`YAML Sample Configuration<../../wsgidav.yaml.sample>`) or a
   (:download:`JSON Sample Configuration<../../wsgidav.json.sample>`).


Verbosity Level
---------------

The verbosity level can have a value from 0 to 5 (default: 3):

=========  ======  ===========  ======================================================
Verbosity  Option  Log level    Remarks
=========  ======  ===========  ======================================================
  0        -qqq    CRITICAL     quiet
  1        -qq     ERROR        no output (excepting application exceptions)
  2        -q      WARN         warnings and errors only
  3                INFO         show single line request summaries (for HTTP logging)
  4        -v      DEBUG        show additional events
  5        -vv     DEBUG        show full request/response header info (HTTP Logging)
                                request body and GET response bodies not shown
=========  ======  ===========  ======================================================


..
  The verbosity level can have a value from 0 to 3::

        0 - no output (excepting application exceptions)
        1 - show single line request summaries (for HTTP logging)
        2 - show additional events
        3 - show full request/response header info (HTTP Logging)
            request body and GET response bodies not shown


Sample ``wsgidav.yaml``
-----------------------

The `YAML <http://yaml.org/spec/1.2/spec.html>`_ syntax is probably the most
concise format to define configuration:

.. literalinclude:: ../../wsgidav.yaml.sample
    :linenos:


Sample ``wsgidav.json``
-----------------------

We can also use a `JSON <http://www.json.org>`_ file for configuration
if we don't require the full power of Python code to set everything up.

Note that the parser ignores JavaScript-style comments:

.. literalinclude:: ../../wsgidav.json.sample
    :linenos:
    :language: json


Sample ``wsgidav.conf``
-----------------------

This format uses plain Python syntax, which allows us to use Python data structures,
and even write helpers function, etc.

.. literalinclude:: ../annotated_wsgidav.conf
    :linenos:
    :language: python
