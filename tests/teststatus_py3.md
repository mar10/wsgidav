# Test Status and Performance

NOTE: run tes suite:
```sh
$ workon wsgidav3_py27
(wsgidav3_py27) $ python setup.py test
```

## Test Status as of 2016-08-23

```
                             Py2.7  Py3.3  Py3.4  Py3.5
---------------------------------------------------------
tests/test_wsgidav_app.py    ok     ok     ok     ok
tests/test_scripted.py       ok     ok     ok     ok
tests/test_litmus.py         ok     ok     ok     ok
tests/*                      ok     ok     ok     ok
```

#### Coverage

  - 2016-08-23   49%


## Performance

[CherryPy seems to be a good choice](https://blog.appdynamics.com/python/a-performance-analysis-of-python-wsgi-servers-part-2/)
 for the default standalone mode.


#### Benchmarks

NOTE: run twice and use 2nd result, for example:
```sh
$ workon wsgidav3_py27
(wsgidav3_py27) $ python tests/benchmarks.py
```

#### Summary

Those benchmarks are pretty naive and may not reflect the actual runtime 
behavior, but anyway:

  - WsgiDAV 2.x on Python 3.5 is 20% faster than WsgiDAV 2.x on Python 2.7  
                             and 10% faster than WsgiDAV 1.x on Python 2.7
  - WsgiDAV 1.x on Python 2.7 is 10% faster than WsgiDAV 2.x on Python 2.7

  - lxml improvemes performance of propfind/proppatch by aprox. 10%


#### Details
```
#-- WsgiDAV Benchmark ---------------------------------------------
Date:     2016-09-05
WsgiDAV:  1.3.1pre1
Python:   2.7.10
CherryPy: CherryPy/3.2.4
OS:       Darwin-15.6.0-x86_64-i386-64bit
lxml:     (not installed)
Starting WsgiDavTestServer...
Timing 'litmus test suite'  took  0.436 sec
Timing 'Setup fixture'      took  0.016 sec
Timing '1000 x PUT 1 kB'    took  3.531 sec,  283.2 req/sec,   0.283 MB/sec
Timing '10 x PUT 10 MB'     took  1.918 sec,    5.2 req/sec,  52.127 MB/sec
Timing '1000 x GET 1 kB'    took  3.132 sec,  319.3 req/sec,   0.319 MB/sec
Timing '10 x GET 10 MB'     took  0.743 sec,   13.5 req/sec, 134.663 MB/sec
Timing '10 x COPY 10 MB'    took  1.815 sec,    5.5 req/sec,  55.109 MB/sec
Timing '100 x MOVE 10 MB'   took  0.375 sec,  266.9 req/sec
Timing '100 x LOCK/UNLOCK'  took  0.726 sec,  275.5 req/sec
Timing '1000 x PROPPATCH'   took  3.526 sec,  283.6 req/sec
Timing '500 x PROPFIND'     took  5.961 sec,   83.9 req/sec
Timing '>>> Summary >>>:'   took 22.224 sec
#-- WsgiDAV Benchmark ---------------------------------------------
Date:     2016-09-05
WsgiDAV:  1.3.1pre1
Python:   2.7.10
CherryPy: CherryPy/3.2.4
OS:       Darwin-15.6.0-x86_64-i386-64bit
lxml:     (not installed)
Starting WsgiDavTestServer...
Timing 'litmus test suite'  took  0.417 sec
Timing 'Setup fixture'      took  0.012 sec
Timing '1000 x PUT 1 kB'    took  3.508 sec,  285.1 req/sec,   0.285 MB/sec
Timing '10 x PUT 10 MB'     took  1.928 sec,    5.2 req/sec,  51.861 MB/sec
Timing '1000 x GET 1 kB'    took  3.030 sec,  330.0 req/sec,   0.330 MB/sec
Timing '10 x GET 10 MB'     took  0.690 sec,   14.5 req/sec, 144.942 MB/sec
Timing '10 x COPY 10 MB'    took  1.825 sec,    5.5 req/sec,  54.807 MB/sec
Timing '100 x MOVE 10 MB'   took  0.407 sec,  245.9 req/sec
Timing '100 x LOCK/UNLOCK'  took  0.673 sec,  297.1 req/sec
Timing '1000 x PROPPATCH'   took  3.287 sec,  304.2 req/sec
Timing '500 x PROPFIND'     took  4.402 sec,  113.6 req/sec
Timing '>>> Summary >>>:'   took 20.225 sec
#-- WsgiDAV Benchmark ---------------------------------------------
Date:     2016-09-05
WsgiDAV:  2.0.0b1
Python:   2.7.10
CherryPy: 7.1.0
OS:       Darwin-15.6.0-x86_64-i386-64bit
lxml:     (not installed)
Starting WsgiDavTestServer...
Timing 'litmus test suite'  took  0.626 sec
Timing 'Setup fixture'      took  0.016 sec
Timing '1000 x PUT 1 kB'    took  5.452 sec,  183.4 req/sec,   0.183 MB/sec
Timing '10 x PUT 10 MB'     took  1.341 sec,    7.5 req/sec,  74.580 MB/sec
Timing '1000 x GET 1 kB'    took  3.700 sec,  270.2 req/sec,   0.270 MB/sec
Timing '10 x GET 10 MB'     took  0.731 sec,   13.7 req/sec, 136.775 MB/sec
Timing '10 x COPY 10 MB'    took  1.173 sec,    8.5 req/sec,  85.265 MB/sec
Timing '100 x MOVE 10 MB'   took  0.480 sec,  208.5 req/sec
Timing '100 x LOCK/UNLOCK'  took  0.957 sec,  208.9 req/sec
Timing '1000 x PROPPATCH'   took  4.471 sec,  223.7 req/sec
Timing '500 x PROPFIND'     took  6.461 sec,   77.4 req/sec
Timing '>>> Summary >>>:'   took 25.445 sec
#-- WsgiDAV Benchmark ---------------------------------------------
Date:     2016-09-05
WsgiDAV:  2.0.0b1
Python:   2.7.10
CherryPy: 7.1.0
OS:       Darwin-15.6.0-x86_64-i386-64bit
lxml:     (3, 6, 4, 0)
Starting WsgiDavTestServer...
Timing 'litmus test suite'  took  0.665 sec
Timing 'Setup fixture'      took  0.014 sec
Timing '1000 x PUT 1 kB'    took  5.527 sec,  180.9 req/sec,   0.181 MB/sec
Timing '10 x PUT 10 MB'     took  1.891 sec,    5.3 req/sec,  52.881 MB/sec
Timing '1000 x GET 1 kB'    took  3.617 sec,  276.5 req/sec,   0.277 MB/sec
Timing '10 x GET 10 MB'     took  0.732 sec,   13.7 req/sec, 136.637 MB/sec
Timing '10 x COPY 10 MB'    took  1.832 sec,    5.5 req/sec,  54.591 MB/sec
Timing '100 x MOVE 10 MB'   took  0.465 sec,  215.2 req/sec
Timing '100 x LOCK/UNLOCK'  took  0.894 sec,  223.7 req/sec
Timing '1000 x PROPPATCH'   took  4.147 sec,  241.1 req/sec
Timing '500 x PROPFIND'     took  5.601 sec,   89.3 req/sec
Timing '>>> Summary >>>:'   took 25.426 sec
#-- WsgiDAV Benchmark ---------------------------------------------
Date:     2016-09-05
WsgiDAV:  2.0.0b1
Python:   3.5.2
CherryPy: 7.1.0
OS:       Darwin-15.6.0-x86_64-i386-64bit
lxml:     (not installed)
Starting WsgiDavTestServer...
Timing 'litmus test suite'  took  0.498 sec
Timing 'Setup fixture'      took  0.016 sec
Timing '1000 x PUT 1 kB'    took  4.869 sec,  205.4 req/sec,   0.205 MB/sec
Timing '10 x PUT 10 MB'     took  2.120 sec,    4.7 req/sec,  47.164 MB/sec
Timing '1000 x GET 1 kB'    took  2.297 sec,  435.4 req/sec,   0.435 MB/sec
Timing '10 x GET 10 MB'     took  0.946 sec,   10.6 req/sec, 105.749 MB/sec
Timing '10 x COPY 10 MB'    took  1.847 sec,    5.4 req/sec,  54.141 MB/sec
Timing '100 x MOVE 10 MB'   took  0.334 sec,  299.1 req/sec
Timing '100 x LOCK/UNLOCK'  took  0.597 sec,  335.2 req/sec
Timing '1000 x PROPPATCH'   took  3.167 sec,  315.8 req/sec
Timing '500 x PROPFIND'     took  4.650 sec,  107.5 req/sec
Timing '>>> Summary >>>:'   took 21.386 sec
Stopping WsgiDavTestServer... done.
#-- WsgiDAV Benchmark ---------------------------------------------
Date:     2016-09-05
WsgiDAV:  2.0.0b1
Python:   3.5.2
CherryPy: 7.1.0
OS:       Darwin-15.6.0-x86_64-i386-64bit
lxml:     (3, 6, 4, 0)
Starting WsgiDavTestServer...
Timing 'litmus test suite'  took  0.491 sec
Timing 'Setup fixture'      took  0.016 sec
Timing '1000 x PUT 1 kB'    took  4.574 sec,  218.6 req/sec,   0.219 MB/sec
Timing '10 x PUT 10 MB'     took  1.442 sec,    6.9 req/sec,  69.357 MB/sec
Timing '1000 x GET 1 kB'    took  2.272 sec,  440.1 req/sec,   0.440 MB/sec
Timing '10 x GET 10 MB'     took  0.948 sec,   10.6 req/sec, 105.512 MB/sec
Timing '10 x COPY 10 MB'    took  1.140 sec,    8.8 req/sec,  87.731 MB/sec
Timing '100 x MOVE 10 MB'   took  0.332 sec,  301.4 req/sec
Timing '100 x LOCK/UNLOCK'  took  0.567 sec,  352.9 req/sec
Timing '1000 x PROPPATCH'   took  2.886 sec,  346.5 req/sec
Timing '500 x PROPFIND'     took  4.164 sec,  120.1 req/sec
Timing '>>> Summary >>>:'   took 18.880 sec

```
