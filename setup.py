# If true, then the svn revision won't be used to calculate the
# revision (set to True for real releases)
RELEASE = False

__version__ = "0.2"

from ez_setup import use_setuptools
use_setuptools()


#manual check for dependencies: PyXML - somehow installer unable to find on PyPI.
import sys

print "\nChecking manual dependencies...\n"
try:
   import xml.dom.ext
   import xml.dom.ext.reader
except ImportError:
   print "Failed to detect PyXML. PyXML is required for PyFileServer. Please install"
   print "PyXML <http://pyxml.sourceforge.net/> before installing PyFileServer"
   sys.exit(-1)


from setuptools import setup, find_packages

setup(name="PyFileServer",
      version=__version__,
      description="Python-based WSGI application for file sharing over WebDAV",
      long_description="""\
PyFileServer is a WebDAV server web application for sharing files and 
directories over the web. It is based on the wsgi interface 
<http://www.python.org/peps/pep-0333.html>.

It comes bundled with a simple wsgi webserver. 
""",
      classifiers=["Development Status :: 4 - Beta",
                   "Intended Audience :: Information Technology, Developers, System Administrators",
                   "License :: OSI Approved :: Lesser GNU Public License",
                   "Programming Language :: Python",
                   "Topic :: Internet :: WWW/HTTP :: HTTP Server",
                   ],
      keywords='web wsgi webdav application server',
      author="Ho Chun Wei",
      author_email="fuzzybr80@gmail.com",
      url="http://pyfilesync.berlios.de",
      license="LGPL",
      install_requires = [],
      packages=find_packages(exclude=[]),
      package_data={'': ['*.txt', '*.html', '*.conf']},
      zip_safe=False,
      extras_require={}
      )


