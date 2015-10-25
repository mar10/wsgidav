#!/usr/bin/env python

from __future__ import print_function

import os
import sys

# If true, then the DVCS revision won't be used to calculate the
# revision (set to True for real releases)
# RELEASE = False

# from wsgidav.version import __version__

# from ez_setup import use_setuptools
# use_setuptools()
# from setuptools import setup, find_packages

from setuptools import setup
from setuptools.command.test import test as TestCommand


# Override 'setup.py test' command
class Tox(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        # Import here, cause outside the eggs aren't loaded
        import tox
        errcode = tox.cmdline(self.test_args)
        sys.exit(errcode)


# Override 'setup.py test' command
# class PyTest(TestCommand):
#      def finalize_options(self):
#          TestCommand.finalize_options(self)
#          self.test_args = []
#          self.test_suite = True
#      def run_tests(self):
#          import pytest
#          errcode = pytest.main(self.test_args)
#          sys.exit(errcode)


# TODO: Add support for 'setup.py sphinx'
#       see http://stackoverflow.com/a/22273180/19166

try:
    from cx_Freeze import setup, Executable
    executables = [
        Executable("wsgidav/server/run_server.py")
        ]
except ImportError:
    # tox has problems to install cx_Freeze to it's venvs, but it is not needed
    # for the tests anyway
    print("Could not import cx_Freeze; 'build' and 'bdist' commands will not be available.")
    print("See https://pypi.python.org/pypi/cx_Freeze")
    executables = []

# Get description and __version__ without using import
readme = open("readme_pypi.rst", "rt").read()

g_dict = {}
exec(open("wsgidav/_version.py").read(), g_dict)
version = g_dict["__version__"]

# 'setup.py upload' fails on Vista, because .pypirc is searched on 'HOME' path
if not "HOME" in os.environ and  "HOMEPATH" in os.environ:
    os.environ.setdefault("HOME", os.environ.get("HOMEPATH", ""))
    print("Initializing HOME environment variable to '%s'" % os.environ["HOME"])

install_requires = [#"colorama",
                    #"keyring",
                    ]
tests_require = ["pytest",
                 "pytest-cov",
                 "tox",
                 "webtest",
                 ]

if sys.version_info < (2, 7):
    install_requires += ["argparse"]
    tests_require += ["unittest2"]

setup_requires = install_requires

build_exe_options = {
    # "init_script": "Console",
    "includes": install_requires,
    "packages": [#"keyring.backends",  # loaded dynamically
                 ],
    # "constants": "BUILD_COPYRIGHT=(c) 2012-2015 Martin Wendt",
    }

bdist_msi_options = {
    "upgrade_code": "{92F74137-38D1-48F6-9730-D5128C8B611E}",
    "add_to_path": True,
#   "initial_target_dir": r"[ProgramFilesFolder]\%s\%s" % (company_name, product_name),
    }


setup(name="WsgiDAV",
      version = version,
      author = "Martin Wendt, Ho Chun Wei",
      author_email = "wsgidav@wwwendt.de",
      maintainer = "Martin Wendt",
      maintainer_email = "wsgidav@wwwendt.de",
      url = "https://github.com/mar10/wsgidav/",
      description = "Generic WebDAV server based on WSGI",
      long_description = readme,

        #Development Status :: 2 - Pre-Alpha
        #Development Status :: 3 - Alpha
        #Development Status :: 4 - Beta
        #Development Status :: 5 - Production/Stable

      classifiers = ["Development Status :: 3 - Alpha",
                     "Intended Audience :: Information Technology",
                     "Intended Audience :: Developers",
                     "Intended Audience :: System Administrators",
                     "License :: OSI Approved :: MIT License",
                     "Operating System :: OS Independent",
                     "Programming Language :: Python :: 2",
                     "Programming Language :: Python :: 3",
                     "Topic :: Internet :: WWW/HTTP",
                     "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
                     "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
                     "Topic :: Internet :: WWW/HTTP :: WSGI",
                     "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
                     "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
                     "Topic :: Software Development :: Libraries :: Python Modules",
                     ],
      keywords = "web wsgi webdav application server",
#      platforms=["Unix", "Windows"],
      license = "The MIT License",
#      install_requires = ["lxml"],
      # packages = find_packages(exclude=[]),
      install_requires = install_requires,
      setup_requires = setup_requires,
      tests_require = tests_require,
      py_modules = [#"ez_setup", 
                    ],

#      package_data={"": ["*.txt", "*.html", "*.conf"]},
#      include_package_data = True, # TODO: PP
      zip_safe = False,
      extras_require = {},
      # tests_require = ["nose",   # run nosetests
      #                  "Paste",  # paste.fixture.TestApp
      #                  ],
      # test_suite = "nose.collector",
      cmdclass = {"test": Tox},
      entry_points = {
          "console_scripts" : ["wsgidav = wsgidav.server.run_server:run"],
          },
      # TODO: PP:
#      entry_points = """
#      [paste.app_factory]
#      main = wsgidav.wsgiapp:make_app
#      """,
      executables = executables,
      options = {"build_exe": build_exe_options,
                 "bdist_msi": bdist_msi_options,
                 }
      )
