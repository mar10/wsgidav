Virtual WebDAV provider
=======================

Examples
--------
Given these 3 'resources':

==========  ===========  =========  ==========  =============
Title       Orga         Status     Tags        Attachments
==========  ===========  =========  ==========  =============
My doc 1    development  draft      cool, hot   MySpec.doc
                                                MySpec.pdf
----------  -----------  ---------  ----------  -------------
My doc 2    development  published  cool, nice  MyURS.doc
----------  -----------  ---------  ----------  -------------
My doc (.)  marketing    published  nice        MyURS.doc
==========  ===========  =========  ==========  =============

this dynamic structure is published:

.. image:: _static/img/Explorer_virtual.png

A resource is served as an collection, which is generated on-the-fly and
contains some virtual files with additional information:

.. image:: _static/img/Browser_virtual.png


Usage
-----
To publish the sample virtual resources, simply add these lines  to the
configuration file::

    # Publish a virtual structure
    from wsgidav.samples.virtual_dav_provider import VirtualResourceProvider
    addShare("virtres", VirtualResourceProvider())


Module description
------------------
.. automodule::  wsgidav.samples.virtual_dav_provider
