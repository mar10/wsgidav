rem @echo off

rem Goto \wsgidav folder
cd %~dp0..

rem @echo on
call \prj\env\wsgidav34\Scripts\activate.bat

python setup.py test
if %ERRORLEVEL% neq 0 (
	echo Error %ERRORLEVEL%. Exiting...
	pause
    exit /b 1
)

@echo. 
@echo Uploading daily build to PyPI...
@echo. 
@echo Hit Ctrl-C to abort. 
@echo. 
pause
python setup.py egg_info --tag-build=".dev" --tag-date sdist register upload --sign --identity="Martin Wendt"

start http://pypi.python.org/pypi/WsgiDAV/
pause
