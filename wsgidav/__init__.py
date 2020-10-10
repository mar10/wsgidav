# -*- coding: utf-8 -*-
"""
Current WsgiDAV version number.

See https://www.python.org/dev/peps/pep-0440

Examples
    Pre-releases (alpha, beta, release candidate):
        '3.0.0a1', '3.0.0b1', '3.0.0rc1'
    Final Release:
        '3.0.0'
    Developmental release (to mark 3.0.0 as 'used'. Don't publish this):
        '3.0.0.dev1'
NOTE:
    When pywin32 is installed, number must be a.b.c for MSI builds?
    "3.0.0a4" seems not to work in this case!
"""
__version__ = "3.0.5-a2"

# make version accessible as 'wsgidav.__version__'
# from wsgidav._version import __version__  # noqa: F401

# Initialize a silent 'wsgidav' logger
# http://docs.python-guide.org/en/latest/writing/logging/#logging-in-a-library
# https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
import logging


_base_logger = logging.getLogger(__name__)
_base_logger.addHandler(logging.NullHandler())
_base_logger.propagate = False
_base_logger.setLevel(logging.INFO)
