rem @echo off

rem Goto \wsgidav folder
cd %~dp0..

rem @echo on
call \prj\env\wsgidav34\Scripts\activate.bat

python setup.py test
if %ERRORLEVEL% != 0 (
	pause
    exit
)

python setup.py bdist_msi
start %~dp0..\dist
pause
