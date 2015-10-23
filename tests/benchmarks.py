# -*- coding: iso-8859-1 -*-
# (c) 2009-2015 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
    Benchmark suite for WsgiDAV. 
    
    This test suite uses davclient to generate WebDAV requests.
     
A first collection of ideas 
===========================
- The result is printable HTML, copy/pastable  
- It also contains date, environment info (Hardware, package versions, ...)
- The suite can be run stand-alone against a running WsgiDAV server, just like
  litmus.
- It uses `davclient` and generates an HTML file.
- There should be detailed results as well as a few summarizing numbers:
  ('Total time', 'Byte reads per second', 'Byte write per second', or something 
  like this), so one can compare benchmarks at a glance. 
- Optional parameters allow to run only a single test
- Parameter allows to pass configuration infos that are dumped with the result:
  benchEnviron = {
      "comment": "Test with caching enabled", 
      "server_os": "Ubuntu 9.01", 
      "server_cpu": "Intel 3GHz",
      "server_ram": "2GB",
      "wsgidav_version": "0.4.b1"  
      "network_bandwidth": "100MBit",
      
      >> these can be automatically set?:      
      "client_os": "Windows XP",  
      "client_cpu": "AMD 5000",
      "date": now() 
      }
- Allow to print profiling info (from WsgiDAV server and from becnhmark client!)
- The result file could also contain the results of test suites ('PASSED'),
  so we could use it as documentation for tests on different platforms/setups.      


Questions
=========
- is lxml really faster?
- compare this to mod_dav's performance 


Test cases
==========
- PUT 1 x 10 MB
- PUT 100 x 1 kB
- GET 1 x 10 MB
- GET 100 x 1 kB
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

from wsgidav import compat

import logging
_benchmarks = [#"proppatch_many",
               #"proppatch_big",
               #"proppatch_deep",
               "test_scripted",
               ]


def _real_run_bench(bench, opts):
    if bench == "*":
        for bench in _benchmarks:
            run_bench(bench, opts)
        return
    
    assert bench in _benchmarks
    if bench == "test_scripted":
        from tests import test_scripted
        test_scripted.main()
    else:
        raise ValueError()


def run_bench(bench, opts):
    profile_benchmarks = opts["profile_benchmarks"]
    if bench in profile_benchmarks:
        # http://docs.python.org/library/profile.html#module-cProfile
        import cProfile, pstats
        prof = cProfile.Profile()
        prof = prof.runctx("_real_run_bench(bench, opts)", globals(), locals())
        stream = compat.StringIO()
        stats = pstats.Stats(prof, stream=stream)
#        stats.sort_stats("time")  # Or cumulative
        stats.sort_stats("cumulative")  # Or time
        stats.print_stats(80)  # 80 = how many to print
        # The rest is optional.
        # stats.print_callees()
        # stats.print_callers()
        logging.warning("Profile data for '%s':\n%s" % (bench, stream.getvalue()))
 
    else:
        _real_run_bench(bench, opts)


def bench_all(opts):
    run_bench("*", opts)


def main():
    opts = {"num": 10,
            "profile_benchmarks": ["*"],
            }    
    bench_all(opts)
    

if __name__ == "__main__":
    main()
