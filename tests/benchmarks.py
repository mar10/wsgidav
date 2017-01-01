# -*- coding: iso-8859-1 -*-
# (c) 2009-2017 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
    Benchmark suite for WsgiDAV. 
    
Questions
=========
- is lxml really faster?
- is WsgiDAV 1.x faster than WsgiDAV 2.x?
- is WsgiDAV 2.x faster or slower on Py2.7 and Py3.x?
- compare this to mod_dav's performance 

Test cases
==========
- 100 x PROPFIND depth 0 
- 1 x PROPFIND depth infinity 
- COPY: big file, many small files, big tree
- MOVE: big file, many small files, big tree
- DELETE: big file, many small files, big tree
- LOCK
- UNLOCK
- Check if locked
- PROPPATCH
- PROPFIND: depth 0, many small files
            depth infinity
- run litmus in a timed script
- Simulate typical Windows Client request sequences:
  - dir browsing
  - file reading
  - file editing

- http://groups.google.com/group/paste-users/t/b2afc88a86caade1?hl=en
  use httperf 
  http://www.hpl.hp.com/research/linux/httperf/httperf-man-0.9.txt
  and openwebload
  http://openwebload.sourceforge.net/index.html

- makeTree(roofolderName="/bench", folderCount=10, subfolderCount=10, fileCount=10, fileSize=1024)
  Big tree with 100 folders and 1000 files
  bench/
    folder1/
    ..
    folder10/
      subfolder10-1/
      ..
      subfolder10-10/
        file10-10-1.txt -> 1k
"""
from __future__ import print_function

import datetime
import logging
import os
import platform
import subprocess
import sys

from tests.util import Timing, WsgiDavTestServer
from wsgidav import __version__
from wsgidav.xml_tools import useLxml

try:
    # WsgiDAV 2.x
    from wsgidav import compat
except ImportError:
    # WsgiDAV 1.x: mock the compat module, so benchmark.py runs in both
    # versions:
    class compat(object):
        xrange = xrange

        @staticmethod
        def to_bytes(s, encoding="utf8"):
            """Convert unicode (text strings) to binary data, i.e. str on Py2 and bytes on Py3."""
            if type(s) is unicode:
                s = s.encode(encoding)
            elif type(s) is not str:
                s = str(s)
            return s


try:
    try:
        from cherrypy import __version__ as cp_version
    except ImportError:
        # Bundled CherryPy wsgiserver in WsgDAV 1.x
        server_folder = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "wsgidav", "server"))
        sys.path.append(server_folder)
        from cherrypy import wsgiserver
        cp_version = wsgiserver.CherryPyWSGIServer.version
except ImportError:
    cp_version = "unknown"
    raise


def _setup_fixture(opts, client):
    # Cleanup target folder
    client.delete("/test/")
    client.mkcol("/test/")
    client.checkResponse(201)


def _bench_litmus(opts):

    try:
        with Timing("litmus test suite"):
            # Run litmus test suite without printing output
            res = subprocess.check_output(
                ["litmus", "http://127.0.0.1:8080/", "tester", "secret"])
            # res = subprocess.check_call(["litmus", "http://127.0.0.1:8080/", "tester", "secret"],
            # stdout=DEVNULL, stderr=subprocess.STDOUT)
    except OSError:
        print("This test requires the litmus test suite (see http://www.webdav.org/neon/litmus/)")
        raise
    return res


def _bench_script(opts):
    # print("Scriptes benchmarks")
    # print("_bench_script(), {}...".format(opts))

    from tests import davclient
    server_url = opts.get("external_server") or "http://localhost:8080/"
    client = davclient.DAVClient(server_url)
    client.set_basic_auth("tester", "secret")

    # Prepare file content
    data_1k = b"." * 1000

    # Prepare big file with 10 MB
    lines = []
    line = "." * (1000 - 6 - len("\n"))
    for i in compat.xrange(10 * 1000):
        lines.append("%04i: %s\n" % (i, line))
    data_10m = "".join(lines)
    data_10m = compat.to_bytes(data_10m)

    with Timing("Setup fixture"):
        _setup_fixture(opts, client)

    # PUT files
    with Timing("1000 x PUT 1 kB", 1000, "{:>6.1f} req/sec", 1, "{:>7,.3f} MB/sec"):
        for _ in compat.xrange(1000):
            client.put("/test/file1.txt", data_1k)
        client.checkResponse()

    with Timing("10 x PUT 10 MB", 10, "{:>6.1f} req/sec", 100, "{:>7,.3f} MB/sec"):
        for _ in compat.xrange(10):
            client.put("/test/bigfile.txt", data_10m)
        client.checkResponse()

    with Timing("1000 x GET 1 kB", 1000, "{:>6.1f} req/sec", 1, "{:>7,.3f} MB/sec"):
        for _ in compat.xrange(1000):
            body = client.get("/test/file1.txt")
        client.checkResponse()

    with Timing("10 x GET 10 MB", 10, "{:>6.1f} req/sec", 100, "{:>7,.3f} MB/sec"):
        for _ in compat.xrange(10):
            body = client.get("/test/bigfile.txt")
        client.checkResponse()

    with Timing("10 x COPY 10 MB", 10, "{:>6.1f} req/sec", 100, "{:>7,.3f} MB/sec"):
        for _ in compat.xrange(10):
            client.copy("/test/bigfile.txt",
                        "/test/bigfile-copy.txt",
                        depth='infinity', overwrite=True)
        client.checkResponse()

    with Timing("100 x MOVE 10 MB", 100, "{:>6.1f} req/sec"):
        name_from = "/test/bigfile-copy.txt"
        for i in compat.xrange(100):
            name_to = "/test/bigfile-copy-{}.txt".format(i)
            client.move(name_from, name_to,
                        depth='infinity', overwrite=True)
            name_from = name_to
        client.checkResponse()

    with Timing("100 x LOCK/UNLOCK", 200, "{:>6.1f} req/sec"):
        for _ in compat.xrange(100):
            locks = client.set_lock("/test/lock-0",
                                    owner="test-bench",
                                    locktype="write",
                                    lockscope="exclusive",
                                    depth="infinity")
            token = locks[0]
            client.unlock("/test/lock-0", token)
        client.checkResponse()

    with Timing("1000 x PROPPATCH", 1000, "{:>6.1f} req/sec"):
        for _ in compat.xrange(1000):
            client.proppatch("/test/file1.txt",
                             set_props=[("{testns:}testname", "testval"),
                                        ],
                             remove_props=None)
        client.checkResponse()

    with Timing("500 x PROPFIND", 500, "{:>6.1f} req/sec"):
        for i in compat.xrange(500):
            client.propfind("/",
                            properties="allprop",
                            namespace='DAV:',
                            depth=None,
                            headers=None)
        client.checkResponse()


#-------------------------------------------------------------------------
#
#-------------------------------------------------------------------------

def run_benchmarks(opts):

    py_version = "{}.{}.{}".format(*sys.version_info)

    print("#-- WsgiDAV Benchmark ---------------------------------------------")
    print("Date:     {}".format(datetime.date.today()))
    print("WsgiDAV:  {}".format(__version__))
    print("Python:   {}".format(py_version))
    print("CherryPy: {}".format(cp_version))
    print("OS:       {}".format(platform.platform(aliased=True)))

    if useLxml:
        from lxml.etree import LXML_VERSION as lxml_version
        print("lxml:     {}".format(lxml_version))
    else:
        print("lxml:     (not installed)")

    def _runner(opts):
        with Timing(">>> Summary >>>:"):
            _bench_litmus(opts)
            _bench_script(opts)
        return

    if opts.get("external_server"):
        _runner(opts)
    else:
        with WsgiDavTestServer(with_auth=False, with_ssl=False, profile=opts.get("profile_server")):
            if opts.get("profile_client"):
                import cProfile
                import pstats
                prof = cProfile.Profile()
                prof = prof.runctx("_runner(opts)", globals(), locals())
                stream = compat.StringIO()
                stats = pstats.Stats(prof, stream=stream)
        #        stats.sort_stats("time")  # Or cumulative
                stats.sort_stats("cumulative")  # Or time
                stats.print_stats(20)  # 80 = how many to print
                # The rest is optional.
                # stats.print_callees()
                # stats.print_callers()
                logging.info("Profile data:")
                logging.info(stream.getvalue())
            else:
                _runner(opts)

    return


def main():
    opts = {"profile_client": False,  #
            "profile_server": False,
            "external_server": None,  # "http://localhost:8080",
            }
    run_benchmarks(opts)


if __name__ == "__main__":
    main()
