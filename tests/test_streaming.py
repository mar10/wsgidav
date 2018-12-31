# -*- coding: utf-8 -*-
# (c) 2009-2019 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php

"""
Unit tests for wsgidav.stream_tools.FileLikeQueue
"""

from tempfile import gettempdir
from tests.util import Timing, write_test_file, WsgiDavTestServer
from wsgidav import compat
from wsgidav.dav_provider import DAVNonCollection, DAVProvider
from wsgidav.stream_tools import FileLikeQueue

import os
import requests
import threading
import unittest


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
        self.worker = None

    def begin_write(self, content_type=None):
        # print("begin_write: {}".format(self.target_path))
        queue = FileLikeQueue(max_size=1)

        # Simulate an asynchrounous consumer. We use a file, so we can check
        # the result from the parent unittest process. In real live this could be
        # requests.post(..., data=queue), ...
        def _consumer():
            # print("_consumer: {}".format(self.target_path))
            with open(self.target_path, "wb") as f:
                s = 0
                # print("_consumer: read()...")
                data = queue.read()
                while data:
                    s += len(data)
                    # print("_consumer: read(): write")
                    f.write(compat.to_bytes(data))
                    data = queue.read()
            # print("_consumer(): done", s)

        self.worker = threading.Thread(target=_consumer)
        self.worker.setDaemon(True)
        self.worker.start()
        return queue

    def end_write(self, with_errors):
        print("end_write: {}".format(self.target_path))
        self.worker.join()


class MockProxyProvider(DAVProvider):
    """
    A simple DAVProvider that returns a dummy MockProxyResource for all requests.
    """

    def __init__(self, target_path):
        super(MockProxyProvider, self).__init__()
        self.target_path = target_path

    def get_resource_inst(self, path, environ):
        print("get_resource_inst", path)
        res = MockProxyResource(path, environ, self.target_path)
        if path == "/":  # if server asks for the parent collection, fake one
            res.is_collection = True
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
        if os.path.isfile(self.target_path):
            os.remove(self.target_path)
        self.provider = None

    def testFileLikeQueueUnsized(self):
        # queue of unlimited size
        q = FileLikeQueue()
        q.write("*" * 42)
        q.write("*" * 3)
        # unsized reads will return chunks as queued
        res = q.read()
        self.assertEqual(len(res), 42)
        res = q.read()
        self.assertEqual(len(res), 3)
        q.close()  # subsequent reads will return "" instead of blocking
        res = q.read()
        self.assertEqual(res, "", "Read after close() returns ''")
        # subsequent write will raise
        self.assertRaises(ValueError, q.write, "***")

    def testFileLikeQueue(self):
        # queue of unlimited size
        q = FileLikeQueue()
        # queue 32 bytes
        q.write("*" * 7)
        q.write("*" * 11)
        q.write("*" * 5)
        q.write("*" * 9)
        q.close()
        # sized reads will return chunks as demanded
        for _ in range(6):
            self.assertEqual(len(q.read(5)), 5)
        self.assertEqual(len(q.read(5)), 2, "last chunk delivers the reminder")
        self.assertEqual(len(q.read(5)), 0, "furtehr read() returns ''")
        # self.assertEqual(q.size, 0)

    def testFileLikeQueueAll(self):
        # queue of unlimited size
        q = FileLikeQueue()
        # queue 32 bytes
        q.write("*" * 7)
        q.write("*" * 11)
        q.write("*" * 5)
        q.write("*" * 9)
        q.close()
        # read(-1) returns all, then ''
        self.assertEqual(len(q.read(-1)), 32)
        self.assertEqual(len(q.read(-1)), 0)

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
