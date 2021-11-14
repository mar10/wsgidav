*****
 FAQ
*****

**What do I need to run WsgiDAV?**
    See :doc:`run-install` for details.

**Which web servers are supported?**
    WsgiDAV comes with a standalone server, to run out of the box.
    There is also built-in support for CherryPy, Paste, and wsgiref servers, as
    long as these packages are installed.
    (Fast)CGI should be possible using `flup <http://trac.saddi.com/flup>`_.

    Basically, it runs with all WSGI servers. Currently we tested with Pylons,
    CherryPy, Paste server.

    See :doc:`run-configure` for details.

**Which configuration do you recommend?**
    Currently CherryPy seems to be very robust. Also installing lxml is
    recommended.

    But since WsgiDAV is pretty new, please provide feedback on your experience.

**Which WebDAV clients are supported?**
    Basically all WebDAV clients on all platforms, though some of them show odd
    behaviors.

    See :doc:`run-access` for details.

**I found a bug, what should I do?**
    First, check the `issue list <https://github.com/mar10/wsgidav/issues>`_,
    if this is a known bug.
    If not, open a new issue and provide detailed information how to reproduce
    it.

    Then fix it and send me the patch ;-)

**How do you pronounce WsgiDAV?**
    Don't care really, but I would say 'Whiskey Dove'.
