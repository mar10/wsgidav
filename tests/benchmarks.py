# -*- coding: iso-8859-1 -*-
# (c) 2009 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
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
