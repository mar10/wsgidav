==========
Quickstart
==========

*Install WsgiDAV, share a folder from the command line, and connect to it
as a network drive -- in a few minutes.*

.. contents:: On this page
   :local:
   :depth: 1


Install
=======

WsgiDAV needs `Python 3.10+ <https://www.python.org/downloads/>`_ and a WSGI
server. The command line tool uses `Cheroot <https://cheroot.cherrypy.dev/>`_
by default, which is **not** installed automatically, so add it explicitly as
shown below. ``lxml`` is optional and speeds up XML processing.

Pick *one* of the following options.

uv (recommended, all platforms)
-------------------------------

`uv <https://docs.astral.sh/uv/>`_ installs WsgiDAV into its own isolated
environment and puts the ``wsgidav`` command on your ``PATH``::

    $ uv tool install wsgidav --with cheroot --with lxml
    $ wsgidav --version

Or run it once, without installing anything permanently::

    $ uvx --from wsgidav --with cheroot wsgidav --root . --auth anonymous

pipx
----

::

    $ pipx install wsgidav
    $ pipx inject wsgidav cheroot lxml

pip
---

Inside a virtual environment::

    $ python -m venv .venv
    $ source .venv/bin/activate        # Windows: .venv\Scripts\activate
    $ pip install wsgidav cheroot lxml

Windows Package Manager (winget)
--------------------------------

Install the command line tool with the Windows Package Manager::

    > winget install wsgidav

Alternatively, download the
`MSI installer <https://github.com/mar10/wsgidav/releases/latest>`_
(see the *Assets* section). It bundles Python, Cheroot, and lxml, so nothing
else is required.

Docker / Podman
---------------

The `mar10/wsgidav <https://hub.docker.com/r/mar10/wsgidav/>`_ image shares
the container folder ``/public/wsgidav-share`` on port 8080 with anonymous
read-write access. Mount the host folder you want to share there::

    $ docker run --rm -it -p 127.0.0.1:8080:8080 \
        -v /path/to/share:/public/wsgidav-share mar10/wsgidav

Podman works the same way; use the fully qualified image name and, on
SELinux systems (Fedora, RHEL), add ``:Z`` to the volume::

    $ podman run --rm -it -p 127.0.0.1:8080:8080 \
        -v /path/to/share:/public/wsgidav-share:Z docker.io/mar10/wsgidav

To use a configuration file (for authentication, several shares, ...), mount
it as ``/config/wsgidav.yaml``. The paths in the configuration file refer to
the container, so the shared folders must be mounted as well::

    $ docker run --rm -it -p 8080:8080 \
        -v ./wsgidav.yaml:/config/wsgidav.yaml \
        -v /path/to/share:/public/wsgidav-share mar10/wsgidav

A ``docker-compose.yml`` is included in the
`repository <https://github.com/mar10/wsgidav>`_ (``docker compose up``).

.. note::
   ``-p 127.0.0.1:8080:8080`` makes the share reachable from this computer
   only. Use ``-p 8080:8080`` to expose it to the network, but read
   `Security notes`_ first.


Share a Folder (No Configuration File)
======================================

Share a folder with anonymous read-write access, reachable from this computer
only::

    $ wsgidav --root /path/to/share --auth anonymous --no-config

WsgiDAV listens on ``http://localhost:8080/`` by default.
Open this URL in a web browser, or add ``--browse`` to open it automatically.

To make the share reachable from other machines in your network, bind to all
interfaces and optionally choose another port::

    $ wsgidav --host 0.0.0.0 --port 8080 --root /path/to/share --auth anonymous --no-config

On Windows::

    > wsgidav --host 0.0.0.0 --port 8080 --root C:\data\share --auth anonymous --no-config

Useful options:

``--no-config``
    Ignore a ``wsgidav.yaml`` in the current directory, so only the command
    line options apply.
``--auth pam-login`` (Linux, macOS)
    Require a login with a local system account. Needs the ``pam`` extra,
    e.g. ``uv tool install "wsgidav[pam]" --with cheroot``.
``--auth nt`` (Windows)
    Require a login with a Windows (domain) account.
``--web-ui dav-explorer``
    Use the :doc:`DAV Explorer <user_guide_dav_explorer>` web interface
    (``dir-browser`` is the classic listing, ``none`` disables the web UI).
``-v`` / ``-q``
    More or less log output.

Run ``wsgidav --help`` for all options, and see :doc:`user_guide_cli`.

Security notes
--------------

- ``--auth anonymous`` grants **read and write** access to everyone who can
  reach the port. Combine it with ``--host 0.0.0.0`` only in a trusted network.
- To require user names and passwords without system accounts, use a
  configuration file. A minimal ``wsgidav.yaml``::

      host: 0.0.0.0
      port: 8080
      provider_mapping:
          '/': '/path/to/share'
      simple_dc:
          user_mapping:
              '*':
                  'tester':
                      password: 'secret'

  Start it with ``wsgidav --config wsgidav.yaml``.
  See :doc:`user_guide_configure` for all options, including SSL.
- Passwords are sent in clear text unless SSL (HTTPS) is configured.


Map a Network Drive
===================

The examples assume that WsgiDAV is running on a machine with the IP address
``192.168.0.2`` and port ``8080``. Replace them with your values, or use
``localhost`` when the server runs on the same machine.
Use ``https://`` (``davs://`` on Linux) instead of ``http://`` when SSL is
enabled.

Windows
-------

**File Explorer:** open *This PC*, choose *Map network drive* (in the
``...`` menu on Windows 11), pick a drive letter, and enter the folder
``http://192.168.0.2:8080/``.

**Command line:**

.. code-block:: bat

    > net use W: http://192.168.0.2:8080/
    > net use W: http://192.168.0.2:8080/ /user:tester *
    > net use W: /delete

The first form connects anonymously, the second prompts for the password of
user ``tester``. Add ``/persistent:yes`` to reconnect after a reboot.

Shares can also be addressed by UNC path, e.g.
``\\192.168.0.2@8080\DavWWWRoot`` (``\\server@SSL@443\DavWWWRoot`` for HTTPS).

.. note::
   Known limitations of the Windows WebDAV client ("WebClient" service):

   - The *WebClient* service must be running. If ``net use`` fails with
     *System error 67*, start it with ``net start webclient`` (as
     Administrator). On Windows Server, install the *WebDAV Redirector*
     feature first.
   - By default, Windows sends passwords (Basic authentication) only over
     HTTPS. Either configure SSL, or set the registry value
     ``BasicAuthLevel`` to ``2`` under
     ``HKLM\SYSTEM\CurrentControlSet\Services\WebClient\Parameters`` and
     restart the service (not recommended outside trusted networks).
   - Files larger than about 50 MB are rejected by default. Raise the
     ``FileSizeLimitInBytes`` registry value in the same key if needed.
   - Microsoft has deprecated the WebClient service. It still ships with
     Windows 10 and 11, but may be removed in a future version.

   See :doc:`user_guide_access` for more details.

macOS
-----

**Finder:** choose *Go* > *Connect to Server...* (:kbd:`⌘K`), enter
``http://192.168.0.2:8080/``, and click *Connect*. The share appears under
*Locations* in the Finder sidebar.

**Command line:**

.. code-block:: sh

    $ mkdir -p ~/wsgidav
    $ mount_webdav -i http://192.168.0.2:8080/ ~/wsgidav
    $ umount ~/wsgidav

``-i`` prompts for user name and password; omit it for anonymous shares.

Linux
-----

**GNOME Files (Nautilus):** choose *Other Locations*, enter
``dav://192.168.0.2:8080/`` in *Connect to Server*, and click *Connect*.
From a terminal: ``gio mount dav://192.168.0.2:8080/``.

**KDE Dolphin:** enter ``webdav://192.168.0.2:8080/`` in the location bar.

**davfs2** mounts the share into the file system, so every application can
use it::

    $ sudo apt install davfs2            # Debian/Ubuntu; Fedora: sudo dnf install davfs2
    $ sudo mkdir -p /mnt/wsgidav
    $ sudo mount -t davfs http://192.168.0.2:8080/ /mnt/wsgidav
    $ sudo umount /mnt/wsgidav

To mount as a regular user, add a line to ``/etc/fstab`` and store the
credentials in ``~/.davfs2/secrets`` (see ``man mount.davfs``)::

    http://192.168.0.2:8080/  /mnt/wsgidav  davfs  user,noauto,rw  0  0

Any platform: rclone
--------------------

`rclone <https://rclone.org/>`_ can mount a WebDAV share as a local folder
or drive on Windows, macOS, and Linux (requires WinFsp on Windows and
macFUSE or FUSE-T on macOS)::

    $ rclone mount :webdav: ~/wsgidav --webdav-url http://192.168.0.2:8080/

Web browser
-----------

No client needed: open ``http://192.168.0.2:8080/`` in a web browser to
browse, upload, and download files.


Next Steps
==========

- :doc:`user_guide_configure` -- configuration file, authentication, SSL,
  multiple shares.
- :doc:`user_guide_access` -- more WebDAV clients and known issues.
- :doc:`user_guide_lib` -- use WsgiDAV as a library in your own WSGI
  application.
