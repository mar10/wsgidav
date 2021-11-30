# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import importlib.metadata
import sys

package_root = os.path.abspath("../..")
sys.path.insert(0, package_root)

on_rtd = os.environ.get("READTHEDOCS", None) == "True"

print(f"on_rtd: {on_rtd}")

# -- Project information -----------------------------------------------------

project = "WsgiDAV"
copyright = "2009-2021 Martin Wendt, 2005 Ho Chun Wei"
author = "Martin Wendt"

# The full version, including alpha/beta/rc tags
# release = "4.0.0"
# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
try:
    # release = pkg_resources.get_distribution("wsgidav").version
    release = importlib.metadata.version("wsgidav")
except importlib.metadata.PackageNotFoundError:
    print("To build the documentation, The distribution information")
    print("has to be available. Either install the package into your")
    print('development environment or run "setup.py develop" to setup the')
    print("metadata. A virtualenv is recommended!")

    print(f"sys.path: {sys.path}")
    print(f"package_root: {package_root}")
    for fn in os.listdir(package_root):
        print("-", fn)
    sys.exit(1)

del importlib.metadata

version = ".".join(release.split(".")[:2])


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.graphviz",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.napoleon",
    # 'sphinx_automodapi.automodapi',
    # 'sphinx_search.extension',
]

# Included at the beginning of every file:
# rst_prolog = """
# .. important ::

#     You are looking at the documentation for the pre-release 3.x with breaking changes. |br|
#     The current `stable version is 2.x </en/stable/>`_.
# """

# A string of reStructuredText that will be included at the end of every source file that is read.
# This is the right place to add substitutions that should be available in every file:
rst_epilog = """
.. |br| raw:: html

   <br />

.. |nbsp| unicode:: 0xA0
   :trim:

"""

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


autodoc_mock_imports = [
    "bson",
    "couchdb",
    "jinja2",
    "mercurial",
    "MySQLdb",
    "pam",
    "pymongo",
    "redis",
    "win32net",
    "win32netcon",
    "win32security",
]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = "alabaster"

if not on_rtd:
    # only import and set the theme if we're building docs locally
    # otherwise, readthedocs.org uses their theme by default, so no need to specify it
    import sphinx_rtd_theme

    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# -- Extension configuration -------------------------------------------------

# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True
