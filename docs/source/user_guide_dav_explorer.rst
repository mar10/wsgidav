============
DAV Explorer
============

*This section describes how to use the built-in WsgiDAV web interface, DAV Explorer.*

WsgiDAV comes with a slick web interface that allows to explore the DAV share and 
perform basic operations (create, delete, move, copy, rename, ...) directly
in the browser, without the need for additional software or drive mapping. |br|
Up- and downloading of files is supported using drag-and-drop or file dialogs. |br|
Also inline editing of office documents is supported when MS Office or LibreOffice is 
installed on the client machine.

.. image:: DAV_Explorer.png
  :name: WsgiDAV explorer

.. note::

  DAV Explorer is available since version 4.4. |br|
  It has beta status and is not enabled by default, but must be explicitly enabled 
  in the configuration file ``wsgidav.yaml``.

.. toctree::
   :maxdepth: 1

Configuration
-------------

TODO: Add configuration instructions here. |br|
See :doc:`user_guide_configure` for more details on how to configure WsgiDAV.

Using DAV Explorer
------------------

TODO: Add detailed instructions here.

Viewing and Editing Text Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Text and source files (for example ``.txt``, ``.md``, ``.toml``, ``.yaml``,
``.py``, ``.js``, ``.html``, ``.ps1``) are displayed with syntax highlighting
in the details pane. Files larger than ``dav_explorer.max_preview_size_kb``
are not displayed.

Unless the share or DAV Explorer is readonly, click **Edit** above the text (or
choose *Edit* from the context menu) to change the file:

- The file is locked (WebDAV ``LOCK``), so other users and clients cannot
  modify it while it is being edited. The lock is refreshed while the editor
  is open.
- **Save** (or :kbd:`Ctrl+S` / :kbd:`Cmd+S`) stores the file with a ``PUT``
  request that passes the lock token.
- **Close** (or :kbd:`Esc`) releases the lock (``UNLOCK``). DAV Explorer asks
  before unsaved changes are discarded.

The editor (`CodeMirror <https://codemirror.net>`_) is loaded from a CDN
when a text file is displayed for the first time. If it cannot be loaded, the
text is displayed without highlighting and cannot be edited.

Third-Party Libraries
---------------------

DAV Explorer loads its JavaScript libraries and stylesheets from the
`jsDelivr <https://www.jsdelivr.com>`_ CDN, so the browser needs access to
``cdn.jsdelivr.net``.
All files are pinned to exact versions and protected with
`Subresource Integrity <https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity>`_
(SRI) hashes: the browser refuses to use a file that was modified on the CDN.
JavaScript modules are verified by the ``integrity`` section of the import map
in ``app.html``. This is supported by Chrome and Edge 127+, Safari 18+, and
Firefox 138+; older browsers load the modules without checking them.
Fonts that the stylesheets load (Bootstrap icons) are not covered by SRI.

Maintainers update the versions and hashes with
``scripts/update_dav_explorer_cdn.py``. ``tox -e cdn`` verifies the hashes
against the CDN without modifying files (also run by the release workflow).

Known Limitations
-----------------

TODO: Add detailed instructions here.

       Feature          |       macOS        |      Windows       |       Linux
----------------------- | ------------------ | :----------------: | :---------------:
Drag files to desktop   | :white_check_mark: | :white_check_mark: | :white_check_mark:
Drag files from desktop | :white_check_mark: | :white_check_mark: | :white_check_mark:
