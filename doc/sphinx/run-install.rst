********************
 Installing WsgiDAV 
********************

This document describes, how a WsgiDAV server is installed.

See also separate documents for information on :doc:`run-configure` and 
:doc:`run-access`.

WsgiDAV server was tested with these operating systems:
  * Linux (Ubuntu)
  * Windows (Vista, XP)


.. toctree::
   :maxdepth: 1


Preconditions
=============

WsgiDAV requires
  * Python version 2.4 or later
  * Optionally `lxml <http://codespeak.net/lxml/>`_ (on Python 2.5 it will fall 
    back to xml)
  * Optionally `Mercurial <http://mercurial.selenic.com/>`_ (only when checking 
    out source code from the repository)


Details
=======
Unix / Linux
------------
The following examples were tested on Ubuntu 8.04.

Install mercurial (optional) and lxml (optional):: 

    ~$ sudo apt-get install mercurial
    ~$ sudo apt-get install python-lxml


Install the latest release::

    ~$ sudo easy_install -U wsgidav

.. note:: during the beta-phase, this will not always give you an up-to-date 
          version.

So it's recommended to checkout the latest WsgiDAV sources instead::

    ~$ hg clone https://wsgidav.googlecode.com/hg/ wsgidav
    ~$ cd wsgidav/
    ~/wsgidav$ sudo python setup.py develop
    ~/wsgidav$ wsgidav --help


Windows
-------
Install the preconditions, if neccessary.

Then install the latest release::

    > easy_install -U wsgidav

.. note:: during the beta-phase, this will not always give you an up-to-date 
          version.

So it's recommended to checkout the latest WsgiDAV sources instead::

    > hg clone https://wsgidav.googlecode.com/hg/ wsgidav
    > cd wsgidav
    > setup.py develop
    > wsgidav --help
