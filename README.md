# ![logo](https://raw.githubusercontent.com/mar10/wsgidav/master/docs/logo.png) WsgiDAV
[![Build Status](https://travis-ci.org/mar10/wsgidav.svg?branch=master)](https://travis-ci.org/mar10/wsgidav)
[![Latest Version](https://img.shields.io/pypi/v/wsgidav.svg)](https://pypi.python.org/pypi/WsgiDAV/)
[![License](https://img.shields.io/pypi/l/wsgidav.svg)](https://github.com/mar10/wsgidav/blob/master/LICENSE)
[![Documentation Status](https://readthedocs.org/projects/wsgidav/badge/?version=latest)](http://wsgidav.readthedocs.io/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Released with: Yabs](https://img.shields.io/badge/released%20with-yabs-yellowgreen)](https://github.com/mar10/yabs)
[![StackOverflow: WsgiDAV](https://img.shields.io/badge/StackOverflow-WsgiDAV-blue.svg)](https://stackoverflow.com/questions/tagged/WsgiDAV)

A generic and extendable [WebDAV](http://www.ietf.org/rfc/rfc4918.txt) server
written in Python and based on [WSGI](http://www.python.org/dev/peps/pep-3333/).

Main features:

  - WsgiDAV is a stand-alone WebDAV server with SSL support, that can be
    installed and run as Python command line script on Linux, OSX, and Windows:<br>
    ```
    $ pip install wsgidav cheroot
    $ wsgidav --host=0.0.0.0 --port=8080 --root=/tmp
    WARNING: share '/' will allow anonymous access.
    Running WsgiDAV/2.2.2 Cheroot/5.5.0 Python/3.4.2
    Serving on http://0.0.0.0:8080 ...
    ```
    Run `wsgidav --help` for a list of available options.<br>
    **Note:** The syntax changed slightly with v3.0.
  - **Note:** python-pam is needed if using pam-login on Linux or OSX:
    ```
    $ pip install python-pam
    $ wsgidav --auth=pam-login --host=0.0.0.0 --port=8080 --root=/tmp
    ```
  - **Note:** Windows users may prefer the
    [MSI Installer](https://github.com/mar10/wsgidav/releases/latest)
    (see <kbd>Assets</kbd> section).
  - WebDAV is a superset of HTTP, so WsgiDAV is also a performant, multi-threaded
    web server with SSL support.
  - WsgiDAV is also a Python library that implements the WSGI protocol and can
	  be run behind any WSGI compliant web server.<br>
  - WsgiDAV is implemented as a configurable stack of WSGI middleware
    applications.<br>
    Its open architecture allows to extend the functionality and integrate
    WebDAV services into your project.<br>
  	Typical use cases are:
  	- Expose data structures as virtual, editable file systems.
  	- Allow online editing of MS Office documents.


## Status

[![Latest Version](https://img.shields.io/pypi/v/wsgidav.svg)](https://pypi.python.org/pypi/WsgiDAV/)
See the ([change log](https://github.com/mar10/wsgidav/blob/master/CHANGELOG.md)) for details.

**Note:** Release 3.0 introduces some refactorings and breaking changes.<br>
  See the ([change log](https://github.com/mar10/wsgidav/blob/master/CHANGELOG.md)) for details.


## More info

  * [Read The Docs](http://wsgidav.rtfd.org) for details.
  * [Discussion Group](https://groups.google.com/forum/#!forum/wsgidav)
  * [Stackoverflow](http://stackoverflow.com/questions/tagged/wsgidav)


## Credits

Contributors:

  * WsgiDAV is a [refactored version](https://github.com/mar10/wsgidav/blob/master/docs/changelog04.md)
    of [PyFileServer 0.2](https://github.com/cwho/pyfileserver),
    Copyright (c) 2005 Ho Chun Wei.<br>
    Chun gave his approval to change the license from LGPL to MIT-License for
    this project.
  * <https://github.com/mar10/wsgidav/contributors>
  * Markus Majer for providing the logo (a mixture of the international
    maritime signal flag for 'W (Whiskey)' and a dove.)


Any kind of feedback is very welcome!<br>
Have fun  :-)<br>
Martin
