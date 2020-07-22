# Benchmarks results

**2020-07-22**

```
This scenario runs some tests against a WebDAV server.
We use it to test stressor against a locally running WsgiDAV server:
- Open a terminal and run
  $ wsgidav --root tests/stressor/htdocs/ --host 127.0.0.1 --port 8082 --auth anonymous --no-config -q

- Open a second terminal and run
  $ stressor run tests/stressor/test_rw.yaml -q
```

```bash
$ stressor -Vv
stressor/0.2.0 Python/64(3.7.7 bit) Darwin-19.5.0-x86_64-i386-64bit
Python from: /Users/martin/.local/share/virtualenvs/wsgidav-9PbuForg/bin/python
$ wsgidav -Vv
WsgiDAV/3.0.4 Python/3.7.7(64 bit) Darwin-19.5.0-x86_64-i386-64bit
Python from: /Users/martin/.local/share/virtualenvs/wsgidav-9PbuForg/bin/python3.7
```

## Cheroot v7.0.0

(wsgidav) martin@MacMoogle wsgidav % stressor run tests/stressor/test_rw.yaml -q
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


## Cheroot v8.0.0

(wsgidav) martin@MacMoogle wsgidav % stressor run tests/stressor/test_rw.yaml -q
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
(wsgidav) martin@MacMoogle wsgidav %


## Cheroot v8.1.0

(wsgidav) martin@MacMoogle wsgidav % stressor run tests/stressor/test_rw.yaml -q
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


## Cheroot v8.3.1

(wsgidav) martin@MacMoogle wsgidav % stressor run tests/stressor/test_rw.yaml -q
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
(wsgidav) martin@MacMoogle wsgidav %

