"""
===========
NewTabmagic
===========

Magics for opening new browser tabs.

============
Sample Usage
============

    Start magic:

        In [1]: %load_ext newtabmagic

        In [2]: %newtab --browser firefox

        In [3]: %newtab --port 8889

        In [4]: %newtab --server start
        Starting job # 0 in a separate thread.
        Server running at http://127.0.0.1:8889/

    Open help pages in new browser tabs:

        In [5]: %newtab IPython.core.debugger.Tracer

        In [6]: import IPython
        In [7]: Tracer = IPython.core.debugger.Tracer()
        In [8]: %newtab Tracer

    Show state:

        In [9]: # random \
        ...: %newtab --show
        browser: firefox
        content-type: html
        server pid: 3096
        server poll: None
        server running: True
        server port: 8889
        server root url: http://127.0.0.1:8889/

    Stop server:

        In [10]: %newtab --server stop
        Server process is terminated.

    Note: shutting down IPython stops the server.

"""
from __future__ import print_function

import inspect
import os
import pydoc
import sys
import subprocess
import time
import tornado.ioloop
import tornado.web


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
        self._content_type = 'html'
        self._content_types = ['html', 'text']
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
        help='Set port used by the newtabmagic server.'
    )
    @argument(
        '--server',
        help='Control the newtabmagic server.',
        choices=['stop', 'start']
    )
    @argument(
        '--show',
        help='Show state of magic.',
        action='store_true'
    )
    @argument(
        '--content-type',
        choices=['text', 'html'],
        help='Set content type of files opened in new tabs.'
    )
    def newtab(self, line):
        """Line magic for opening new browser tabs."""

        args = parse_argstring(self.newtab, line)

        if args.port:
            self._server.port = args.port

        if args.server:
            if args.server == 'start':
                self._server.start()
            elif args.server == 'stop':
                self._server.stop()

        if args.browser:
            self.browser = args.browser

        if args.content_type:
            self._content_type = args.content_type

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
        obj = self._get_object(path)
        if obj:
            page_name = fully_qualified_name(obj)
        else:
            page_name = None
        return page_name

    def _get_object(self, path):
        """Return object, or None if the object does not exist."""
        parts = [part for part in path.split('.') if part]
        if parts[0] in self.shell.user_ns:
            obj = self.shell.user_ns[parts[0]]
            if parts[1:]:
                obj = _getattr_path(obj, parts[1:])
        else:
            obj = pydoc.locate(path)
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
    def browser(self, browser_args):
        """Set browser name."""
        browser_name = ' '.join(browser_args)
        self._browser = browser_name.strip('"\'')

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
        msg += 'content-type: {}\n'.format(self._content_type)
        print(msg, end='')
        self._server.show()

    def base_url(self):
        """Base Url for newtabmagic server."""
        return self._server.url()

    def _pydoc_url(self, page):
        """Return url for pydoc help page."""
        root = self._server.url()
        if self._content_type == 'html':
            url = root + page + '.html'
        else:
            url = root + page + '.txt'
        return url

class ServerProcess(object):
    """Class for the newtabmagic server process."""

    def __init__(self):
        self._process = None
        self._port = 8888

    def start(self):
        """Start server if not previously started."""
        msg = ''
        if not self.running():
            self._process = start_server_background(self._port)
        else:
            msg = 'Server already started\n'
        msg += 'Server running at {}'.format(self.url())
        print(msg)

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


def fully_qualified_name(obj):
    """Returns fully qualified name, including module name, except for the
    built-in module."""

    builtins = ['builtins', '__builtin__']

    if inspect.ismodule(obj):
        name = obj.__name__
    else:
        module_name = get_module_name(obj)
        if not module_name or module_name in builtins:
            name = _qualname(obj, module_name)
        else:
            name = module_name + '.' + _qualname(obj, module_name)
    return name


def _qualname(obj, module_name):
    """Qualified name not including module name."""

    if sys.version_info >= (3, 3):
        return _qualname33(obj)
    elif sys.version_info >= (3, 0):
        return _qualname32(obj)
    else:
        return _qualname27(obj, module_name)


def _qualname33(obj):
    """Qualified name, not including module name, for Python 3.3+."""
    try:
        return obj.undecorated.__qualname__
    except AttributeError:
        try:
            return obj.__qualname__
        except AttributeError:
            return type(obj).__name__


def _qualname32(obj):
    """Qualified name, not including module name, for Python 3.0-3.2."""
    try:
        return obj.__objclass__.__name__ + "." + obj.__name__
    except AttributeError:
        try:
            if inspect.ismodule(obj.__self__):
                return obj.__name__
            else:
                return obj.__self__.__class__.__name__ + "." + obj.__name__
        except AttributeError:
            try:
                return obj.__name__
            except AttributeError:
                return type(obj).__name__

def _qualname27(obj, module_name):
    """Qualified name, not including module name, Python 2.7."""
    try:
        return obj.__objclass__.__name__ + "." + obj.__name__
    except AttributeError:
        try:
            attr = obj.__name__
            # loop through base classes looking for class where
            # attr is defined.
            for base_class in obj.im_class.mro():
                qual_name = base_class.__name__ + '.' + attr
                if pydoc.locate(module_name + '.' + qual_name):
                    return qual_name
        except AttributeError:  # no im_class
            try:
                if obj.__self__ is not None:
                    return obj.__self__.__class__.__name__ + "." + obj.__name__
            except AttributeError: # no __self__
                pass
            try:
                return obj.__name__
            except AttributeError:
                return type(obj).__name__

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


def get_module_name(object_):
    """Return module name of object, or module name of object's class."""
    try:
        name = object_.__module__
    except AttributeError:
        name = object_.__class__.__module__
    return name


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



class HtmlHandler(tornado.web.RequestHandler):
    """Handler for html pages."""
    def get(self):
        page = get_html(self.request.uri)
        self.write(page)


class TextHandler(tornado.web.RequestHandler):
    """Handler for plain text pages."""
    def get(self):
        page = get_text(self.request.uri)
        self.set_header("Content-Type", "text/plain")
        self.write(page)


def get_html(url):
    """Get method for HTML pages."""
    if sys.version_info[0] >= 3:
        page = pydoc._url_handler(url)  # pylint: disable=W0212
    else:
        if url.endswith('.html'):
            page = pydoc_html_help(url[1:-5])
        elif url == '/':
            # index page is not available for Python 2
            page = "Index page not available"
    return page


def get_text(uri):
    """Get method for plain text pages."""
    path = uri[1:-4]  # remove leading '/' and trailing '.txt'
    page = pydoc_text_help(path)
    return page


def pydoc_html_help(path):
    """Returns a pydoc help page in html for the object referred
    to by path.

    Keyword Arguments:
    path -- an object name or a dotted path to an object

    Reference: pydoc.writedoc

    """
    try:
        obj, name = pydoc.resolve(path)
        html_doc = pydoc.html.document(obj, name)
        page = pydoc.html.page(pydoc.describe(obj), html_doc)
    except (ImportError, pydoc.ErrorDuringImport):
        raise tornado.web.HTTPError(404)
    return page


def pydoc_text_help(path):
    """Returns a pydoc help page in plain text for the object
    referred to by path.

    Keyword Arguments:
    path -- an object name or a dotted path to an object
    """
    try:
        if sys.version_info[0] == 2:
            page = pydoc.plain(pydoc.render_doc(path))
        else:
            page = pydoc.render_doc(path, renderer=pydoc.plaintext)
    except (ImportError, pydoc.ErrorDuringImport):
        raise tornado.web.HTTPError(404)
    return page.encode('utf-8')


def start_server(port):
    """Starts the newtab server on the given port."""
    application = tornado.web.Application([
        (r'/', HtmlHandler),
        (r'/[\w\.]*.html', HtmlHandler),
        (r'/[\w\.]*.txt', TextHandler),
    ])
    application.listen(port)

    tornado.ioloop.IOLoop.instance().start()


def start_server_background(port):
    """Start the newtab server server as a background process."""

    # Using script cell magic so that shutting down
    # IPython stops the server process.

    path = repr(os.path.dirname(os.path.realpath(__file__)))
    lines = ('import sys\n'
             'sys.path.append({path})\n'
             'import {module}\n'
             '{module}.start_server({port})')
    cell = lines.format(path=path, module='newtabmagic', port=port)

    line = "python --proc proc --bg"
    ip = get_ipython()
    ip.run_cell_magic("script", line, cell)

    return ip.user_ns['proc']


def load_ipython_extension(ip):
    """Load NewTabMagics extension."""
    ip.register_magics(NewTabMagics)
