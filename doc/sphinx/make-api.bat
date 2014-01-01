REM python generate_modules.py --dry-run ../../wsgidav --doc-header="WsgiDAV API" --dest-dir="api-doc"

PAUSE

sphinx-apidoc -H "WsgiDAV API" -V "1.1" -R "1.1" -A "Martin Wendt" -o api-doc ../../wsgidav ../../wsgidav/server/cherrypy
