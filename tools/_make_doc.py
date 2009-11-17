import os
import sys
from epydoc import cli
import webbrowser

sys.path.append("..")
# Call epidoc with command arg
assert len(sys.argv) == 1, "This module must be called without args"
sys.argv.append("--config=epydoc.conf")
cli.cli()

# Open results in browser
#print os.getcwd()
apidocsPath = os.path.abspath("../../wsgidav-dev-wiki/apidocs")
logUrl = os.path.abspath("../../wsgidav-dev-wiki/apidocs/epydoc-log.html")

webbrowser.open(os.path.join(apidocsPath, "epydoc-log.html"))
webbrowser.open(os.path.join(apidocsPath, "..", "DEVELOPERS.html"))
webbrowser.open(os.path.join(apidocsPath, "index.html"))

#from subprocess import check_call
#check_call(["epydoc.py", 
#            "-v",
#            "--debug",
#            "--config=tools/epydoc.conf",
#            "wsgidav"
#            ]) 
