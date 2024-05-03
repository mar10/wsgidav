#!/usr/bin/env python

# NOTE: isort must not change this import order:
# isort: skip_file

import os
import re
import sys

from setuptools import find_packages, setup
from cx_Freeze import setup, Executable  # noqa re-import setup

from wsgidav import __version__

# Check for Windows MSI Setup
if "bdist_msi" not in sys.argv:  # or len(sys.argv) != 2:
    raise RuntimeError(
        "This setup.py variant is only for creating 'bdist_msi' targets: {}\n"
        "Example `{} bdist_msi`".format(sys.argv, sys.argv[0])
    )

org_version = __version__

# Since we included pywin32 extensions, cx_Freeze tries to create a
# version resource. This only supports the 'a.b.c[.d]' format.
# Our version has either the for '1.2.3' or '1.2.3-a1'
unsafe_version = False
major, minor, patch = org_version.split(".", 3)
major = int(major)
minor = int(minor)
if "-" in patch:
    # We have a pre-release version, e.g. '1.2.3-a1'.
    # This is presumably a post-release increment after '1.2.2' release.
    # It must NOT be converted to '1.2.3.1', since that would be *greater*
    # than '1.2.3', which is not even released yet.
    # Approach 1:
    #     We cannot guarantee that '1.2.2.1' is correct either, so for
    #     pre-releases we assume '0.0.0.0':
    # major = minor = patch = alpha = 0
    # Approach 2:
    #     '1.2.3-a1' was presumably a post-release increment after '1.2.2',
    #     so assume '1.2.2.1':
    patch, alpha = patch.split("-", 1)
    patch = int(patch)
    # Remove leading letters
    alpha = re.sub("^[a-zA-Z]+", "", alpha)
    alpha = int(alpha)
    if unsafe_version and patch >= 1:
        patch -= 1  # 1.2.3-a1 => 1.2.2.1
    else:
        # may be 1.2.0-a1 or 2.0.0-a1: we don't know what the previous release was
        major = minor = patch = alpha = 0
else:
    patch = int(patch)
    alpha = 0

version = "{}.{}.{}.{}".format(major, minor, patch, alpha)
print("Version {}, using {}".format(org_version, version))

try:
    readme = open("README.md", "rt").read()
except IOError:
    readme = "(readme not found. Running from tox/setup.py test?)"

# These dependencies are for plain WsgiDAV:
# NOTE: Only need to list requirements that are not discoverable by scanning
#       the main package. For example due to dynamic or optional imports.
# Also, cx_Freeze may have difficulties with packages listed here, e.g. PpyYAML:
#    https://github.com/marcelotduarte/cx_Freeze/issues/1541
install_requires = []
# ... The Windows MSI Setup should include lxml and CherryPy
install_requires.extend(
    [
        "cheroot",
        "lxml",
    ]
)
setup_requires = install_requires
tests_require = []

executables = [
    Executable(
        script="wsgidav/server/server_cli.py",
        base=None,
        # base="Win32GUI",
        target_name="wsgidav.exe",
        icon="docs/source/logo.ico",
        shortcut_name="WsgiDAV",
        copyright="(c) 2009-2024 Martin Wendt",
        # trademarks="...",
    )
]

# See https://cx-freeze.readthedocs.io/en/latest/distutils.html#build-exe
build_exe_options = {
    "includes": install_requires,
    # "include_files": [],
    "packages": [
        "asyncio",  # https://stackoverflow.com/a/41881598/19166
        "cheroot",
        "dbm",
        "wsgidav.dir_browser",
        "wsgidav.dc.nt_dc",
    ],
    "excludes": [
        "tkinter",
    ],
    "constants": "BUILD_COPYRIGHT='(c) 2009-2024 Martin Wendt'",
    # "init_script": "Console",
    "include_msvcr": True,
}

# See https://cx-freeze.readthedocs.io/en/latest/distutils.html#bdist-msi
bdist_msi_options = {
    "upgrade_code": "{92F74137-38D1-48F6-9730-D5128C8B611E}",
    "add_to_path": True,
    # "all_users": True,
    "install_icon": "docs/source/logo.ico",
    # "summary_data": {"author": "Martin Wendt"},
}

setup(
    name="WsgiDAV",
    version=version,
    author="Martin Wendt",
    author_email="wsgidav@wwwendt.de",
    maintainer="Martin Wendt",
    maintainer_email="wsgidav@wwwendt.de",
    url="https://github.com/mar10/wsgidav/",
    description="Generic and extendable WebDAV server based on WSGI",
    long_description=readme,
    long_description_content_type="text/markdown",
    classifiers=[],  # not required for this build-only setup config
    keywords="web wsgi webdav application server",
    license="MIT",
    packages=find_packages(exclude=["tests"]),
    package_data={
        # If any package contains *.txt files, include them:
        # "": ["*.css", "*.html", "*.ico", "*.js"],
        "wsgidav.dir_browser": ["htdocs/*.*"]
    },
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    py_modules=[],
    zip_safe=False,
    extras_require={},
    # cmdclass={"test": ToxCommand, "sphinx": SphinxCommand},
    entry_points={"console_scripts": ["wsgidav = wsgidav.server.server_cli:run"]},
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    # Used by cx_Freeze:
    executables=executables,
)
