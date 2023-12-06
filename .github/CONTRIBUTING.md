# Contribution Guideline

Thanks for contributing :-)

Please have a look at the
[Development Guide](http://wsgidav.readthedocs.io/en/latest/development.html).

<!--
## Setup for Contributors

We need [Python 2.7](https://www.python.org/downloads/), [Python 3.4+](https://www.python.org/downloads/), and [pip](https://pip.pypa.io/en/stable/installing/#do-i-need-to-install-pip) on our system:

Also virtualenv, virtualenvwrapper (may require sudo):

```
$ pip install virtualenv virtualenvwrapper
```

Then clone wsgidav to a local folder and checkout the branch you want to work on:

```
$ git clone git@github.com:mar10/wsgidav.git
$ cd wsgidav
$ git checkout my_branch
```

Setup a virtual environment with a specific Python version for development and
testing.
`-p` chooses the desired python version.
The `-a .` option associates the `wsgidav` source folder with the environment,
so we will change to this directory when `workon` is called.

For example Python 3.4
```
$ mkvirtualenv wsgidav_py34 -p /Library/Frameworks/Python.framework/Versions/3.4/bin/python3.4 -a .
$ workon wsgidav_py34
```

or using Python's builtin `venv` instead of `virtualenvwrapper`:
```
> py -3.4 -m venv c:\env\wsgidav_py34
> c:\env\wsgidav_py34\Scripts\activate.bat
```

The new environment exists and is activated.
Now install the development dependencies into that environment:
```
(wsgidav_py34) $ pip install -r requirements-dev.txt
```

Finally install wsgidav to the environment in a debuggable version
```
(wsgidav_py34) $ python setup.py develop
(wsgidav_py34) $ wsgidav --version
(wsgidav_py34) $ 1.3.0pre1
```

The test suite should run as well:
```
(wsgidav_py34) $ python setup.py test
```

Happy hacking :)
-->
