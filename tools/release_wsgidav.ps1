# Release WsgiDAV


$ProjectRoot = "C:\Prj\git\wsgidav";

#$BuildEnvRoot = "C:\prj\env\wsgidav_build_3.4";
#$BuildEnvRoot = "C:\prj\env\wsgidav_build_3.5";
$BuildEnvRoot = "C:\prj\env\wsgidav_build_3.6";
# $BuildEnvRoot = "C:\prj\env\wsgidav_build_3.7";


$IGNORE_UNSTAGED_CHANGES = 0;
$SKIP_TESTS = 0;

# ----------------------------------------------------------------------------
# Pre-checks

# Working directory must be clean
cd $ProjectRoot
git status
git diff --exit-code --quiet
if($LastExitCode -ne 0) {
   if( $IGNORE_UNSTAGED_CHANGES ) {
       Write-Warning "IGNORING UNSTAGED CHANGES!"
   } else {
       Write-Error "Unstaged changes: exiting."
       Exit 1
   }
}


# ----------------------------------------------------------------------------
# Create and activate a fresh build environment

cd $ProjectRoot

"Removing venv folder $BuildEnvRoot..."
Remove-Item $BuildEnvRoot -Force -Recurse -ErrorAction SilentlyContinue


"Creating venv folder $BuildEnvRoot..."
#py -3.4 -m venv "$BuildEnvRoot"
#py -3.5 -m venv "$BuildEnvRoot"
py -3.6 -m venv "$BuildEnvRoot"
# py -3.7 -m venv "$BuildEnvRoot"

Invoke-Expression "& ""$BuildEnvRoot\Scripts\Activate.ps1"""

# TODO: Check for 3.7
python --version

python -m pip install --upgrade pip

# Black is beta and needs --pre flag
python -m pip install --pre black

# 1. cx_Freeze does not compile here with Py3.7, so install from wheel
#    See https://www.lfd.uci.edu/~gohlke/pythonlibs/#cx_freeze
# 2. cx_freeze has a Bug with 3.7
#    https://stackoverflow.com/questions/51314105/cx-freeze-crashing-python3-7-0
python -m pip install tools/cx_Freeze-5.1.1-cp36-cp36m-win32.whl
#python -m pip install tools/cx_Freeze-5.1.1-cp37-cp37m-win32.whl

python -m pip install -r requirements-dev.txt
#python -m pip list
python -m pip install lxml
#python -m pip install cx_freeze cheroot defusedxml wheel
#python -m pip list

# Run tests
if( $SKIP_TESTS ) {
    Write-Warning "SKIPPING TESTS!"
} else {
    python setup.py test
    if($LastExitCode -ne 0) {
        Write-Error "Tests failed with exit code $LastExitCode"
        Exit 1
    }
}


# (optional) Do a test release
#python setup.py pypi_daily


#--- Create MSI installer
#    This call causes setup.py to import and use cx_Freeze:
python setup.py bdist_msi
if($LastExitCode -ne 0) {
   Write-Error "Create MSI failed with exit code $LastExitCode"
   Exit 1
}

#--- Create source distribution and Wheel
#    This call causes setup.py to NOT import and use cx_Freeze:

#python -m setup egg_info --tag-build="" -D sdist bdist_wheel --universal
#python -m setup egg_info --tag-build="" -D sdist bdist_wheel --universal register upload --sign --identity="Martin Wendt"
python -m setup egg_info --tag-build="" -D sdist bdist_wheel --universal

if($LastExitCode -ne 0) {
   Write-Error "Create Wheel and/or upload failed with exit code $LastExitCode"
   Exit 1
}

#--- Done.

"SUCCESS."
"We should now:"
"  1. twine upload dist\WsgiDAV-x.y.z.tar.gz"
"  2. twine upload dist\WsgiDAV-x.y.z-py2.py3-none-any.whl"
"  3. Release on GitHub"
"  4. Upload dist\WsgiDAV-x.y.z-win32.msi on GitHub"
"  5. Update changelog"
"  6. Bump version and commit/push"
