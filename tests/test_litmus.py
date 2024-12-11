# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
r"""
Run the [Litmus test suite](http://www.webdav.org/neon/litmus/) against WsgiDAV
server.

## Usage

**NOTE:** replace <HOST_IP> with the real IP address of the test client.


### 1. Edit Configuration File


```yaml
host: <HOST_IP>
port: 8080
...
```

### 2. Run WsgiDAV

```bash
$ cd WSGIDAV-ROOT
$ wsgidav --config tests\wsgidav-litmus.yaml -H <HOST_IP>
```


### 3. Run Litmus Suite as Docker Container

[Install Docker](https://docs.docker.com/desktop/).

Then open a new console and run these commands:

```bash
$ docker pull mar10/docker-litmus
$ docker run --rm -ti mar10/docker-litmus https://<HOST_IP>:8080/ tester secret
```

Output should look something like this:
```
$ docker run --rm -ti mar10/docker-litmus https://192.168.178.35:8080 tester secret
-> running `basic':
 0. init.................. pass
 ...
15. finish................ pass
<- summary for `basic': of 16 tests run: 16 passed, 0 failed. 100.0%
-> running `copymove':
 0. init.................. pass
 ...
12. finish................ pass
<- summary for `copymove': of 13 tests run: 13 passed, 0 failed. 100.0%
-> running `props':
 0. init.................. pass
 ...
29. finish................ pass
<- summary for `props': of 30 tests run: 30 passed, 0 failed. 100.0%
-> running `locks':
 0. init.................. pass
 ...
40. finish................ pass
<- summary for `locks': of 41 tests run: 41 passed, 0 failed. 100.0%
-> running `http':
 0. init.................. pass
 ...
 3. finish................ pass
-> 1 test was skipped.
<- summary for `http': of 3 tests run: 3 passed, 0 failed. 100.0%
$
```

See here for details on the Docker image: https://github.com/mar10/docker-litmus
"""

import subprocess
import unittest

from tests.util import WsgiDavTestServer

# ========================================================================
# WsgiDAVServerTest
# ========================================================================


class WsgiDAVLitmusTest(unittest.TestCase):
    """Run litmus test suite against builtin server."""

    _litmus_connect_failed = None

    def setUp(self):
        if WsgiDAVLitmusTest._litmus_connect_failed:
            self._report_missing_litmus(" (again)")

    def tearDown(self):
        pass

    def _report_missing_litmus(self, extra=""):
        WsgiDAVLitmusTest._litmus_connect_failed = True
        print("*" * 70)
        print("This test requires the litmus test suite.")
        print("See https://github.com/mar10/docker-litmus")
        print("*" * 70)
        raise unittest.SkipTest(f"Test requires litmus test suite{extra}")

    def test_litmus_with_authentication(self):
        """Run litmus test suite on HTTP with authentication."""
        with WsgiDavTestServer(with_auth=True, with_ssl=False):
            try:
                res = subprocess.call(
                    ["litmus", "http://127.0.0.1:8080/", "tester", "secret"]
                )
                self.assertEqual(res, 0, "litmus suite failed: check the log")
            except OSError:
                self._report_missing_litmus()
                raise
        return

    def test_litmus_anonymous(self):
        """Run litmus test suite on HTTP with authentication."""
        with WsgiDavTestServer(with_auth=False, with_ssl=False):
            try:
                res = subprocess.call(["litmus", "http://127.0.0.1:8080/"])
                self.assertEqual(res, 0, "litmus suite failed: check the log")
            except OSError:
                self._report_missing_litmus()
                raise
        return

    def test_litmus_with_ssl_and_authentication(self):
        """Run litmus test suite on SSL / HTTPS with authentication."""
        with WsgiDavTestServer(with_auth=True, with_ssl=True):
            try:
                res = subprocess.call(
                    ["litmus", "https://127.0.0.1:8080/", "tester", "secret"]
                )
                self.assertEqual(res, 0, "litmus suite failed: check the log")
            except OSError:
                self._report_missing_litmus()
                raise
        return


# ========================================================================
# suite
# ========================================================================

if __name__ == "__main__":
    unittest.main()
