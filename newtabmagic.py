"""newtabmagic: IPython CLI for viewing documentation in the browser.
"""
from __future__ import print_function

__version__ = '0.1.0'

import inspect
import operator
import os
import pydoc
import socket
import subprocess
import sys
import time
import webbrowser


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

    @line_magic
    @magic_arguments()
    @argument(
        'names',
        help=("Python paths or names of objects "
              "used to open tabs in the browser."),
        nargs='*'
    )
    @argument(
        '--browser',
        help="Specify browser used to open tabs.",
        nargs='+'
    )
    @argument(
        '--port',
        help='Specify port used by pydoc server.',
        type=int,
    )
    @argument(
        '--server',
        help='Interact with pydoc server process.',
        choices=['stop', 'start', 'read']
    )
    @argument(
        '--show',
        help="Show state.",
        action='store_true'
    )
    def newtab(self, line):
        """View documentation in the browser."""

        args = parse_argstring(self.newtab, line)

        if args.port is not None:
            self._server.port = args.port

        if args.server:
            self._server_interact(args.server)

        if args.browser:
            self.browser = args.browser

        if args.names:
            self._open_new_tabs(args.names)

        if args.show:
            self._show()

    def _open_new_tabs(self, names):
        """Open browser tabs for a list of variable names and paths."""
        for name in names:
            url = self._get_url(name)
            if url:
                self._open_new_tab(url)
            else:
                print('Documentation not found: {}'.format(name))

    def _get_url(self, name):
        """Get pydoc url for name of variable or path."""
        page = self._get_pydoc_page_name(name)
        if page:
            url = self.base_url + page + '.html'
        else:
            url = None
        return url

    def _get_pydoc_page_name(self, path):
        """Return name of pydoc page, or None if path is not valid."""
        obj = _get_user_ns_object(self.shell, path)
        if obj is not None:
            page_name = _get_object_pydoc_page_name(obj)
        else:
            if pydoc.locate(path) is not None:
                page_name = path
            else:
                page_name = None
        return page_name

    def _open_new_tab(self, url):
        """Open a new tab in the browser."""
        if self._browser:
            cmd = [self._browser, url]
            try:
                subprocess.Popen(cmd)
            except OSError:
                msg = "the command '{}' raised an OSError\n"
                msg = msg.format(' '.join(cmd))
                raise UsageError(msg)
        else:
            webbrowser.open_new_tab(url)

    def _show(self):
        """Show state of magic."""
        msg = ''
        msg += 'browser: {}\n'.format(self._browser)
        print(msg, end='')
        self._server.show()

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

    @property
    def base_url(self):
        """Base url for pydoc server."""
        return self._server.url()

    @property
    def browser(self):
        """Name of browser used to open new tabs."""
        return self._browser

    @browser.setter
    def browser(self, args):
        """Set browser by command name or path."""
        path = ' '.join(args).strip('\'\"')
        self._browser = path


class ServerProcess(object):
    """Wrapper for the web server process."""

    def __init__(self):
        self._process = None
        self._port = 0

    def start(self):
        """Start server if not previously started."""
        msg = ''
        if not self.running():
            if self._port == 0:
                self._port = _port_not_in_use()
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


def _get_object_pydoc_page_name(obj):
    """Returns fully qualified name, including module name, except for the
    built-in module."""
    page_name = _fully_qualified_name(obj)
    if page_name is not None:
        if page_name.startswith('builtins.'):
            page_name = page_name[len('builtins.'):]
        elif page_name.startswith('__builtin__.'):
            page_name = page_name[len('__builtin__.'):]
    return page_name


def _fully_qualified_name(obj):
    """Returns fully qualified name, or None if introspection not supported."""
    if sys.version_info >= (3,):
        return _fully_qualified_name_py3(obj)
    else:
        return _fully_qualified_name_py2(obj)


def _fully_qualified_name_py3(obj):
    """Returns fully qualified name for Python 3."""

    if type(obj).__name__ == 'builtin_function_or_method':

        return _fully_qualified_name_builtin_py3(obj)

    elif type(obj).__name__ == 'function':

        return _fully_qualified_name_function_py3(obj)

    elif type(obj).__name__ == 'generator':
        # Introspection not supported for generators prior to Python 3.5.
        return None

    elif type(obj).__name__ in ['member_descriptor',
                                'wrapper_descriptor', 'method_descriptor']:

        return obj.__objclass__.__module__ + '.' + obj.__qualname__

    elif type(obj).__name__ == 'method':

        return _fully_qualified_name_method_py3(obj)

    elif type(obj).__name__ == 'method-wrapper':

        return _fully_qualified_name_py3(obj.__self__) + '.' + obj.__name__

    elif type(obj).__name__ == 'module':

        return obj.__name__

    elif type(obj).__name__ == 'property':

        return obj.fget.__module__ + '.' + obj.fget.__qualname__

    elif inspect.isclass(obj):

        return obj.__module__ + '.' + obj.__qualname__

    return obj.__class__.__module__ + '.' + obj.__class__.__qualname__


def _fully_qualified_name_builtin_py3(obj):
    """Fully qualified name in Python 3 for 'builtin_function_or_method'
    objects.
    """

    if obj.__module__ is not None:
        # built-in functions
        module = obj.__module__
    else:
        # built-in methods
        if inspect.isclass(obj.__self__):
            module = obj.__self__.__module__
        else:
            module = obj.__self__.__class__.__module__

    return module + '.' + obj.__qualname__


def _fully_qualified_name_function_py3(obj):
    """Fully qualified name in Python 3 for 'function' objects.
    """

    if hasattr(obj, "__wrapped__"):
        qualname = obj.__wrapped__.__qualname__
    else:
        qualname = obj.__qualname__

    return obj.__module__ + '.' + qualname


def _fully_qualified_name_method_py3(obj):
    """Fully qualified name in Python 3 for 'method' objects.
    """

    if inspect.isclass(obj.__self__):
        cls = obj.__self__.__qualname__
    else:
        cls = obj.__self__.__class__.__qualname__

    return obj.__self__.__module__ + '.' + cls + '.' + obj.__name__


def _fully_qualified_name_py2(obj):
    """Fully qualified name for Python 2."""

    if type(obj).__name__ == 'builtin_function_or_method':

        return _fully_qualified_name_builtin_py2(obj)

    elif type(obj).__name__ == 'function':

        return obj.__module__ + '.' + obj.__name__

    elif type(obj).__name__ == 'generator':
        # Introspection not supported for generators prior to Python 3.5.
        return None

    elif type(obj).__name__ in ['member_descriptor',
                                'wrapper_descriptor', 'method_descriptor']:

        return (obj.__objclass__.__module__ + '.' +
                obj.__objclass__.__name__ + '.' +
                obj.__name__)

    elif type(obj).__name__ == 'instancemethod':

        return _fully_qualified_name_method_py2(obj)

    elif type(obj).__name__ == 'method-wrapper':

        return _fully_qualified_name_py2(obj.__self__) + '.' + obj.__name__

    elif type(obj).__name__ == 'module':

        return obj.__name__

    elif inspect.isclass(obj):

        return obj.__module__ + '.' + obj.__name__

    return obj.__class__.__module__ + '.' + obj.__class__.__name__


def _fully_qualified_name_builtin_py2(obj):
    """Fully qualified name in Python 2 for 'builtin_function_or_method'
    objects.
    """

    if obj.__self__ is None:
        # built-in functions
        module = obj.__module__
        qualname = obj.__name__
    else:
        # built-in methods
        if inspect.isclass(obj.__self__):
            cls = obj.__self__
        else:
            cls = obj.__self__.__class__
        module = cls.__module__
        qualname = cls.__name__ + '.' + obj.__name__

    return module + '.' + qualname


def _fully_qualified_name_method_py2(obj):
    """Fully qualified name for 'instancemethod' objects in Python 2.
    """

    if obj.__self__ is None:
        # unbound method
        module = obj.im_class.__module__
        cls = obj.im_class.__name__
    else:
        # bound method
        if inspect.isclass(obj.__self__):
            # method decorated with @classmethod
            module = obj.__self__.__module__
            cls = obj.__self__.__name__
        else:
            module = obj.__self__.__class__.__module__
            cls = obj.__self__.__class__.__name__

    return module + '.' + cls + '.' + obj.__func__.__name__


def _get_user_ns_object(shell, path):
    """Get object from the user namespace, given a path containing
    zero or more dots.  Return None if the path is not valid.
    """
    parts = path.split('.', 1)
    name, attr = parts[0], parts[1:]
    if name in shell.user_ns:
        if attr:
            try:
                return _getattr(shell.user_ns[name], attr[0])
            except AttributeError:
                return None
        else:
            return shell.user_ns[name]
    return None


def _getattr(obj, attr):
    """Get a named attribute from an object, where attr is a string
    that may contain dots.
    """
    f = operator.attrgetter(attr)
    return f(obj)


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

    # Monkey-patch input so that input does not raise EOFError when
    # called by pydoc.cli
    def input(_):  # pylint: disable=W0622
        """Monkey-patched version of builtins.input"""
        while 1:
            time.sleep(1.0)

    import builtins
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


def _port_not_in_use():
    """Use the port 0 trick to find a port not in use."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port = 0
    s.bind(('', port))
    _, port = s.getsockname()
    return port


def load_ipython_extension(ip):
    """Load NewTabMagics extension."""
    ip.register_magics(NewTabMagics)
