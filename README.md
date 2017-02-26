# ![logo](logo.png?raw=true) WsgiDAV [![Build Status](https://travis-ci.org/mar10/wsgidav.png?branch=master)](https://travis-ci.org/mar10/wsgidav) [![Latest Version](https://img.shields.io/pypi/v/wsgidav.svg)](https://pypi.python.org/pypi/WsgiDAV/) [![Downloads](https://img.shields.io/pypi/dm/wsgidav.svg)](https://pypi.python.org/pypi/WsgiDAV/) [![License](https://img.shields.io/pypi/l/wsgidav.svg)](https://pypi.python.org/pypi/WsgiDAV/)

WsgiDAV is a generic [WebDAV](http://www.ietf.org/rfc/rfc4918.txt) server 
written in Python and based on [WSGI](http://www.python.org/dev/peps/pep-0333/).

Main features:

  - WsgiDAV is a stand-alone WebDAV server with SSL support, that can be 
    installed and run as Python command line script on Linux, OSX, and Windows:<br>
    ```
    $ pip install wsgidav
    $ wsgidav --host=0.0.0.0 --port=8080 --root=/tmp
    WARNING: share '/' will allow anonymous access.
    Running WsgiDAV/2.2.1 CherryPy/unknown Python/3.5.2
    Serving on http://0.0.0.0:8080 ...
    ```

    Run `wsgidav --help` for a list of available options.
  - A binary MSI installer is available for Microsoft Windows.
  - WsgiDAV is also a Python library that implements the WSGI protocol and can
	be run behind any WSGI compliant web server.<br>
  - WsgiDAV is implemented as a configurable stack of WSGI middleware
    applications.<br>
    The open architecture allows to extend the functionality and integrate
    WebDAV services into your project.<br>
	Typical use cases are:
	- Expose data structures as virtual file systems.
	- Allow online editing of MS Office documents.


## Status

[![Latest Version](https://img.shields.io/pypi/v/wsgidav.svg)](https://pypi.python.org/pypi/WsgiDAV/)
See the ([change log](CHANGELOG.md)) for details.

**Note 2016-10-08:** Release 2.0.1 includes a security patch that prevents certain XML
attacks (thanks Tom Viner). We highly recommend to update!


## More info

  * [Read The Docs](http://wsgidav.rtfd.org) for details.
  * [Discussion Group](https://groups.google.com/forum/#!forum/wsgidav)
  * [Stackoverflow](http://stackoverflow.com/questions/tagged/wsgidav)


## Credits

Contributors:

  * <https://github.com/mar10/wsgidav/contributors>
  * Markus Majer for providing the logo (a mixture of the international 
    maritime signal flag for 'W (Whiskey)' and a dove.)


Any kind of feedback is very welcome!<br>
Have fun  :-)<br>
Martin
