# (c) 2009-2016 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implement the FileLikeQueue helper class.

This helper class is intended to handle use cases where an incoming PUT
request should be directly streamed to a remote target.

Usage: return an instance of this class to`beginWrite` and pass it to the
consumer at the same time::

    def beginWrite(self, contentType=None):
        queue = FileLikeQueue(maxsize=1)
        requests.post(..., data=queue)
        return queue    

"""
from wsgidav import compat
from wsgidav import util

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

# ============================================================================
# FileLikeQueue
# ============================================================================

class FileLikeQueue(object):
    """A queue for chunks that behaves like a file-like.
    
    read() and write() are typically called from different threads.

    This helper class is intended to handle use cases where an incoming PUT
    request should be directly streamed to a remote target:

    def beginWrite(self, contentType=None):
        queue = FileLikeQueue(maxsize=1)
        requests.post(..., data=queue)
        return queue    
    """
    def __init__(self, maxsize=0):
        self.is_closed = False
        self.queue = compat.queue.Queue(maxsize)
        self.unread = ""

    def read(self, size=0):
        """Read a chunk of bytes from queue.

        size = 0: Read next chunk (arbitrary length)
             < 0: Read all bytes 
             > 0: Read one chunk of `size` bytes (or less if stream was closed)

        Blocks if queue is empty and close() was not yet called.
        If close() was called and queue is empty, return ''.
        """
        res = self.unread
        self.unread = ""
        # print("FileLikeQueue.read()")
        # Deliver pending data without delay
        while ( (res == "") or (size < 0) or (size > 0 and len(res) < size) ):
            try:
                # Read pending data, blocking if neccessary
                # (but handle the case that close() is called while waiting)
                res += compat.to_native(self.queue.get(True, 0.1))
            except compat.queue.Empty:
                # There was no pending data: wait for more, unless close() was called
                if self.is_closed:
                    break
        #
        if size > 0 and len(res) > size:
            self.unread = res[size:]
            res = res[:size]
        # print("FileLikeQueue.read({}) => {} bytes".format(size, len(res)))
        return res

    def write(self, chunk):
        """Put a chunk of bytes (or an iterable) to the queue.

        May block if maxsize number of chunks is reached.
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
        print("FileLikeQueue.close()")
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
