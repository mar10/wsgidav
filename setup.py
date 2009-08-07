# If true, then the svn revision won't be used to calculate the
# revision (set to True for real releases)
RELEASE = False

from wsgidav.version import __version__

from ez_setup import use_setuptools
use_setuptools()



#manual check for dependencies: PyXML - somehow installer unable to find on PyPI.
#import sys
#try:
#    from lxml import etree  #@UnusedImport
#except ImportError:
#    print "Failed to detect lxml. lxml is required for WsgiDAV. Please install"
#    print "lxml <http://codespeak.net/lxml/> before installing WsgiDAV"
#    sys.exit(-1)


from setuptools import setup, find_packages

setup(name="WsgiDAV",
      version = __version__,
      author = "Ho Chun Wei, Martin Wendt",
      author_email = "wsgidav@wwwendt.de",
      maintainer = "Martin Wendt",
      maintainer_email = "wsgidav@wwwendt.de",
      url = "http://wsgidav.googlecode.com/",
      description = "Generic WebDAV server based on WSGI",
      long_description="""\
WsgiDAV is a WebDAV server for sharing files and other resources over the web. 
It is based on the WSGI interface <http://www.python.org/peps/pep-0333.html>.

It comes bundled with a simple WSIG web server.

*This package is based on PyFileServer by Ho Chun Wei.*

Project home: http://wsgidav.googlecode.com/  
""",

        #Development Status :: 2 - Pre-Alpha
        #Development Status :: 3 - Alpha
        #Development Status :: 4 - Beta
        #Development Status :: 5 - Production/Stable

      classifiers = ["Development Status :: 3 - Alpha",
                     "Intended Audience :: Information Technology",
                     "Intended Audience :: Developers",
                     "Intended Audience :: System Administrators",
                     "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
                     "Operating System :: OS Independent",
                     "Programming Language :: Python",
                     "Topic :: Internet :: WWW/HTTP",
                     "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
                     "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
                     "Topic :: Internet :: WWW/HTTP :: WSGI",
                     "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
                     "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
                     "Topic :: Software Development :: Libraries :: Python Modules",
                     ],
      keywords = 'web wsgi webdav application server', 
#      platforms=['Unix', 'Windows'],
      license = "LGPL",
      install_requires = ["lxml"],
      packages = find_packages(exclude=[]),
#      package_data={'': ['*.txt', '*.html', '*.conf']},
#      include_package_data = True, # TODO: PP
      zip_safe = False,
      extras_require = {},
      entry_points = {
          "console_scripts" : ["wsgidav = wsgidav.server.run_server:run"],
          },
      # TODO: PP:
#      entry_points = """
#      [paste.app_factory]
#      main = wsgidav.wsgiapp:make_app
#      """,
      )
