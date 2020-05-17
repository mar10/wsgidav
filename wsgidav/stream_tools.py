# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implement the FileLikeQueue helper class.

This helper class is intended to handle use cases where an incoming PUT
request should be directly streamed to a remote target.

Usage: return an instance of this class to`begin_write` and pass it to the
consumer at the same time::

    def begin_write(self, contentType=None):
        queue = FileLikeQueue(max_size=1)
        requests.post(..., data=queue)
        return queue

"""
from __future__ import print_function
from wsgidav import compat, util


__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)


# ============================================================================
# FileLikeQueue
# ============================================================================


class FileLikeQueue(object):
    """A queue for chunks that behaves like a file-like.

    read() and write() are typically called from different threads.

    This helper class is intended to handle use cases where an incoming PUT
    request should be directly streamed to a remote target:

    def begin_write(self, contentType=None):
        # Create a proxy buffer
        queue = FileLikeQueue(max_size=1)
        # ... and use it as source for the consumer:
        requests.post(..., data=queue)
        # pass it to the PUT handler as target
        return queue
    """

    def __init__(self, max_size=0):
        self.is_closed = False
        self.queue = compat.queue.Queue(max_size)
        self.unread = ""

    def read(self, size=0):
        """Read a chunk of bytes from queue.

        size = 0: Read next chunk (arbitrary length)
             > 0: Read one chunk of `size` bytes (or less if stream was closed)
             < 0: Read all bytes as single chunk (i.e. blocks until stream is closed)

        This method blocks until the requested size become available.
        However, if close() was called, '' is returned immediately.
        """
        res = self.unread
        self.unread = ""
        # Get next chunk, cumulating requested size as needed
        while res == "" or size < 0 or (size > 0 and len(res) < size):
            try:
                # Read pending data, blocking if neccessary
                # (but handle the case that close() is called while waiting)
                res += compat.to_native(self.queue.get(True, 0.1))
            except compat.queue.Empty:
                # There was no pending data: wait for more, unless close() was called
                if self.is_closed:
                    break
        # Deliver `size` bytes from buffer
        if size > 0 and len(res) > size:
            self.unread = res[size:]
            res = res[:size]
        # print("FileLikeQueue.read({}) => {} bytes".format(size, len(res)))
        return res

    def write(self, chunk):
        """Put a chunk of bytes (or an iterable) to the queue.

        May block if max_size number of chunks is reached.
        """
        if self.is_closed:
            raise ValueError("Cannot write to closed object")
        # print("FileLikeQueue.write(), n={}".format(len(chunk)))
        # Add chunk to queue (blocks if queue is full)
        if compat.is_basestring(chunk):
            self.queue.put(chunk)
        else:  # if not a string, assume an iterable
            for o in chunk:
                self.queue.put(o)

    def close(self):
        # print("FileLikeQueue.close()")
        self.is_closed = True

    # TODO: we may also implement iterator functionality, but this should be
    # optional, since the consumer may behave differently.
    # For example the `requests` library produces chunked transfer encoding if
    # the `data` argument is a generator instead of a file-like.

    # def __iter__(self):
    #     return self

    # def __next__(self):
    #     result = self.read(self.block_size)
    #     if not result:
    #         raise StopIteration
    #     return result

    # next = __next__  # Python 2.x


# ============================================================================
# StreamingFile
# ============================================================================


class StreamingFile(object):
    """A file object wrapped around an iterator / data stream."""

    def __init__(self, data_stream):
        """Intialise the object with the data stream."""
        self.data_stream = data_stream
        self.buffer = ""

    def read(self, size=None):
        """Read bytes from an iterator."""
        while size is None or len(self.buffer) < size:
            try:
                self.buffer += next(self.data_stream)
            except StopIteration:
                break

        sized_chunk = self.buffer[:size]
        if size is None:
            self.buffer = ""
        else:
            self.buffer = self.buffer[size:]
        return sized_chunk
