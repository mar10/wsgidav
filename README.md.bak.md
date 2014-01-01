![logo](https://raw.github.com/mar10/wsgidav/master/logo.png)

WsgiDAV is a generic [WebDAV](http://www.ietf.org/rfc/rfc4918.txt) server 
written in Python and based on [http://www.python.org/dev/peps/pep-0333/ WSGI].

### Status
1.1.0 is released. 

### Documentation
[Read The Docs](http://wsgidav.rtfd.org).


WsgiDAV is a 
[refactored version of PyFileServer](https://github.com/mar10/wsgidav/blob/master/doc/changelog04.md)
written by Ho Chun Wei.

WsgiDAV is designed to run behind any WSGI compliant server, but it also comes 
bundled with a server, so you can start right away from the command line.<br>
A file system provider is included, but the architecture allows to write custom 
providers as well.<br>
WsgiDAV contains a simple web interface and was tested with different clients.


See also the [Change Log](https://github.com/mar10/wsgidav/blob/master/CHANGELOG.md).


### Quickstart
Releases are hosted on [https://pypi.python.org/pypi/WsgiDAV PyPI]. Install like
```
> pip install -U wsgidav
> wsgidav --host=0.0.0.0 --port=80 --root=/tmp
```
See also [http://docs.wsgidav.googlecode.com/hg/html/run.html running WsgiDAV].

Or install the latest (potentially unstable) development version:
```
> pip install git+https://github.com/mar10/wsgidav.git
```

If you want to participate, check it out from the repository:

```
> git clone https://github.com/mar10/wsgidav.git wsgidav
> cd wsgidav
> setup.py develop
> wsgidav --help
```

Python 2.4 or later is required.

### Supported Clients

WsgiDAV comes with a web interface and was tested with different clients 
(Windows File Explorer and drive mapping, MS Office, Ubuntu, Mac OS X, ...). 
Read the docs for details.

![teaser](https://raw.github.com/mar10/wsgidav/master/doc/teaser.png)


### More info

Please read the [Read The Docs](wsgidav.rtfd.org) for details.

Any kind of feedback is very welcome!<br>
Have fun  :-)<br>
Martin
