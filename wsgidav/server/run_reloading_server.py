# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Wrapper for ``run_server``, that restarts the server when source code is 
modified.
"""
import os
import sys
from subprocess import Popen 

def run():
    args = sys.argv[1:]
    if not "--reload" in args:
        args.append("--reload")

    print "run_reloading_server", args 

    try:
        serverpath = os.path.join(os.path.dirname(__file__), "run_server.py")
        while True:
            p = Popen(["python", serverpath] + args, 
#                      stdin=sys.stdin, 
#                      stdout=subprocess.PIPE, 
#                      stderr=subprocess.PIPE, 
    #                  preexec_fn, close_fds, shell, cwd, env, universal_newlines, startupinfo, creationflags
                      )
            sys.stdout = p.stdout
            sys.stderr = p.stderr
            p.wait()
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            
            if p.returncode == 3:
                print "run_server returned 3: restarting..."
            else:
                print "run_server returned %s: terminating." % p.returncode
                break
    except Exception, e:
        raise e
    
    
if __name__ == "__main__":
    run()
