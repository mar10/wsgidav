# make version accessible as 'wsgidav.__version__'
# noqa: F401
from wsgidav._version import __version__

# Initialize a silent 'wsgidav' logger
# http://docs.python-guide.org/en/latest/writing/logging/#logging-in-a-library
# https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
