---
name: run-wsgidav
description: Start a local WsgiDAV server on a temporary folder to manually check a change (WebDAV requests, DAV Explorer, or dir browser), then stop it. Use when asked to run, start, or try out the server or web UI.
---

# Run a local WsgiDAV server

Use this to see a change working against a real server. Automated tests remain
the primary check (`uv run pytest -ra tests/test_<area>.py`).

## 1. Prepare a temporary share

```sh
ROOT=$(mktemp -d)
mkdir -p "$ROOT/folder/sub"
echo "hello" > "$ROOT/readme.txt"
echo "nested" > "$ROOT/folder/nested.txt"
```

## 2. Start the server in the background

Pick a free port (default 8080) and the web UI to check
(`dav-explorer`, `dir-browser`, or `none`):

```sh
uv run wsgidav --no-config --host 127.0.0.1 --port 8080 \
    --root "$ROOT" --auth anonymous --web-ui dav-explorer -v
```

Run it with the Bash tool's background option, not with `&`.
`--no-config` keeps a local `wsgidav.yaml` from changing the setup.

Safety: bind to `127.0.0.1` only. Never combine `--auth anonymous` with a
public host such as `0.0.0.0`.

## 3. Verify

Wait until the port answers, then:

```sh
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/        # 200 (web UI)
curl -s -i -X PROPFIND -H "Depth: 1" http://127.0.0.1:8080/ | head -1  # 207 Multi-Status
curl -s -T "$ROOT/readme.txt" http://127.0.0.1:8080/upload.txt -w "%{http_code}\n"  # 201
```

For UI checks, open `http://127.0.0.1:8080/` in a browser tool if one is
available, and check the browser console for JavaScript errors.

## 4. Clean up

Stop the background server process and remove the temporary folder:

```sh
rm -rf "$ROOT"
```

Report the observed status codes and any server log errors.
