-----------------
Using the Library
-----------------

This section describes how to use the ``wsgidav`` package to implement custom
WebDAV servers.

and the ``wsgidav`` package can be used in Python code::

  $ python
  >>> from wsgidav import __version__
  >>> __version__
  '2.3.1'


Passing Options
---------------

Options are passed as Python dict. See the :doc:`user_guide_configure`.

.. todo:: TODO.


Verbosity Level
---------------

The verbosity level can have a value from 0 to 6::

    0: quiet
    1: show errors only
    2: show conflicts and 1 line summary only
    3: show write operations
    4: show equal files
    5: diff-info and benchmark summary
    6: show FTP commands


Script Examples
---------------

All options that are available for command line, can also be passed to
the synchronizers. For example ``--delete-unmatched`` becomes ``"delete_unmatched": True``.

Upload modified files from local folder to FTP server::

  from ftpsync.targets import FsTarget
  from ftpsync.ftp_target import FtpTarget
  from ftpsync.synchronizers import UploadSynchronizer

  local = FsTarget("~/temp")
  user ="joe"
  passwd = "secret"
  remote = FtpTarget("/temp", "example.com", username=user, password=passwd)
  opts = {"force": False, "delete_unmatched": True, "verbose": 3}
  s = UploadSynchronizer(local, remote, opts)
  s.run()

Synchronize a local folder with an FTP server using TLS::

  from ftpsync.targets import FsTarget
  from ftpsync.ftp_target import FtpTarget
  from ftpsync.synchronizers import BiDirSynchronizer

  local = FsTarget("~/temp")
  user ="joe"
  passwd = "secret"
  remote = FtpTarget("/temp", "example.com", username=user, password=passwd, tls=True)
  opts = {"resolve": "skip", "verbose": 1}
  s = BiDirSynchronizer(local, remote, opts)
  s.run()


Logging
-------

By default, the library initializes and uses a
`python logger <https://docs.python.org/library/logging.html>`_ named 'pyftpsync'.
This logger can be customized like so::

    import logging

    logger = logging.getLogger("pyftpsync")
    logger.setLevel(logging.DEBUG)

and replaced like so::

    import logging
    import logging.handlers
    from ftpsync.util import set_pyftpsync_logger

    custom_logger = logging.getLogger("my.logger")
    log_path = "/my/path/pyftpsync.log"
    handler = logging.handlers.WatchedFileHandler(log_path)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    custom_logger.addHandler(handler)

    set_pyftpsync_logger(custom_logger)


.. note::

    The CLI calls ``set_pyftpsync_logger(None)`` on startup, so it logs to stdout
    (and stderr).

..
  .. toctree::
     :hidden:

     addons
