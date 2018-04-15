===========
Development
===========

This section describes how developers can *contribute* to the WsgiDAV project.


.. toctree::
   :maxdepth: 1


Install for Development
=======================

First off, thanks for taking the time to contribute!

This small guideline may help taking the first steps.

Happy hacking :)


Fork the Repository
-------------------

Clone WsgiDAV to a local folder and checkout the branch you want to work on::

    $ git clone git@github.com:mar10/wsgidav.git
    $ cd wsgidav
    $ git checkout my_branch

..
    If you want to participate, check it out from the repository ::

      $ git clone https://github.com/mar10/wsgidav.git wsgidav
      $ cd wsgidav
      $ setup.py develop
      $ setup.py test
      $ wsgidav --help


Work in a Virtual Environment
-----------------------------

Install Python
^^^^^^^^^^^^^^
We need `Python 2.7 <https://www.python.org/downloads/>`_,
`Python 3.4+ <https://www.python.org/downloads/>`_,
and `pip <https://pip.pypa.io/en/stable/installing/#do-i-need-to-install-pip>`_ on our system.

If you want to run tests on *all* supported platforms, install Python 2.7, 3.4,
3.5, and 3.6.

Create and Activate the Virtual Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Linux / macOS
"""""""""""""
On Linux/OS X, we recommend to use `pipenv <https://github.com/kennethreitz/pipenv>`_
to make this easy::

    $ cd /path/to/wsgidav
    $ pipenv shell
    bash-3.2$

Windows
"""""""
Alternatively (especially on Windows), use `virtualenv <https://virtualenv.pypa.io/en/latest/>`_
to create and activate the virtual environment.
For example using Python's builtin ``venv`` (instead of ``virtualenvwrapper``)
in a Windows PowerShell::

    > cd /path/wsgidav
    > py -3.6 -m venv c:\env\wsgidav_py36
    > c:\env\wsgidav_py36\Scripts\Activate.ps1
    (wsgidav_py36) $

Install Requirements
^^^^^^^^^^^^^^^^^^^^
Now that the new environment exists and is activated, we can setup the
requirements::

    $ pip install -r requirements-dev.txt

and install wsgidav to run from source code::

    $ pip install -e .

..    $ python setup.py develop

The code should now run::

    $ wsgidav --version
    $ 2.3.1

The test suite should run as well::

    $ python setup.py test
    $ pytest -v -rs

Build Sphinx documentation::

    $ python setup.py sphinx


Run Tests
=========

The unit tests create fixtures in a special folder. By default, a temporary folder
is created on every test run, but it is recommended to define a location using the
``PYFTPSYNC_TEST_FOLDER`` environment variable, for example::

    export PYFTPSYNC_TEST_FOLDER=/Users/USER/pyftpsync_test

Run all tests with coverage report. Results are written to <pyftpsync>/htmlcov/index.html::

    $ pytest -v -rsx --cov=ftpsync --cov-report=html

Run selective tests::

    $ pytest -v -rsx -k FtpBidirSyncTest
    $ pytest -v -rsx -k "FtpBidirSyncTest and test_default"
    $ pytest -v -rsx -m benchmark

Run tests on multiple Python versions using `tox <https://tox.readthedocs.io/en/latest/#>`_
(need to install those Python versions first)::

    $ tox
    $ tox -e py36

In order to run realistic tests through an FTP server, we need a setup that publishes
a folder that is also accessible using file-system methods.

This can be achieved by configuring an FTP server to allow access to the `remote`
folder::

  <PYFTPSYNC_TEST_FOLDER>/
    local/
      folder1/
        file1_1.txt
        ...
      file1.txt
      ...
    remote/  # <- FTP server should publish this folder as <PYFTPSYNC_TEST_FTP_URL>
      ...

The test suite checks if ``PYFTPSYNC_TEST_FTP_URL`` is defined and accessible.
Otherwise FTP tests will be skipped.

For example, environment variables may look like this, assuming the FTP server is rooted
at the user's home directory::

    export PYFTPSYNC_TEST_FOLDER=/Users/USER/pyftpsync_test
    export PYFTPSYNC_TEST_FTP_URL=ftp://USER:PASSWORD@localhost/pyftpsync_test/remote

This environment variable may be set to generate ``.pyftpsync-meta`` files in a
larger, but more readable format::

    export PYFTPSYNC_VERBOSE_META=True


Code
====

.. note::

    	Follow the Style Guide, basically
        `PEP 8 <https://www.python.org/dev/peps/pep-0008/>`_.

        Failing tests or not follwing PEP 8 will break builds on
        `travis <https://travis-ci.org/mar10/pyftpsync>`_,
        so run ``$ pytest`` and ``$ flake8`` frequently and before you commit!


Create a Pull Request
=====================

.. todo::

    	TODO
