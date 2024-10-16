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
copyright = "2009-2024 Martin Wendt, 2005 Ho Chun Wei"
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
    'sphinxcontrib.googleanalytics',
    'sphinxcontrib.mermaid',
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
    "cheroot",
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
html_theme = "furo"

# if not on_rtd:
#     # only import and set the theme if we're building docs locally
#     # otherwise, readthedocs.org uses their theme by default, so no need to specify it
#     import sphinx_rtd_theme

#     html_theme = "sphinx_rtd_theme"
#     html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    # See https://pradyunsg.me/furo/customisation/
}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = []
# html_theme = 'bootstrap'
# html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()

googleanalytics_id = 'G-NESEWWF02Y'
# googleanalytics_enabled = False

# MyST Markdown Support
myst_enable_extensions = [
    "dollarmath",
    "amsmath",
    "deflist",
    "fieldlist",
    "html_admonition",
    "html_image",
    "colon_fence",
    "smartquotes",
    "replacements",
    "linkify",
    "strikethrough",
    "substitution",
    "tasklist",
]
myst_number_code_blocks = ["typescript"]
myst_heading_anchors = 2
myst_footnote_transition = True
myst_dmath_double_inline = True

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
# html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
# html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = 'logo.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = "favicon.ico"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
# html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
# html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = False

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
# html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
# html_show_sourcelink = True
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
# html_show_sphinx = True
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Language to be used for generating the HTML full-text search index.
# Sphinx supports the following languages:
#   'da', 'de', 'en', 'es', 'fi', 'fr', 'hu', 'it', 'ja'
#   'nl', 'no', 'pt', 'ro', 'ru', 'sv', 'tr'
# html_search_language = 'en'

# A dictionary with options for the search language support, empty by default.
# Now only 'ja' uses this config value
# html_search_options = {'type': 'default'}

# The name of a javascript file (relative to the configuration directory) that
# implements a search results scorer. If empty, the default will be used.
# html_search_scorer = 'scorer.js'

# Output file base name for HTML help builder.
htmlhelp_basename = "wsgidavdoc"


# -- Extension configuration -------------------------------------------------

# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True
