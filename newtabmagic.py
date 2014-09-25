"""
===========
NewTabmagic
===========

A magic that provides access to the pydoc web server.

============
Sample Usage
============

    To load and configure newtabmagic:

        In [1]: %load_ext newtabmagic

        In [2]: %newtab --browser firefox

        In [3]: %newtab --port 8880

    To start the pydoc web server:

        In [4]: %newtab --server start
        Starting job # 0 in a separate thread.
        Server running at http://127.0.0.1:8880/

    To open pydoc help pages:

        In [5]: %newtab IPython.core.debugger.Tracer

        In [6]: import IPython
        In [7]: Tracer = IPython.core.debugger.Tracer()
        In [8]: %newtab Tracer

    To show state:

        In [9]: %newtab --show
        browser: firefox
        server pid: 3096
        server poll: None
        server running: True
        server port: 8880
        server root url: http://127.0.0.1:8880/

    To stop the pydoc server:

        In [10]: %newtab --server stop
        Server process is terminated.

    Note: shutting down IPython stops the server.

"""
from __future__ import print_function

__version__ = '0.1'

import inspect
import os
import pydoc
import sys
import subprocess
import time


from IPython import get_ipython
from IPython.core.error import UsageError
from IPython.core.magic import (
    Magics,
    magics_class,
    line_magic)
from IPython.core.magic_arguments import (
    argument,
    magic_arguments,
    parse_argstring)


@magics_class
class NewTabMagics(Magics):
    """Magic class for opening new browser tabs."""

    def __init__(self, shell):
        super(NewTabMagics, self).__init__(shell)
        self._browser = None
        self._server = ServerProcess()
        self.new_tabs_enabled = True
        self._cmds = []

    @line_magic
    @magic_arguments()
    @argument(
        'names',
        help='Variable names and dotted paths, separated by spaces.',
        nargs='*'
    )
    @argument(
        '--browser',
        help='Set name of browser used to open new tabs.',
        nargs='+'
    )
    @argument(
        '--port',
        type=int,
        help='Set port used by the pydoc server.'
    )
    @argument(
        '--server',
        help='Interact with the pydoc server process.',
        choices=['stop', 'start', 'read']
    )
    @argument(
        '--show',
        help='Show state of magic.',
        action='store_true'
    )
    def newtab(self, line):
        """Line magic for opening new browser tabs."""

        args = parse_argstring(self.newtab, line)

        if args.port:
            self._server.port = args.port

        if args.server:
            self._server_interact(args.server)

        if args.browser:
            self.browser = args.browser

        if args.names:
            if self._browser:
                self._open_new_tabs(args.names)
            else:
                msg = "Browser not initialized\n"
                raise UsageError(msg)

        if args.show:
            self._show()

    def _open_new_tabs(self, names):
        """Open browser tabs for a list of variable names and paths."""
        self._cmds = []
        for name in names:
            url, msg = self._get_url(name)
            if not url:
                print(msg)
            else:
                cmd = [self._browser, url]
                self._cmds.append(cmd)
                self._open_new_tab(cmd)

    def _get_url(self, name):
        """Get url associated with name, returning None if not found"""
        return self._get_pydoc_url(name)

    def _get_pydoc_url(self, name):
        """Get pydoc url for name of variable or path."""
        msg = ''
        page = self._get_pydoc_page_name(name)
        if page:
            url = self._pydoc_url(page)
        else:
            url = None
            msg = 'Documentation not found: {}'.format(name)
        return url, msg

    def _get_pydoc_page_name(self, path):
        """Return name of pydoc page, or None if path is not valid."""
        obj = self._get_user_ns_object(path)
        if obj is not None:
            page_name = _fully_qualified_name(obj)
        else:
            obj = pydoc.locate(path)
            if obj is not None:
                page_name = path
            else:
                page_name = None
        return page_name

    def _get_user_ns_object(self, path):
        """Get object associated with path, provided the first
        part of the path is the name of an object in the user
        namespace.  Return None if the object does not exist."""
        parts = [part for part in path.split('.') if part]
        if parts[0] in self.shell.user_ns:
            obj = self.shell.user_ns[parts[0]]
            if parts[1:]:
                obj = _getattr_path(obj, parts[1:])
        else:
            obj = None
        return obj

    @property
    def command_lines(self):
        """Command lines used (most recently) to invoke subproccesses."""
        return self._cmds

    @property
    def browser(self):
        """Name of browser used to open new tabs."""
        return self._browser

    @browser.setter
    def browser(self, args):
        """Set browser by command name or path."""
        path = ' '.join(args).strip('\'\"')
        self._browser = path

    def _open_new_tab(self, cmd):
        """Open a new browser tab by invoking a subprocess."""
        try:
            if self.new_tabs_enabled:
                # chromium browser writes to screen, so redirect
                subprocess.Popen(cmd, stdout=subprocess.PIPE)
        except OSError:
            msg = "Browser named {} failed to open new tab\n".format(
                self._browser)
            raise UsageError(msg)

    def _show(self):
        """Show state of magic."""
        msg = ''
        msg += 'browser: {}\n'.format(self._browser)
        print(msg, end='')
        self._server.show()

    def base_url(self):
        """Base url for pydoc server."""
        return self._server.url()

    def _pydoc_url(self, page):
        """Return url for pydoc help page."""
        return self.base_url() + page + '.html'

    def _server_interact(self, cmd):
        """Interact with the pydoc server process."""
        if cmd == 'start':
            self._server.start()
        elif cmd == 'stop':
            self._server.stop()
        elif cmd == 'read':
            out, err = self._server.read()
            print('Server stdout: {}'.format(out))
            print('Server stderr: {}'.format(err))


class ServerProcess(object):
    """Wrapper for the web server process."""

    def __init__(self):
        self._process = None
        self._port = 8880

    def start(self):
        """Start server if not previously started."""
        msg = ''
        if not self.running():
            self._process = start_server_background(self._port)
        else:
            msg = 'Server already started\n'
        msg += 'Server running at {}'.format(self.url())
        print(msg)

    def read(self):
        """Read stdout and stdout pipes if process is no longer running."""
        if self._process and self._process.poll() is not None:
            ip = get_ipython()
            err = ip.user_ns['error'].read().decode()
            out = ip.user_ns['output'].read().decode()
        else:
            out = ''
            err = ''
        return out, err

    def stop(self):
        """Stop server process."""

        msg = ''
        if self._process:
            _stop_process(self._process, 'Server process')
        else:
            msg += 'Server not started.\n'
        if msg:
            print(msg, end='')

    def running(self):
        """If the server has been started, is it still running?"""
        return self._process is not None and self._process.poll() is None

    def show(self):
        """Show state."""
        msg = ''
        if self._process:
            msg += 'server pid: {}\n'.format(self._process.pid)
            msg += 'server poll: {}\n'.format(self._process.poll())
        msg += 'server running: {}\n'.format(self.running())
        msg += 'server port: {}\n'.format(self._port)
        msg += 'server root url: {}\n'.format(self.url())
        print(msg, end='')

    def url(self):
        """Base url. Includes protocol, host, and port number."""
        proto = 'http'
        ip = '127.0.0.1'
        return '{}://{}:{}/'.format(proto, ip, self._port)

    @property
    def port(self):
        """Port number server listens on."""
        return self._port

    @port.setter
    def port(self, port):
        """Set port number if server is not running."""
        if not self.running():
            self._port = port
        else:
            print('Server already running. Port number not changed')


def _fully_qualified_name(obj):
    """Returns fully qualified name, including module name, except for the
    built-in module."""

    module_name = _get_module_name(obj)

    if inspect.ismodule(obj):
        name = module_name
    else:
        qualname = _qualname(obj)
        if module_name in ['builtins', '__builtin__']:
            name = qualname
        else:
            name = module_name + '.' + qualname
    return name


def _get_module_name(obj):
    """Return module name of object, or module name of object's class."""
    if inspect.ismodule(obj):
        name = obj.__name__
    elif inspect.ismethod(obj):
        try:
            name = obj.im_class.__module__
        except AttributeError:
            name = obj.__self__.__module__
    else:
        try:
            name = obj.__module__
            if name is None:
                name = obj.__self__.__module__
        except AttributeError:
            name = obj.__class__.__module__
    return name


def _qualname(obj):
    """Qualified name not including module name."""
    if sys.version_info >= (3,):
        return _qualname_py3(obj)
    else:
        return _qualname_py2(obj)


def _qualname_py3(obj):
    """Qualified name, not including module name, for Python 3."""

    if hasattr(obj, "undecorated"):
        return obj.undecorated.__qualname__

    if inspect.ismethod(obj):
        return obj.__self__.__class__.__name__ + '.' + obj.__func__.__name__

    if hasattr(obj, '__objclass__'):
        return obj.__objclass__.__name__ + "." + obj.__name__

    try:
        return obj.__qualname__
    except AttributeError:
        pass

    try:
        return obj.__name__
    except AttributeError:
        pass

    return type(obj).__name__


def _qualname_py2(obj):
    """Qualified name, not including module name, for Python 2.7."""
    if inspect.isbuiltin(obj):
        return _qualname_builtin_py2(obj)
    elif hasattr(obj, 'im_class'):
        return obj.im_class.__name__ + '.' + obj.__name__
    elif hasattr(obj, '__objclass__'):
        return obj.__objclass__.__name__ + "." + obj.__name__
    else:
        try:
            return obj.__name__
        except AttributeError:
            return type(obj).__name__


def _qualname_builtin_py2(obj):
    """Qualified name for builtin functions and methods, for Python 2.7."""
    if obj.__self__ is not None:
        # builtin methods
        if hasattr(obj.__self__, '__name__'):
            self_name = obj.__self__.__name__
        else:
            self_name = obj.__self__.__class__.__name__
        return self_name + "." + obj.__name__
    else:
        # builtin function
        return obj.__name__


def _getattr_path(obj, attrs):
    """Get a named attribute from an object, returning None if the
    attribute does not exist.

    Keyword Arguments:
    attrs -- a list of attributes obtained from a path by applying
                String.split('.')
    """

    try:
        for attr in attrs:
            obj = getattr(obj, attr)
    except AttributeError:
        obj = None
    return obj


def _stop_process(p, name):
    """Stop process, by applying terminate and kill."""
    # Based on code in IPython.core.magics.script.ScriptMagics.shebang
    if p.poll() is not None:
        print("{} is already stopped.".format(name))
        return
    p.terminate()
    time.sleep(0.1)
    if p.poll() is not None:
        print("{} is terminated.".format(name))
        return
    p.kill()
    print("{} is killed.".format(name))


def pydoc_cli_monkey_patched(port):
    """In Python 3, run pydoc.cli with builtins.input monkey-patched
    so that pydoc can be run as a process.
    """
    import builtins
    # Monkey-patch input so that input does not raise EOFError when
    # called by pydoc.cli
    def input(_): # pylint: disable=W0622
        """Monkey-patched version of builtins.input"""
        while 1:
            time.sleep(1.0)
    builtins.input = input
    sys.argv += ["-p", port]
    pydoc.cli()


def start_server_background(port):
    """Start the newtab server as a background process."""

    if sys.version_info[0] == 2:
        lines = ('import pydoc\n'
                 'pydoc.serve({port})')
        cell = lines.format(port=port)
    else:
        # The location of newtabmagic (normally $IPYTHONDIR/extensions)
        # needs to be added to sys.path.
        path = repr(os.path.dirname(os.path.realpath(__file__)))
        lines = ('import sys\n'
                 'sys.path.append({path})\n'
                 'import newtabmagic\n'
                 'newtabmagic.pydoc_cli_monkey_patched({port})')
        cell = lines.format(path=path, port=port)

    # Use script cell magic so that shutting down IPython stops
    # the server process.
    line = "python --proc proc --bg --err error --out output"
    ip = get_ipython()
    ip.run_cell_magic("script", line, cell)

    return ip.user_ns['proc']


def load_ipython_extension(ip):
    """Load NewTabMagics extension."""
    ip.register_magics(NewTabMagics)
