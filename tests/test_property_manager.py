# -*- coding: iso-8859-1 -*-
# (c) 2009-2015 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""Unit test for property_manager.py"""
from tempfile import gettempdir
import unittest

import os
import sys
from wsgidav import property_manager

#===============================================================================
# BasicTest
#===============================================================================
class BasicTest(unittest.TestCase):
    """Test property_manager.PropertyManager()."""
    respath = "/dav/res"

#     @classmethod
#     def suite(cls):
#         """Return test case suite (so we can control the order)."""
#         suite = TestSuite()
#         suite.addTest(cls("testPreconditions"))
#         suite.addTest(cls("testOpen"))
#         suite.addTest(cls("testValidation"))
#         suite.addTest(cls("testReadWrite"))
#         return suite


    def setUp(self):
        self.pm = property_manager.PropertyManager()
        self.pm._verbose = 2


    def tearDown(self):
        self.pm._close()
        self.pm = None


    def testPreconditions(self):
        """Environment must be set."""
        self.assertTrue(__debug__, "__debug__ must be True, otherwise asserts are ignored")


    def testOpen(self):
        """Property manager should be lazy opening on first access."""
        pm = self.pm
        assert not pm._loaded, "PM must be closed until first access"
        pm.getProperties(self.respath)
        assert pm._loaded, "PM must be opened after first access"


    def testValidation(self):
        """Property manager should raise errors on bad args."""
        pm = self.pm
        self.assertRaises(AssertionError,
                          pm.writeProperty, None, "{ns1:}foo", "hurz", False)
        # name must have a namespace
#        self.assertRaises(AssertionError,
#                          pm.writeProperty, "/dav/res", "foo", "hurz", False)
        self.assertRaises(AssertionError,
                          pm.writeProperty, "/dav/res", None, "hurz", False)
        self.assertRaises(AssertionError,
                          pm.writeProperty, "/dav/res", "{ns1:}foo", None, False)

        assert pm._dict is None, "No properties should have been created by this test"


    def testReadWrite(self):
        """Property manager should raise errors on bad args."""
        pm = self.pm
        url = "/dav/res"
        pm.writeProperty(url, "foo", "my name is joe")
        assert pm.getProperty(url, "foo") == "my name is joe"



#===============================================================================
# ShelveTest
#===============================================================================
class ShelveTest(BasicTest):
    """Test property_manager.ShelvePropertyManager()."""

    def setUp(self):
        if sys.version_info < (3, 0):
            modifier = "-py2" # shelve formats are incompatible
        else:
            modifier = "-py3"
        self.path = os.path.join(gettempdir(), "wsgidav-props%s.shelve" % modifier)
        # Note: os.remove(self.path) does not work, because Shelve may append
        # a file extension.
#        if os.path.exists(self.path):
#            os.remove(self.path)
        self.pm = property_manager.ShelvePropertyManager(self.path)
        self.pm._verbose = 1

    def tearDown(self):
#        self.pm.storage.clear()
        self.pm._close()
        self.pm = None
#        os.remove(self.path)


#===============================================================================


if __name__ == "__main__":
    unittest.main()
