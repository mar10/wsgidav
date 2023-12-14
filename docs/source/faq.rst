*****
 FAQ
*****

**What do I need to run WsgiDAV?**
    See :doc:`installation` for details.

**Which web servers are supported?**
    WsgiDAV comes with a standalone server, to run out of the box.
    There is also built-in support for cheroot, ext-wsgiutils, gevent, gunicorn,
    paste, uvicorn, and wsgiref.

    See :doc:`user_guide_configure` for details.

**Which configuration do you recommend?**
    Currently Cherroot seems to be very robust. Also installing lxml is
    recommended.

    But since servers are improved over time, please provide feedback on your experience.

**Which WebDAV clients are supported?**
    Basically all WebDAV clients on all platforms, though some of them show odd
    behaviors.

    See :doc:`user_guide_access` for details.

**I found a bug, what should I do?**
    First, check the `issue list <https://github.com/mar10/wsgidav/issues>`_,
    if this is a known bug.
    If not, open a new issue and provide detailed information how to reproduce
    it.

    Then fix it and send me the patch ;-)

**How do you pronounce WsgiDAV?**
    Don't care really, but I would say 'Whiskey Dove'.
