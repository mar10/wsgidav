Mercurial WebDAV provider
=========================

Examples
--------
This screenshot shows how a Mercurial repository appears in Microsoft Windows
File Explorer:

.. image:: _static/img/Explorer_Mercurial.png

Some new live properties are available:

.. image:: _static/img/DAVExplorer_Mercurial.png


Usage
-----
.. note:: This is **not** production code.

To publish a Mercurial repository by the share name 'hg', simply add these lines
to the configuration file::

    # Publish a Mercurial repository
    from wsgidav.samples.hg_dav_provider import HgResourceProvider
    addShare("hg", HgResourceProvider("REPO_PATH_OR_URL"))


Details
-------
DAV provider that publishes a Mercurial repository.

Note: This is **not** production code!

The repository is rendered as three top level collections.

edit:
    Contains the working directory, i.e. all files. This includes uncommitted
    changes and untracked new files.
    This folder is writable.
released:
    Contains the latest committed files, also known as 'tip'.
    This folder is read-only.
archive:
    Contains the last 10 revisions as sub-folders.
    This folder is read-only.

Sample layout::

    /<share>/
        edit/
            server/
                ext_server.py
            README.txt
        released/
        archive/
            19/
            18/
            ...

Supported features:

#. Copying or moving files from ``/edit/..`` to the ``/edit/..`` folder will
   result in a ``hg copy`` or ``hg rename``.
#. Deleting resources from ``/edit/..`` will result in a ``hg remove``.
#. Copying or moving files from ``/edit/..`` to the ``/released`` folder will
   result in a ``hg commit``.
   Note that the destination path is ignored, instead the source path is used.
   So a user can drag a file or folder from somewhere under the ``edit/..``
   directory and drop it directly on the ``released`` directory to commit
   changes.
#. To commit all changes, simply drag'n'drop the ``/edit`` folder on the
   ``/released`` folder.
#. Creating new collections results in creation of a file called ``.directory``,
   which is then ``hg add`` ed since Mercurial doesn't track directories.
#. Some attributes are published as live properties, such as ``{hg:}date``.


Known limitations:

#. This 'commit by drag-and-drop' only works, if the WebDAV clients produces
   MOVE or COPY requests. Alas, some clients will send PUT, MKCOL, ... sequences
   instead.
#. Adding and then removing a file without committing after the 'add' will
   leave this file on disk (untracked)
   This happens for example with lock files that Open Office Write and other
   applications will create.
#. Dragging the 'edit' folder onto 'released' with Windows File Explorer will
   remove the folder in the explorer view, although WsgiDAV did not delete it.
   This seems to be done by the client.


See:
    http://mercurial.selenic.com/wiki/MercurialApi
Requirements:
    ``easy_install mercurial`` or install the API as non-standalone version
    from here: http://mercurial.berkwood.com/
    http://mercurial.berkwood.com/binaries/mercurial-1.4.win32-py2.6.exe
