===========
Development
===========

This section describes how developers can *contribute* to the WsgiDAV project.

.. toctree::
   :maxdepth: 1


First off, thanks for taking the time to contribute!

There are many ways you can help:

- Send feedback: |br|
  Know a cool project that uses it,
  created a custom provider or have an interesting use case?
  Let us know in :ref:`the forum <_forum>` .
- Create issues for bugs or feature requests (see `Bug Reports and Feature Requests`_ below).
- Help others, by answering questions in the `forum`_ or on `Stackoverflow`_.
- Improve this documentation.
- Fix bugs or propose features.

This small guideline may help taking the first steps.

Happy hacking :)

.. _`issue tracker`: https://github.com/mar10/wsgidav/issues
.. _forum: https://github.com/mar10/wsgidav/discussions
.. _`the repository`: https://github.com/mar10/wsgidav
.. _`Stackoverflow`: https://stackoverflow.com/questions/tagged/wsgidav
.. _CHANGES: https://github.com/mar10/wsgidav/blob/master/CHANGELOG.md


Bug Reports and Feature Requests
================================

If you have encountered a problem with WsgiDAV or have an idea for a new
feature, please submit it to the `issue tracker`_ on GitHub.

.. note::
  The issue tracker is for bugs and feature requests.
  Please use :ref:`the Q&A forum <forum>` or `Stackoverflow`_ to ask questions.

Use the search function to find existing issues if any.
If you have additional information, add a comment there instead of creating a new issue.

**If it's a bug report:**

- Carefully describe the required steps to reproduce the failure.
- Give additional information about the server:
  (OS version, WsgiDAV version, WSGI server setup)?
  Which settings are enabled (configuration file)?
- What client are you using (OS, client software and -version)?
- What output do you see on the console or log files?
- Maybe attach a patch file or describe a potential fix?


**If it's a feature request:**

  - What are you trying to accomplish?
  - Why is this a cool feature? Give use cases.
  - Can you propose a specification? Are there similar implementations in other projects?
    Add references or screenshots if you have some.
    Remember that the general API must stay generic, extensible, and consistent.
    How will this interfere with existing API and functionality?
    Does it play well with the other extensions?


Contributing Code
=================

.. note::

  Please open (or refer to) an issue, even if you provide a pull request.
  It will be useful to discuss different approaches or upcoming related
  problems.

The recommended way for new contributors to submit code to WsgiDAV is to fork
the repository on GitHub and then submit a pull request after
committing the changes.  The pull request will then need to be approved before it is merged.

#. Check for open issues or open a fresh issue to start a discussion around a
   feature idea or a bug.
#. Fork the repository on GitHub.
#. Clone the repo to your local computer
#. Setup the project for development
#. Create and activate your feature branch
#. Hack, Hack, Hack
#. Test, Test, Test
#. Send a pull request and bug the maintainer until it gets merged and published.

.. note::

  Don't mix different topics in a single commit or issue. Instead submit a new pull request (and
  even create separate branches as appropriate).


Setup for Development
---------------------
Fork the Repository
^^^^^^^^^^^^^^^^^^^

#. Create an account on GitHub.

#. Fork the main WsgiDAV repository (`mar10/wsgidav
   <https://github.com/mar10/wsgidav>`_) using the GitHub interface.

#. Clone your forked repository to your machine. ::

       git clone https://github.com/YOUR_USERNAME/wsgidav
       cd wsgidav

#. Create and activate a new working branch.  Choose any name you like. ::

       git checkout -b feature-xyz


Create and Activate a Virtual Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Virtual environments allow us to develop and test in a sandbox, without affecting our
system otherwise. |br|
We need `Python 3.8+ <https://www.python.org/downloads/>`_ and
`uv <https://docs.astral.sh/uv/>`_ on our system.

If you want to run tests on *all supported* platforms, install Python
3.9, 3.10, 3.11, 3.12, and 3.13.

We use `uv <https://docs.astral.sh/uv/>`_ for dependency management. Install it with::

    $ curl -LsSf https://astral.sh/uv/install.sh | sh

or via Homebrew (macOS)::

    $ brew install uv

Then create and activate the virtual environment::

    $ cd /path/to/wsgidav
    $ uv sync
    $ source .venv/bin/activate

On Windows (PowerShell)::

    > cd /path/wsgidav
    > uv sync
    > .venv\Scripts\Activate.ps1

**Note:** On Ubuntu you additionally may have to install ``apt-get install python3-venv``.


Install Requirements
^^^^^^^^^^^^^^^^^^^^

``uv sync`` installs all runtime and development dependencies defined in
``pyproject.toml`` (including the ``[dependency-groups]``) and creates a
``uv.lock`` lock file::

    $ uv sync

and install wsgidav itself in editable mode (already handled by ``uv sync``)::

    $ uv pip install -e .

..    $ python setup.py develop

If everything is cool, this code should now run::

    $ uv run wsgidav --version

The test suite should run as well::

    $ uv run tox


Hack, Hack, Hack
----------------

.. note::

      Follow the Style Guide, basically `PEP 8 <https://www.python.org/dev/peps/pep-0008/>`_.

      Since version 3.x source formatting rules are delegated to
      `Ruff <https://docs.astral.sh/ruff/>`_ (lint + format).

      Failing tests or not following PEP 8 will break builds on
      `GitHub <https://github.com/mar10/wsgidav/actions/workflows/tests.yml>`_ 
      and therefore be automatically rejected:

        - Run ``$ uv run tox -e format`` to re-format the code, or
          look for plugins for your favorite editor that format on-save.

        - Run ``$ uv run tox -e check`` frequently and before you commit.

        - Don't forget to run ``$ uv run tox -e format`` and ``$ uv run tox`` to run the
          whole test suite before you commit.


Test, Test, Test
----------------

Testing is best done through ``tox``, which provides a number of targets and
allows testing against multiple different Python environments:

* To run all unit tests on all suppprted Python versions inclusive flake8 style
  checks and code coverage::

      $ uv run tox

* To run unit tests for a specific Python version, such as 3.10::

      $ uv run tox -e py310

* To run selective tests, we can call ``pytest`` directly, e.g.::

      $ uv run pytest -ra wsgidav tests/test_util.py

* Arguments to ``pytest`` can be passed via ``tox``, e.g. in order to run a
  particular test::

      $ uv run tox -e py310 -- -x tests/test_util.py::BasicTest::testBasics

* To list all possible targets (available commands)::

      $ uv run tox -av

* To build the Sphinx documentation::

      $ uv run tox -e docs

Gain additional Kudos by first adding a test that fails without your changes and passes
after they are applied. |br|
New unit tests should be included in the ``tests`` directory whenever possible.

Run Litmus Test Suite
---------------------

'`litmus <http://www.webdav.org/neon/litmus/>`' is the reference test suite for
WebDAV - although unmaintained now.

See the docstring in
`test_litmus.py <https://github.com/mar10/wsgidav/blob/master/tests/test_litmus.py>`
for details.

Create a Pull Request
---------------------
`The proposed procedure <http://git-scm.com/book/en/Distributed-Git-Contributing-to-a-Project#Public-Small-Project>`_
is:

#. Make sure you have forked the original repository on GitHub and
   checked out the new fork to your computer as described above.
#. Create and activate your feature branch (``git checkout -b my-new-feature``).
#. Commit your changes (`git commit -am "Added some cool feature"`).
#. Push to the branch (`git push origin my-new-feature`).
#. Create a new Pull Request on GitHub.
#. Please add a bullet point to :file:`../../CHANGELOG.md` if the fix or feature is not
   trivial (small doc updates, typo fixes).
   Then commit::

       git commit -m '#42: Add useful new feature that does this.'

   GitHub recognizes certain phrases that can be used to automatically
   update the issue tracker.

   For example::

       git commit -m 'Closes #42: Fix invalid markup in docstring of Foo.bar.'

   would close issue #42.

#. Wait for a core developer to review your changes.
