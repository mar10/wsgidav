# -*- coding: iso-8859-1 -*-
# (c) 2009-2016 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""Unit test for property_manager.py"""
import io
import os
import sys
from tempfile import gettempdir
import threading
import unittest

import requests

from .util import Timing, write_test_file, WsgiDavTestServer
from wsgidav import compat
from wsgidav.dav_provider import DAVProvider, DAVNonCollection


class FileLikeQueue(object):
    """A queue for chunks that behaves like a file-like.
    
    read() and write() are typically called from different threads.
    """
    def __init__(self, maxsize=0):
        self.is_closed = False
        self.queue = compat.queue.Queue(maxsize)

    def read(self, size=None):
        """Read a chunk of bytes from queue.

        Blocks if queue is empty and close() was not yet called.
        If close() was called and queue is empty, return ''.
        """
        if size:
            # TODO: if a size arg was passed, we need to
            #   - check whether the next pending chunk is too large.
            #     If so, we return only a part and store the rest until the next 
            #     call
            #   - check whether the next pending chunk is too small.
            #     If so, can we simply return a smaller chunk, or do we need to
            #     collect more? I.e. would callers assume EOF if the returned 
            #     size is less than the requested size?
            # See http://stackoverflow.com/q/7383464/19166
            raise NotImplementedError
        print("FileLikeQueue.read()")
        # Deliver pending data without delay
        try:
            return self.queue.get_nowait()
        except compat.queue.Empty:
            if self.is_closed:  # No need to wait for more write() calls
                return ""
        # There was no pending data, so wait for more.
        # But handle the case that close() is called while blocking
        while True:
            try:
                print("FileLikeQueue.read(), get")
                return self.queue.get(True, 0.1)
            except compat.queue.Empty:  # timeout
                if self.is_closed:
                    return ""

    def write(self, chunk):
        """Put a chunk of bytes (or an iterable) to the queue.

        May block if maxsize number of chunks is reached.
        """
        if self.is_closed:
            raise ValueError("Cannot write to closed object")
        print("FileLikeQueue.write(), n={}".format(len(chunk)))
        # Add chunk to queue (blocks if queue is full)
        if compat.is_basestring(chunk):
            self.queue.put(chunk)
        else:  # if not a string, assume an iterable
            for o in chunk:
                self.queue.put(o)

    def close(self):
        print("FileLikeQueue.close()")
        self.is_closed = True


# ----------------------------------------------------------------------------
# Dummy DAVProvider implementation
#
# Note that this code runs in a separated process, spawned by the unit tests.

class MockProxyResource(DAVNonCollection):
    """
    A simple _DAVResource that handles PUT requests by passing a FileLikeQueue
    to the server and asynchronuosly pipes the incoming data stream to a target
    file.
    """
    def __init__(self, path, environ, target_path):
        super(MockProxyResource, self).__init__(path, environ)
        self.target_path = target_path

    def beginWrite(self, contentType=None):
        print("beginWrite: {}".format(self.target_path))
        queue = FileLikeQueue(maxsize=1)

        # Simulate an asynchrounous consumer. We use a file, so we can check 
        # the result from the parent unittest process. In real live this could be
        # requests.post(..., data=queue), ...
        def _consumer():
            print("_consumer: {}".format(self.target_path))
            with open(self.target_path, "wb") as f:
                print("_consumer: read()...")
                data = queue.read()
                while data:
                    print("_consumer: read(): write")
                    f.write(data)
                    data = queue.read()
            print("_consumer(): done")

        worker = threading.Thread(target=_consumer)
        worker.setDaemon(True)
        worker.start()        
        return queue

    def endWrite(self, withErrors):
        print("endWrite: {}".format(self.target_path))


class MockProxyProvider(DAVProvider):
    """
    A simple DAVProvider that returns a dummy MockProxyResource for all requests.
    """
    def __init__(self, target_path):
        super(MockProxyProvider, self).__init__()
        self.target_path = target_path

    def getResourceInst(self, path, environ):
        print("getResourceInst", path)
        res = MockProxyResource(path, environ, self.target_path)
        if path == "/":  # if server asks for the parent collection, fake one
            res.isCollection = True
        return res


# ========================================================================
# BasicTest
# ========================================================================

class BasicTest(unittest.TestCase):
    def setUp(self):
        self.SIZE = 10 * 1000 * 1000
        self.test_file = write_test_file("source.txt", self.SIZE)
        self.target_path = os.path.join(gettempdir(), "target.txt")
        self.provider = MockProxyProvider(self.target_path)

    def tearDown(self):
        os.remove(self.test_file)
        os.remove(self.target_path)
        self.provider = None

    def testStream(self):
        with WsgiDavTestServer(provider=self.provider):
            with Timing("testStream", self.SIZE):
                with open(self.test_file, "rb") as f:
                    r = requests.put("http://127.0.0.1:8080/bar.txt", data=f)
            self.assertEqual(r.status_code, 204)
            self.assertEqual(os.path.getsize(self.target_path), self.SIZE)

    # def testStreamBlob(self):
    #     with WsgiDavTestServer(provider=self.provider):
    #         with Timing("testStream", self.SIZE):
    #             blob = b"*" * self.SIZE
    #             r = requests.put("http://127.0.0.1:8080/bar.txt", data=blob)
    #         self.assertEqual(r.status_code, 204)
    #         self.assertEqual(os.path.getsize(self.target_path), self.SIZE)

    # def testStreamChunked(self):
    #     with WsgiDavTestServer(provider=self.provider):
    #         with Timing("testStream", self.SIZE):
    #             def _print_url(r, *args, **kwargs):
    #                 print(r.url)
    #             def _generate():
    #                 with open(self.test_file, "rb") as f:
    #                     while True:
    #                         out = f.read(1000*1000)
    #                         if not out:
    #                             break
    #                         yield out
    #             r = requests.put("http://127.0.0.1:8080/bar.txt",
    #                     data=_generate(),
    #                     # headers={"Content-Length": str(self.SIZE)},
    #                     hooks=dict(response=_print_url))
    #         self.assertEqual(r.status_code, 204)
    #         self.assertEqual(os.path.getsize(self.target_path), self.SIZE)


# ========================================================================


if __name__ == "__main__":
    unittest.main()
