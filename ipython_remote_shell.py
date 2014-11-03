#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""An interactive python shell that uses remote_api.

Usage:
  %prog [-s HOSTNAME] [-p PATH] [APPID]

If the -s HOSTNAME flag is not specified, the APPID must be specified.
"""

import os
import sys

DIR_PATH = os.path.abspath(os.environ['GAE_SDK_ROOT'])
EXTRA_PATHS = [
    DIR_PATH,
    os.path.join(DIR_PATH, 'lib', 'antlr3'),
    os.path.join(DIR_PATH, 'lib', 'django-0.96'),
    os.path.join(DIR_PATH, 'lib', 'fancy_urllib'),
    os.path.join(DIR_PATH, 'lib', 'ipaddr'),
    os.path.join(DIR_PATH, 'lib', 'jinja2-2.6'),
    os.path.join(DIR_PATH, 'lib', 'protorpc-1.0'),
    os.path.join(DIR_PATH, 'lib', 'PyAMF'),
    os.path.join(DIR_PATH, 'lib', 'markupsafe'),
    os.path.join(DIR_PATH, 'lib', 'webob_0_9'),
    os.path.join(DIR_PATH, 'lib', 'webapp2-2.5.2'),
    os.path.join(DIR_PATH, 'lib', 'yaml', 'lib'),
    os.path.join(DIR_PATH, 'lib', 'simplejson'),
]

#extra_paths = EXTRA_PATHS[:]
# extra_paths.extend(extra_extra_paths)
sys.path = EXTRA_PATHS[:] + sys.path


import atexit
import code
import getpass
import optparse

try:
    import readline
except ImportError:
    readline = None


from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.tools import appengine_rpc


HISTORY_PATH = os.path.expanduser('~/.remote_api_shell_history')
DEFAULT_PATH = '/_ah/remote_api'
BANNER = """App Engine remote_api shell
Python %s
The db, users, urlfetch, and memcache modules are imported.""" % sys.version


def remote_api_shell(auth_func, servername, appid, path, options, rpc_server_factory):
    """Actually run the remote_api_shell."""

    remote_api_stub.ConfigureRemoteApi(appid, path, auth_func,
                                       servername=servername,
                                       save_cookies=True, secure=options.secure,
                                       rpc_server_factory=rpc_server_factory)
    remote_api_stub.MaybeInvokeAuthentication()

    os.environ['SERVER_SOFTWARE'] = 'Development (remote_api_shell)/1.0'
    if not appid:
        appid = os.environ['APPLICATION_ID']
    sys.ps1 = '%s> ' % appid
    try:
        if options.bpython:
            from bpython import cli
            cli.main(args=[], banner=BANNER)
        elif options.ipython:
            import IPython
            # from IPython.config.loader import Config
            # Explicitly pass an empty list as arguments, because otherwise IPython
            # would use sys.argv from this script.
            #cfg = Config()
            #IPython.embed(config=cfg, banner2=BANNER)
            IPython.embed(banner2=BANNER)
        raise ImportError
    except ImportError:
        if readline is not None:
            readline.parse_and_bind('tab: complete')
            atexit.register(lambda: readline.write_history_file(HISTORY_PATH))
            if os.path.exists(HISTORY_PATH):
                readline.read_history_file(HISTORY_PATH)
        code.interact(banner=BANNER, local=globals())


def main(argv):
    # fix paths
    """Parse arguments and run shell."""
    parser = optparse.OptionParser(usage=__doc__)
    parser.add_option('-s', '--server', dest='server',
                      help='The hostname your app is deployed on. '
                           'Defaults to <app_id>.appspot.com.')
    parser.add_option('-p', '--path', dest='path',
                      help='The path on the server to the remote_api handler. '
                           'Defaults to %s.' % DEFAULT_PATH)
    parser.add_option('--secure', dest='secure', action="store_true",
                      default=False, help='Use HTTPS when communicating '
                                          'with the server.')
    parser.add_option('--bpython', action='store_true', dest='bpython',
                      default=False, help='Use BPython.')
    parser.add_option('--ipython', action='store_true', dest='ipython',
                      default=True, help='Use IPython.')
    parser.add_option('--email', dest='email',
                      help='Admin Email')

    (options, args) = parser.parse_args()

    if ((not options.server and not args) or len(args) > 2
            or (options.path and len(args) > 1)):
        parser.print_usage(sys.stderr)
        if len(args) > 2:
            print >> sys.stderr, 'Unexpected arguments: %s' % args[2:]
        elif options.path and len(args) > 1:
            print >> sys.stderr, 'Path specified twice.'
        sys.exit(1)

    servername = options.server
    appid = None
    path = options.path or DEFAULT_PATH
    if args:
        if servername:
            appid = args[0]
        else:
            servername = '%s.appspot.com' % args[0]
        if len(args) == 2:
            path = args[1]

    def auth_func():
        return (options.email or raw_input('Email: '), getpass.getpass('Password: '))

    remote_api_shell(auth_func, servername, appid, path, options,
                     appengine_rpc.HttpRpcServer)


if __name__ == '__main__':
    main(sys.argv)
