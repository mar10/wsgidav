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
(wsgidav3_py27) $ python tests/bencmarks.py
```

```
2016-08-27, wsgdav 2.0.0
	On Python 2.7:
		Timing 'Setup fixture'      took  0.018 sec
		Timing '1000 x PUT 1 kB'    took  4.267 sec,  234.4 req/sec,   0.234 MB/sec
		Timing '10 x PUT 10 MB'     took  1.901 sec,    5.3 req/sec,  52.595 MB/sec
		Timing '1000 x GET 1 kB'    took  3.827 sec,  261.3 req/sec,   0.261 MB/sec
		Timing '10 x GET 10 MB'     took  0.743 sec,   13.5 req/sec, 134.659 MB/sec
		Timing '10 x COPY 10 MB'    took  1.817 sec,    5.5 req/sec,  55.034 MB/sec
		Timing '100 x MOVE 10 MB'   took  0.496 sec,  201.7 req/sec
		Timing '100 x LOCK/UNLOCK'  took  0.991 sec,  201.7 req/sec
		Timing '1000 x PROPPATCH'   took  4.637 sec,  215.6 req/sec
		Timing '500 x PROPFIND'     took  5.701 sec,   87.7 req/sec
		Timing 'Test suite, WsgiDAV 2.0.0b1, Python 2.7.10' took 24.449 sec
	On Python 3.5:
		Timing 'Setup fixture'      took  0.017 sec
		Timing '1000 x PUT 1 kB'    took  3.291 sec,  303.9 req/sec,   0.304 MB/sec
		Timing '10 x PUT 10 MB'     took  2.020 sec,    5.0 req/sec,  49.504 MB/sec
		Timing '1000 x GET 1 kB'    took  2.289 sec,  436.9 req/sec,   0.437 MB/sec
		Timing '10 x GET 10 MB'     took  0.949 sec,   10.5 req/sec, 105.377 MB/sec
		Timing '10 x COPY 10 MB'    took  1.816 sec,    5.5 req/sec,  55.051 MB/sec
		Timing '100 x MOVE 10 MB'   took  0.332 sec,  300.8 req/sec
		Timing '100 x LOCK/UNLOCK'  took  0.601 sec,  333.0 req/sec
		Timing '1000 x PROPPATCH'   took  3.128 sec,  319.6 req/sec
		Timing '500 x PROPFIND'     took  4.001 sec,  125.0 req/sec
		Timing 'Test suite, WsgiDAV 2.0.0b1, Python 3.5.2' took 18.514 sec
```
