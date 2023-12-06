# Benchmarks results
```
This scenario runs some tests against a WebDAV server.
We use it to test stressor against a locally running WsgiDAV server:

1. cd <prj>/wsgidav
2. Open a terminal and run
  $ wsgidav --root tests/stressor/htdocs/ --host 127.0.0.1 --port 8082 --auth anonymous --no-config -q
3. Open a second terminal and run
  $ stressor run tests/stressor/test_rw.yaml -q
```

## 2022-01-04
WsgiDAV 4.0.0-a2
Runtime 30 secs, 10 parallel sessions
The script GETs a static file, PUTs a new file, GETs that file, and loops again.

### Windows 10, Ryzen 5 @ 3.9 GHz

- Cheroot 8.3.1 Executed  2,760 activities (~ 9 requests per user per second)
- Cheroot 8.5.2 Executed 23,584 activities (~ 78 requests per user per second)
- Cheroot 8.6.0 Executed  8,640 activities (~ 28 requests per user per second)

Same scenario, different no. of parallel users. Best of 3

|               |          | #1     | #2     | #3     | Best   |
| ------------- | -------- | ------ | ------ | ------ | ------ |
| Cheroot 8.5.2 |  5 users |  9,160 |  9,672 |  9,180 |  9,672 |
|               | 10 users | 22,532 | 21,708 | 23,312 | 23,312 |
|               | 20 users | 23,528 | 23,516 | 23,544 | 23,544 |
| Cheroot 8.6.0 |  5 users |  2,540 |  2,540 |  2,540 |  2,540 |
|               | 10 users |  5,008 | 10,080 |  6,604 | 10,080 |
|               | 20 users | 23,720 | 23,404 | 23,596 | 23,596 |

### macOS 12, i5 @ 2.9 GHz

- Cheroot 8.3.1 Executed   5,468 activities (~ 18 requests per user per second)
- Cheroot 8.5.2 Executed  12,596 activities (~ 42 requests per user per second)
- Cheroot 8.6.0 Executed  12,660 activities (~ 42 requests per user per second)


## 2021-11-09
> Seems that stressor is the limiting factor
(MacBook, i5 2,9GHz, macOs 12.0.1, Py3.9)
- Cheroot 8.5.2 Executed 9,700 activities
- gevent 21.8.0 Executed 9,704 activities
- gunicorn 20.1.0 Executed 9,324 activities
- uvicorn 0.15.0 Executed 8,036 activities
- paste 0.5 Executed 9,756 activities
- wsgiref 0.2 Executed 8,188 activities ERRORS: 27 (NewConnectionError)
- ext_wsgiutils Executed 9,668 activities

## 2021-01-04
(PC, Windows 10)
- Cheroot 8.5.1 Executed 16,660 activities
- Cheroot 8.4.8 Executed 16,364 activities
- Cheroot 8.3.1 Executed 2,928 activities
- Cheroot 8.2.1 Executed 2,828 activities
- Cheroot 8.1.0 Executed 2,960 activities
- Cheroot 8.0.0: Executed 17,092 activities
- gevent 20.12.1: Executed 15,420 activities

<details>
  <summary>Click to expand details</summary>


```
> stressor -Vv
stressor/0.5.1-a1 Python/3.9.1(64 bit) Windows-10-10.0.19041-SP0
> wsgidav -Vv
WsgiDAV/3.0.5-a4 Python/3.9.1(64 bit) Windows-10-10.0.19041-SP0
```

### Cheroot 8.5.1
```
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2021-01-04 21:24:12
  End:      2021-01-04 21:24:42
Run time 30.281 sec, net: 4:58.43 min.
Executed 16,660 activities in 4,175 sequences, using 10 parallel sessions.
Sequence duration: 0.007253 sec average.
             rate: 8,273 sequences per minute (per user: 827.3).
Activity rate:     550.2 activities per second (per user: 55.02).
3 monitored activities:
  - /main/1/GetRequest(/private/test.html)
    n: 4,155, min: 0.004999 sec, avg: 0.011 sec, max: 0.035 sec
  - /main/2/PutRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 4,155, min: 0.007987 sec, avg: 0.019 sec, max: 0.046 sec
  - /main/3/GetRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 4,155, min: 0.004061 sec, avg: 0.018 sec, max: 0.048 sec
Result: Ok.
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
```

### Cheroot 8.4.8
```
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2021-01-04 21:22:12
  End:      2021-01-04 21:22:42
Run time 30.265 sec, net: 4:58.40 min.
Executed 16,364 activities in 4,101 sequences, using 10 parallel sessions.
Sequence duration: 0.007380 sec average.
             rate: 8,130 sequences per minute (per user: 813.0).
Activity rate:     540.7 activities per second (per user: 54.07).
3 monitored activities:
  - /main/1/GetRequest(/private/test.html)
    n: 4,081, min: 0.004999 sec, avg: 0.012 sec, max: 0.042 sec
  - /main/2/PutRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 4,081, min: 0.003999 sec, avg: 0.019 sec, max: 0.059 sec
  - /main/3/GetRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 4,081, min: 0.007000 sec, avg: 0.018 sec, max: 0.072 sec
Result: Ok.
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
```

### Cheroot 8.3.1
```
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2021-01-04 21:20:48
  End:      2021-01-04 21:21:19
Run time 30.453 sec, net: 5:01.63 min.
Executed 2,928 activities in 742 sequences, using 10 parallel sessions.
Sequence duration: 0.041 sec average.
             rate: 1,462 sequences per minute (per user: 146.2).
Activity rate:     96.15 activities per second (per user: 9.615).
3 monitored activities:
  - /main/1/GetRequest(/private/test.html)
    n: 722, min: 0.006999 sec, avg: 0.085 sec, max: 0.155 sec
  - /main/2/PutRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 722, min: 0.008998 sec, avg: 0.106 sec, max: 0.147 sec
  - /main/3/GetRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 722, min: 0.009990 sec, avg: 0.100 sec, max: 0.139 sec
Result: Ok.
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
```

### Cheroot 8.2.1
```
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2021-01-04 21:18:48
  End:      2021-01-04 21:19:18
Run time 30.547 sec, net: 5:01.84 min.
Executed 2,828 activities in 717 sequences, using 10 parallel sessions.
Sequence duration: 0.043 sec average.
             rate: 1,408 sequences per minute (per user: 140.8).
Activity rate:     92.58 activities per second (per user: 9.258).
3 monitored activities:
  - /main/1/GetRequest(/private/test.html)
    n: 697, min: 0.007997 sec, avg: 0.089 sec, max: 0.143 sec
  - /main/2/PutRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 697, min: 0.014 sec, avg: 0.108 sec, max: 0.148 sec
  - /main/3/GetRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 697, min: 0.013 sec, avg: 0.105 sec, max: 0.146 sec
Result: Ok.
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
```

### Cheroot 8.1.0
```
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2021-01-04 21:17:07
  End:      2021-01-04 21:17:37
Run time 30.485 sec, net: 5:01.40 min.
Executed 2,960 activities in 750 sequences, using 10 parallel sessions.
Sequence duration: 0.041 sec average.
             rate: 1,476 sequences per minute (per user: 147.6).
Activity rate:     97.1 activities per second (per user: 9.71).
3 monitored activities:
  - /main/1/GetRequest(/private/test.html)
    n: 730, min: 0.005002 sec, avg: 0.083 sec, max: 0.141 sec
  - /main/2/PutRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 730, min: 0.012 sec, avg: 0.105 sec, max: 0.156 sec
  - /main/3/GetRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 730, min: 0.011 sec, avg: 0.099 sec, max: 0.138 sec
Result: Ok.
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
```

### Cheroot 8.0.0
```
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2021-01-04 21:13:26
  End:      2021-01-04 21:13:56
Run time 30.281 sec, net: 4:58.11 min.
Executed 17,092 activities in 4,283 sequences, using 10 parallel sessions.
Sequence duration: 0.007070 sec average.
             rate: 8,487 sequences per minute (per user: 848.7).
Activity rate:     564.4 activities per second (per user: 56.44).
3 monitored activities:
  - /main/1/GetRequest(/private/test.html)
    n: 4,263, min: 0.002996 sec, avg: 0.010 sec, max: 0.031 sec
  - /main/2/PutRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 4,263, min: 0.004000 sec, avg: 0.018 sec, max: 0.058 sec
  - /main/3/GetRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 4,263, min: 0.002999 sec, avg: 0.017 sec, max: 0.045 sec
Result: Ok.
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
```

### gevent 20.12.1

> Compared to gevent as Wsgi-Server
```
$ pip install gevent
$ wsgidav --root tests/stressor/htdocs/ --host 127.0.0.1 --port 8082 --auth anonymous --no-config --server gevent -q
```
```
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2021-01-04 21:43:29
  End:      2021-01-04 21:43:59
Run time 30.266 sec, net: 4:58.30 min.
Executed 15,420 activities in 3,865 sequences, using 10 parallel sessions.
Sequence duration: 0.007831 sec average.
             rate: 7,662 sequences per minute (per user: 766.2).
Activity rate:     509.5 activities per second (per user: 50.95).
3 monitored activities:
  - /main/1/GetRequest(/private/test.html)
    n: 3,845, min: 0.005235 sec, avg: 0.018 sec, max: 0.033 sec
  - /main/2/PutRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 3,845, min: 0.006213 sec, avg: 0.019 sec, max: 0.039 sec
  - /main/3/GetRequest(/temp/wsgidav_test_file~$(session_id).txt)
    n: 3,845, min: 0.002064 sec, avg: 0.019 sec, max: 0.036 sec
Result: Ok.
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
```

</details>


## 2020-07-22

(macBook Pro)

- Cheroot v8.4.0 Executed 2,920 activities
- Cheroot v8.3.1 Executed 2,920 activities
- Cheroot v8.1.0 Executed 2,960 activities
- Cheroot v8.0.0 Executed 11,872 activities
- Cheroot v7.0.0 Executed 10,020 activities
- **gevent 20.6.2** Executed 12,388 activities

<details>
  <summary>Click to expand details</summary>

```bash
$ stressor -Vv
stressor/0.2.0 Python/3.7.7(64 bit) Darwin-19.5.0-x86_64-i386-64bit
$ wsgidav -Vv
WsgiDAV/3.0.4 Python/3.7.7(64 bit) Darwin-19.5.0-x86_64-i386-64bit
```

### Cheroot v7.0.0

**10.0k activities per 30 sec**
```
$ stressor run tests/stressor/test_rw.yaml -q
22:53:32.466 <4672335296> NOTE    All 10 sessions running, waiting for them to terminate...
22:54:02.696 <4672335296> NOTE    Result Summary:
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2020-07-22 22:53:32
  End:      2020-07-22 22:54:02
Run time 0:00:30.256000, net: 4:58.62 min.
Executed 10,020 activities in 2,515 sequences, using 10 parallel sessions.
Result: Ok. ✨ 🍰 ✨
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
```

### Cheroot v8.0.0

**11.8k activities per 30 sec**
```
$ stressor run tests/stressor/test_rw.yaml -q
22:54:36.489 <4595936704> NOTE    All 10 sessions running, waiting for them to terminate...
22:55:06.708 <4595936704> NOTE    Result Summary:
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2020-07-22 22:54:36
  End:      2020-07-22 22:55:06
Run time 0:00:30.242884, net: 4:58.50 min.
Executed 11,872 activities in 2,978 sequences, using 10 parallel sessions.
Result: Ok. ✨ 🍰 ✨
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
$
```


### Cheroot v8.1.0

**2.9k activities per 30 sec**
**Major Performance Drop Introduced with v8.1.0**
```
$ stressor run tests/stressor/test_rw.yaml -q
23:00:22.793 <4745440704> NOTE    All 10 sessions running, waiting for them to terminate...
23:00:53.304 <4745440704> NOTE    Result Summary:
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2020-07-22 23:00:22
  End:      2020-07-22 23:00:53
Run time 0:00:30.528596, net: 5:03.18 min.
Executed 2,960 activities in 750 sequences, using 10 parallel sessions.
Result: Ok. ✨ 🍰 ✨
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
```


### Cheroot v8.3.1

**2.9k activities per 30 sec**
```
$ stressor run tests/stressor/test_rw.yaml -q
23:04:10.270 <4582501824> NOTE    All 10 sessions running, waiting for them to terminate...
23:04:40.757 <4582501824> NOTE    Result Summary:
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2020-07-22 23:04:10
  End:      2020-07-22 23:04:40
Run time 0:00:30.499292, net: 5:02.85 min.
Executed 2,920 activities in 740 sequences, using 10 parallel sessions.
Result: Ok. ✨ 🍰 ✨
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
$
```

## Cheroot v8.4.0

**2.9k activities per 30 sec**
```
$ stressor run tests/stressor/test_rw.yaml -q
18:22:11.218 <4554210752> NOTE    All 10 sessions running, waiting for them to terminate...
18:22:41.714 <4554210752> NOTE    Result Summary:
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2020-07-23 18:22:11
  End:      2020-07-23 18:22:41
Run time 0:00:30.509040, net: 5:02.92 min.
Executed 2,920 activities in 740 sequences, using 10 parallel sessions.
Result: Ok. ✨ 🍰 ✨
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
$
```

### gevent 20.6.2

> Compared to gevent as Wsgi-Server
```
$ wsgidav --root tests/stressor/htdocs/ --host 127.0.0.1 --port 8082 --auth anonymous --no-config --server gevent -q
```
```
$ stressor run tests/stressor/test_rw.yaml -q
18:13:41.249 <4513201600> NOTE    All 10 sessions running, waiting for them to terminate...
18:14:11.469 <4513201600> NOTE    Result Summary:
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
Stressor scenario 'test_rw' finished.
  Tag:      'n.a.'
  Base URL: http://127.0.0.1:8082
  Start:    2020-07-23 18:13:41
  End:      2020-07-23 18:14:11
Run time 0:00:30.232158, net: 4:58.41 min.
Executed 12,388 activities in 3,107 sequences, using 10 parallel sessions.
Result: Ok. ✨ 🍰 ✨
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
$
```
</details>
