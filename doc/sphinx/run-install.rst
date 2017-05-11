********************
 Installing WsgiDAV 
********************

This document describes, how a WsgiDAV server is installed.

WsgiDAV server was tested with these operating systems:
  * Linux (Ubuntu 13)
  * Mac OS X 10.9
  * Windows (Win7, Vista, XP)

.. toctree::
   :maxdepth: 1


Preconditions
=============

WsgiDAV requires
  * Python version 2.7, 3.3 or later
  * Optionally `lxml <http://codespeak.net/lxml/>`_ (will fall back to xml)


Details
=======
Unix / Linux
------------
The following examples were tested on Ubuntu 13.04.

Install lxml (optional):: 

    ~$ sudo apt-get install python-lxml


Install the latest release::

    ~$ sudo pip install -U wsgidav

or install the latest (potentially unstable) development version::

    ~$ pip install git+https://github.com/mar10/wsgidav.git

If you want to participate, check it out from the repository ::

  $ git clone https://github.com/mar10/wsgidav.git wsgidav
  $ cd wsgidav
  $ setup.py develop
  $ setup.py test
  $ wsgidav --help


Windows
-------
Install the preconditions, if neccessary.
Basically the same as for `Unix / Linux`_
