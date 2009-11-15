# -*- coding: iso-8859-1 -*-
"""
run_reloading_server
====================

:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Wrapper for run_server, that restarts the server when source code is modified.
"""
import sys
from subprocess import call

def run():
    args = sys.argv[1:]
    if not "--reload" in args:
        args.append("--reload")

    print "run_reloading_server", args 

    while 3 == call(["python", "run_server.py"] + args):
        print "run_server returned 3: restarting..."
    
if __name__ == "__main__":
    run()
