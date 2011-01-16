# -*- coding: iso-8859-1 -*-
# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Unit tests for the WsgiDAV package.
"""

from tests import test_lock_manager, test_property_manager, test_wsgidav_app,\
    test_util, test_scripted
from unittest import TestSuite, TextTestRunner
import sys


def run():
    suite = TestSuite([test_util.suite(),
                       test_lock_manager.suite(),
                       test_property_manager.suite(),
                       test_wsgidav_app.suite(),
#                       test_scripted.suite(),
                       ])
    failures = TextTestRunner(descriptions=0, verbosity=2).run(suite)
    sys.exit(failures)



if __name__ == "__main__":
    run()
