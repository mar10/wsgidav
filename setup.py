#!/usr/bin/env python

from __future__ import print_function

import os
import sys

# If true, then the DVCS revision won't be used to calculate the
# revision (set to True for real releases)
# RELEASE = False

from setuptools import setup, find_packages
from setuptools import Command
from setuptools.command.test import test as TestCommand

from wsgidav._version import __version__


# Override 'setup.py test' command
class ToxCommand(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # Import here, cause outside the eggs aren't loaded
        import tox
        errcode = tox.cmdline(self.test_args)
        sys.exit(errcode)


# Add custom command 'setup.py sphinx'
# See https://dankeder.com/posts/adding-custom-commands-to-setup-py/
# and http://stackoverflow.com/a/22273180/19166
class SphinxCommand(Command):
    user_options = []
    description = "Build docs using Sphinx"

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess
        res = subprocess.call("sphinx-build -b html doc/sphinx doc/sphinx-build", shell=True)
        outdir = os.path.join("doc", "sphinx-build")
        if res:
            print("ERROR: sphinx-build exited with code {}".format(res))
        else:
            print("Documentation created at {}.".format(os.path.abspath(outdir)))


try:
    # readme = open("readme_pypi.rst", "rt").read()
    readme = open("README.md", "rt").read()
except IOError:
    readme = "(Readme file not found. Running from tox/setup.py test?)"

# 'setup.py upload' fails on Vista, because .pypirc is searched on 'HOME' path
if "HOME" not in os.environ and "HOMEPATH" in os.environ:
    os.environ.setdefault("HOME", os.environ.get("HOMEPATH", ""))
    print("Initializing HOME environment variable to '{}'".format(os.environ["HOME"]))

# CherryPy is required for the tests and benchmarks. It is also the preferrred
# server for the stand-alone mode (`wsgidav.server.server_cli.py`).
# We currently do not add it as an installation requirement, because
#   1. users may not need the command line server at all
#   2. users may prefer another server
#   3. there may already cherrypy versions installed

install_requires = [
    "defusedxml",
    "jsmin",
    "PyYAML",
    # "defusedxml~=0.5",
    # "jsmin~=2.2",
    # "PyYAML~=3.2",
    ]

# The Windows MSI Setup should include lxml and CherryPy
if "bdist_msi" in sys.argv:
    install_requires.extend([
        "cheroot",
        "lxml",
        ])

tests_require = [
    # "cheroot",
    # "flake8",
    # "pytest",
    # "pytest-cov",
    # "tox",
    # "webtest",
    ]

setup_requires = install_requires

use_cx_freeze = False
for cmd in ["bdist_msi"]:
    if cmd in sys.argv:
        use_cx_freeze = True
        break

if use_cx_freeze:
    try:
        # cx_Freeze seems to be confused by module name 'PyYAML' which
        # must be imported as 'yaml', so we rename here. However it must
        # be listed as 'PyYAML' in the requirements.txt and be installed!
        install_requires.remove("PyYAML")
        install_requires.append("yaml")

        from cx_Freeze import setup, Executable  # noqa F811
        executables = [
            Executable(script="wsgidav/server/server_cli.py",
                       base=None,
                       # base="Win32GUI",
                       targetName="wsgidav.exe",
                       icon="doc/logo.ico",
                       shortcutName="WsgiDAV",
                       # requires cx_Freeze PR#94:
                       # copyright="(c) 2009-2018 Martin Wendt",
                       # trademarks="...",
                       )
            ]
    except ImportError:
        # tox has problems to install cx_Freeze to it's venvs, but it is not
        # needed for the tests anyway
        print("Could not import cx_Freeze; 'build' and 'bdist' commands will not be available.")
        print("See https://pypi.python.org/pypi/cx_Freeze")
        executables = []
else:
    print("Did not import cx_Freeze, because 'bdist_msi' commands are not used ({})."
          .format(sys.argv))
    print("NOTE: this is a hack, because cx_Freeze seemed to sabotage wheel creation")
    executables = []


build_exe_options = {
    "includes": install_requires,
    "packages": [],
    "constants": "BUILD_COPYRIGHT='(c) 2009-2018 Martin Wendt'",
    # "init_script": "Console",
    }

bdist_msi_options = {
    "upgrade_code": "{92F74137-38D1-48F6-9730-D5128C8B611E}",
    "add_to_path": True,
    # TODO: configure target dir
    # "initial_target_dir": r"[ProgramFilesFolder]\%s\%s" % (company_name, product_name),
    # TODO: configure shortcuts:
    # http://stackoverflow.com/a/15736406/19166
    }

setup(
    name="WsgiDAV",
    version=__version__,
    author="Martin Wendt, Ho Chun Wei",
    author_email="wsgidav@wwwendt.de",
    maintainer="Martin Wendt",
    maintainer_email="wsgidav@wwwendt.de",
    url="https://github.com/mar10/wsgidav/",
    description="Generic and extendable WebDAV server based on WSGI",
    long_description=readme,
    long_description_content_type="text/markdown",
    classifiers=[
        # Development Status :: 2 - Pre-Alpha
        # Development Status :: 3 - Alpha
        # Development Status :: 4 - Beta
        # Development Status :: 5 - Production/Stable
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
    keywords="web wsgi webdav application server",
    license="MIT",
    packages=find_packages(exclude=["tests"]),
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    py_modules=[],
    zip_safe=False,
    extras_require={},
    cmdclass={
        "test": ToxCommand,
        "sphinx": SphinxCommand,
        },
    entry_points={
        "console_scripts": ["wsgidav = wsgidav.server.server_cli:run"],
        },
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
        },
    executables=executables,
    )
