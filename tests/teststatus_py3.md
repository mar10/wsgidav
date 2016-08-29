# Results

## Test Status as of 2016-08-23

```
                             Py2.7  Py3.3  Py3.4  Py3.5
---------------------------------------------------------
tests/test_wsgidav_app.py    ok     ok     ok     ok
tests/test_scripted.py       ok     ok     ok     ok
tests/test_litmus.py         ok     ok     ok     ok
tests/*                      ok     ok     ok     ok
```

## Coverage

  - 2016-08-23   49%


## Benchmarks

NOTE: run twice and use 2nd result:
```sh
$ workon wsgidav3_py27
(wsgidav3_py27) $ python tests/benchmarks.py
```

### Summary

  - WsgiDAV 1.x on Python 2.7 is 10% faster than WsgiDAV 2.x on Python 2.7
  - WsgiDAV 2.x on Python 3.5 is 20% faster than WsgiDAV 2.x on Python 2.7  
  - WsgiDAV 2.x on Python 3.5 is 10% faster than WsgiDAV 1.x on Python 2.7


### Details
```
Date:     2016-08-29
OS:       Darwin-15.6.0-x86_64-i386-64bit
lxml:     (not installed)
#-- WsgiDAV Benchmark ---------------------------------------------
	WsgiDAV:  1.3.1pre1
	Python:   2.7.10
	Timing 'litmus test suite'  took  0.459 sec
	Timing 'Setup fixture'      took  0.013 sec
	Timing '1000 x PUT 1 kB'    took  4.069 sec,  245.8 req/sec,   0.246 MB/sec
	Timing '10 x PUT 10 MB'     took  1.931 sec,    5.2 req/sec,  51.774 MB/sec
	Timing '1000 x GET 1 kB'    took  3.202 sec,  312.3 req/sec,   0.312 MB/sec
	Timing '10 x GET 10 MB'     took  0.808 sec,   12.4 req/sec, 123.768 MB/sec
	Timing '10 x COPY 10 MB'    took  1.821 sec,    5.5 req/sec,  54.906 MB/sec
	Timing '100 x MOVE 10 MB'   took  0.406 sec,  246.0 req/sec
	Timing '100 x LOCK/UNLOCK'  took  0.759 sec,  263.4 req/sec
	Timing '1000 x PROPPATCH'   took  3.591 sec,  278.5 req/sec
	Timing '500 x PROPFIND'     took  6.126 sec,   81.6 req/sec
	Timing '>>> Summary >>>:'   took 23.231 sec
#-- WsgiDAV Benchmark ---------------------------------------------
	WsgiDAV:  2.0.0b1
	Python:   2.7.10
	Timing 'litmus test suite'  took  0.631 sec
	Timing 'Setup fixture'      took  0.014 sec
	Timing '1000 x PUT 1 kB'    took  4.477 sec,  223.4 req/sec,   0.223 MB/sec
	Timing '10 x PUT 10 MB'     took  1.828 sec,    5.5 req/sec,  54.694 MB/sec
	Timing '1000 x GET 1 kB'    took  3.917 sec,  255.3 req/sec,   0.255 MB/sec
	Timing '10 x GET 10 MB'     took  0.718 sec,   13.9 req/sec, 139.264 MB/sec
	Timing '10 x COPY 10 MB'    took  1.861 sec,    5.4 req/sec,  53.724 MB/sec
	Timing '100 x MOVE 10 MB'   took  0.493 sec,  202.8 req/sec
	Timing '100 x LOCK/UNLOCK'  took  0.957 sec,  209.0 req/sec
	Timing '1000 x PROPPATCH'   took  4.533 sec,  220.6 req/sec
	Timing '500 x PROPFIND'     took  6.575 sec,   76.0 req/sec
	Timing '>>> Summary >>>:'   took 26.051 sec
#-- WsgiDAV Benchmark ---------------------------------------------
	WsgiDAV:  2.0.0b1
	Python:   3.5.2
	Timing 'litmus test suite'  took  0.498 sec
	Timing 'Setup fixture'      took  0.015 sec
	Timing '1000 x PUT 1 kB'    took  4.200 sec,  238.1 req/sec,   0.238 MB/sec
	Timing '10 x PUT 10 MB'     took  2.185 sec,    4.6 req/sec,  45.766 MB/sec
	Timing '1000 x GET 1 kB'    took  2.336 sec,  428.2 req/sec,   0.428 MB/sec
	Timing '10 x GET 10 MB'     took  0.975 sec,   10.3 req/sec, 102.532 MB/sec
	Timing '10 x COPY 10 MB'    took  1.839 sec,    5.4 req/sec,  54.384 MB/sec
	Timing '100 x MOVE 10 MB'   took  0.338 sec,  295.4 req/sec
	Timing '100 x LOCK/UNLOCK'  took  0.605 sec,  330.5 req/sec
	Timing '1000 x PROPPATCH'   took  3.153 sec,  317.2 req/sec
	Timing '500 x PROPFIND'     took  4.795 sec,  104.3 req/sec
	Timing '>>> Summary >>>:'   took 20.995 sec

```
