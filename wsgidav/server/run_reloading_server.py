# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Wrapper for ``server_cli``, that restarts the server when source code is
modified.
"""
from __future__ import print_function
from subprocess import Popen

import os
import sys


def run():
    args = sys.argv[1:]
    if "--reload" not in args:
        args.append("--reload")

    print("run_reloading_server", args)

    try:
        serverpath = os.path.join(os.path.dirname(__file__), "server_cli.py")
        while True:
            p = Popen(
                ["python", serverpath] + args,
                # stdin=sys.stdin,
                # stdout=subprocess.PIPE,
                # stderr=subprocess.PIPE,
                # preexec_fn, close_fds, shell, cwd, env, universal_newlines, startupinfo,
                # creationflags
            )
            sys.stdout = p.stdout
            sys.stderr = p.stderr
            p.wait()
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            if p.returncode == 3:
                print("server_cli returned 3: restarting...")
            else:
                print("server_cli returned {}: terminating.".format(p.returncode))
                break
    except Exception as e:
        raise e


if __name__ == "__main__":
    run()
