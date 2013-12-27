@echo off

rem Run this with setup.py in current directory
rem Also make sure, that '.pypirc' is on the home path

@echo. 
@echo Uploading RELEASE BUILD to PyPI...
@echo. 
@echo Hit Ctrl-C to abort. 
@echo. 
pause
python setup.py egg_info --tag-build="" -RD sdist register upload --sign --identity="Martin Wendt"

start http://pypi.python.org/pypi/WsgiDAV/
