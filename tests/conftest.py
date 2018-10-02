# -*- coding: utf-8 -*-

import os
import pkg_resources
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
pkg_resources.require("wsgidav")
