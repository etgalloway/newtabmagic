'''
Tests for newtabmagic

To run tests:

    nosetests

'''
# pylint: disable=C0111, C0321, R0903
import contextlib
import nose
import sys

import IPython
import newtabmagic

from IPython.testing.decorators import skipif
from tornado.testing import AsyncHTTPTestCase

if sys.version_info.major == 2:
    from StringIO import StringIO
    from urlparse import urlparse
else:
    from io import StringIO
    from urllib.parse import urlparse


if not IPython.get_ipython():
    from IPython.testing import globalipapp
    globalipapp.start_ipython()


@contextlib.contextmanager
def stdout_redirected(new_target=None):
    old_target = sys.stdout
    if new_target is None:
        sys.stdout = StringIO()
    else:
        sys.stdout = new_target
    try:
        yield sys.stdout
    finally:
        sys.stdout = old_target


@contextlib.contextmanager
def server_running(newtab):
    newtab.newtab('--server start')
    try:
        yield
    finally:
        newtab.newtab('--server stop')


def _get_newtabmagic(new_tabs_enabled=False, browser='firefox', port=None):
    ip = IPython.get_ipython()
    ip.reset()
    newtab = newtabmagic.NewTabMagics(ip)
    newtab.new_tabs_enabled = new_tabs_enabled
    if browser is not None:
        newtab.newtab('--browser ' + browser)
    if port is not None:
        newtab.newtab('--port ' + str(port))
    return newtab


def test_set_browser():
    paths = ['chrome',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe']

    for path in paths:
        for format_str in ['{}', "'{}'", '"{}"']:
            browser_arg = format_str.format(path)
            newtab = _get_newtabmagic(browser=None)
            newtab.newtab('--browser ' + browser_arg)
            result = newtab.browser
            expected = path
            nose.tools.assert_equals(result, expected)


def test_set_port():
    newtab = _get_newtabmagic()

    root_original = newtab.base_url()
    newtab.newtab('--port 9999')
    result = newtab.base_url()
    expected = 'http://127.0.0.1:9999/'
    assert result != root_original
    nose.tools.assert_equals(result, expected)


def test_set_port_server_running():
    # Setting the port number should fail if the server is running

    newtab = _get_newtabmagic(port=9999)
    root_original = newtab.base_url()
    with server_running(newtab):
        with stdout_redirected() as out:
            newtab.newtab('--port 8888')

    result = out.getvalue()
    expected = 'Server already running. Port number not changed\n'
    nose.tools.assert_equals(result, expected)
    result = newtab.base_url()
    expected = root_original
    nose.tools.assert_equals(result, expected)


def test_server_start_stop():

    newtab = _get_newtabmagic(browser=None)
    url = newtab.base_url()

    # Start server
    with stdout_redirected() as out:
        newtab.newtab('--server start')

    result = out.getvalue()
    expected = ("Starting job # ? in a separate thread.\n"
       "Server running at {}\n".format(url))
    head, tail = expected.split('?')
    nose.tools.assert_true(result.startswith(head))
    nose.tools.assert_true(result.endswith(tail))

    # Stop server
    with stdout_redirected() as out:
        newtab.newtab('--server stop')

    result = out.getvalue()
    expected = 'Server process is terminated.\n'
    nose.tools.assert_equal(result, expected)


def test_server_stop_not_started():

    newtab = _get_newtabmagic(browser=None)

    with stdout_redirected() as out:
        newtab.newtab('--server stop')

    result = out.getvalue()
    expected = 'Server not started.\n'
    nose.tools.assert_equals(result, expected)


def test_server_already_started():

    newtab = _get_newtabmagic(browser=None)

    with server_running(newtab):
        with stdout_redirected() as out:
            newtab.newtab('--server start')

    expected = 'Server already started\n' + \
        'Server running at {}\n'.format(newtab.base_url())
    result = out.getvalue()
    nose.tools.assert_equals(result, expected)


def test_server_already_stopped():

    newtab = _get_newtabmagic(browser=None)

    newtab.newtab('--server start')
    newtab.newtab('--server stop')
    with stdout_redirected() as out:
        newtab.newtab('--server stop')

    expected = 'Server process is already stopped.\n'
    result = out.getvalue()
    nose.tools.assert_equals(result, expected)


def test_show():

    newtab = _get_newtabmagic(browser='firefox', port=8888)

    # Server not running
    with stdout_redirected() as out:
        newtab.newtab('--show')

    result = out.getvalue()
    expected = "\n".join(['browser: firefox',
                'server running: False',
                'server port: 8888',
                'server root url: http://127.0.0.1:8888/',
                ''])
    nose.tools.assert_equals(result, expected)

    # Server running
    with server_running(newtab):
        with stdout_redirected() as out:
            newtab.newtab('--show')

    expected = ['browser: firefox',
                'server poll: None',
                'server running: True',
                'server port: 8888',
                'server root url: http://127.0.0.1:8888/',
                '']
    result = out.getvalue().split('\n')
    diff = [line for line in result if line not in expected]
    nose.tools.assert_equals(len(diff), 1)
    assert diff[0].startswith('server pid: ')


def test_newtab_name_argument():
    # Test for a single name argument

    browser = 'firefox'
    newtab = _get_newtabmagic(browser=browser)
    url = newtab.base_url()

    with stdout_redirected() as out:
        newtab.newtab('sys') # name argument

    output = out.getvalue()
    nose.tools.assert_equals(output, '')

    result = newtab.command_lines
    expected = [[browser, url + 'sys.html']]
    nose.tools.assert_equals(result, expected)


def test_newtab_name_arguments():
    # Test for multiple name arguments

    browser = 'firefox'
    newtab = _get_newtabmagic(browser=browser)
    url = newtab.base_url()

    with stdout_redirected() as out:
        newtab.newtab('sys os zip') # name arguments

    output = out.getvalue()
    nose.tools.assert_equals(output, '')

    result = newtab.command_lines
    expected = [[browser, url + 'sys.html'],
                [browser, url + 'os.html'],
                [browser, url + 'zip.html']]
    nose.tools.assert_equals(result, expected)


def test_name_argument_doc_not_found():

    newtab = _get_newtabmagic()

    with stdout_redirected() as out:
        newtab.newtab('does.not.exist')

    result = out.getvalue()
    expected = 'Documentation not found: does.not.exist\n'
    nose.tools.assert_equals(result, expected)


def test_name_argument_browser_not_initialized():
    # Exception thrown if browser not initialized

    newtab = _get_newtabmagic(browser=None)

    try:
        newtab.newtab('sys')
    except IPython.core.error.UsageError as error:
        result = error.args

    expected = ('Browser not initialized\n',)
    nose.tools.assert_equals(result, expected)


def test_name_argument_nonexistent_browser():
    # Exception thrown if browser does not exist

    newtab = _get_newtabmagic(new_tabs_enabled=True)
    newtab.newtab('--browser nonexistent')

    nose.tools.assert_raises(
        IPython.core.error.UsageError,
        newtab.newtab, 'sys')


def _url_name(newtab):
    """Return name part of url."""
    url = newtab.command_lines[0][1]
    path = urlparse(url).path
    # drop leading '/' and trailing '.html'
    return path[1:-5]


def test_name_argument_dotted_path():
    # Tests of name arguments which are paths not objects.

    newtab = _get_newtabmagic()

    # Name in user name space
    arg = 'pydoc'
    newtab.shell.run_cell('import ' + arg)
    assert arg in newtab.shell.user_ns
    newtab.newtab(arg)
    result = _url_name(newtab)
    expected = arg
    nose.tools.assert_equals(expected, result)

    # Name in user namespace with attribute
    arg = 'pydoc.locate'
    assert 'pydoc' in newtab.shell.user_ns
    newtab.newtab(arg)
    result = _url_name(newtab)
    expected = arg
    nose.tools.assert_equals(expected, result)

    # Name not in user name space
    arg = 'cmath'
    assert arg not in newtab.shell.user_ns
    newtab.newtab(arg)
    result = _url_name(newtab)
    expected = arg
    nose.tools.assert_equals(expected, result)

    # module in user namespace, nonexistent attribute
    arg = 'pydoc.non_existent_attribute'
    assert 'pydoc' in newtab.shell.user_ns
    newtab.newtab(arg)
    nose.tools.assert_equals(newtab.command_lines, [])

    # invalid path
    arg = 'does.not.exist'
    newtab.newtab(arg)
    nose.tools.assert_equals(newtab.command_lines, [])


def test_name_argument_object_module():
    # Object is a module
    newtab = _get_newtabmagic()
    newtab.shell.run_cell('import sys')
    newtab.shell.run_cell('o = sys')
    newtab.newtab('o')
    result = _url_name(newtab)
    expected = 'sys'
    nose.tools.assert_equals(result, expected)


def test_name_argument_object_no_module_attribute():
    # Object does not have a '__module__' attribute
    newtab = _get_newtabmagic()
    newtab.shell.run_cell('f = str.split')
    newtab.newtab('f')
    result = _url_name(newtab)
    expected = 'str.split'
    nose.tools.assert_equals(result, expected)


def test_name_object_builtin_function():
    # Object module attribute is 'builtins' or '__builtin__'
    newtab = _get_newtabmagic()
    newtab.shell.run_cell('f = len')
    newtab.newtab('f')
    result = _url_name(newtab)
    expected = 'len'
    nose.tools.assert_equals(result, expected)


def test_name_argument_object_is_not_builtin():
    # Object is not defined in the builtin module.
    newtab = _get_newtabmagic()
    newtab.shell.run_cell('import sys')
    newtab.shell.run_cell('f=sys.settrace')
    newtab.newtab('f')
    result = _url_name(newtab)
    expected = 'sys.settrace'
    nose.tools.assert_equals(result, expected)


@skipif(sys.version_info[:2] == (3, 2), "Python 3.2 Failure")
def test_name_argument_decorated_object():
    # In Python 3.3, object has an undecorated.__qualname__ attribute
    # In Python 2.7, object has an im_class attribute
    newtab = _get_newtabmagic()
    newtab.shell.run_cell('import newtabmagic')
    newtab.shell.run_cell('f=newtabmagic.NewTabMagics.newtab')
    newtab.newtab('f')
    result = _url_name(newtab)
    expected = 'newtabmagic.NewTabMagics.newtab'
    nose.tools.assert_equals(result, expected)


def test_name_argument_object_objclass_attribute():
    newtab = _get_newtabmagic()
    newtab.shell.run_cell('f = str.split')
    newtab.newtab('f')
    result = _url_name(newtab)
    expected = 'str.split'
    nose.tools.assert_equals(result, expected)


def test_name_argument_object_self_attribute():
    # Test for Python 2.7
    newtab = _get_newtabmagic()
    newtab.shell.run_cell('f = "".split')
    newtab.newtab('f')
    result = _url_name(newtab)
    expected = 'str.split'
    nose.tools.assert_equals(result, expected)


def test_name_argument_object_no_name_attribute():
    # Object does not have a '__name__' attribute.
    newtab = _get_newtabmagic()
    newtab.shell.run_cell('x = 0')
    newtab.newtab('x')
    result = _url_name(newtab)
    expected = 'int'
    nose.tools.assert_equals(result, expected)


def test_name_argument_path_attribute_no_module():
    # Test of path to attribute ('mro') not defined in a module

    newtab = _get_newtabmagic()
    assert 'IPython' not in newtab.shell.user_ns
    newtab.newtab('IPython.core.debugger.Tracer.mro')
    result = _url_name(newtab)
    expected = 'IPython.core.debugger.Tracer.mro'
    nose.tools.assert_equals(result, expected)


@skipif(sys.version_info[:2] == (3, 2), "Python 3.2 Failure")
def test_name_argument_object_attribute_no_module():
    # Test of object attribute ('mro') not defined in a module

    newtab = _get_newtabmagic()
    newtab.shell.run_cell('import newtabmagic')
    newtab.shell.run_cell('f = newtabmagic.NewTabMagics.mro')
    newtab.newtab('f')
    result = _url_name(newtab)
    expected = 'newtabmagic.NewTabMagics.mro'
    nose.tools.assert_equals(result, expected)


def test_name_argument_object_method_wrapper():
    # Test needed for Python 2.7
    # [].__add__ has an __objclass__ attribute
    # In CPython, type([].__add__).__name__ == 'method-wrapper'

    newtab = _get_newtabmagic()
    newtab.shell.run_cell('f = [].__add__')
    newtab.newtab('f')
    result = _url_name(newtab)
    expected = 'list.__add__'
    nose.tools.assert_equals(result, expected)


def test_name_argument_object_instance_method():

    newtab = _get_newtabmagic()
    newtab.shell.run_cell('im=get_ipython')
    newtab.newtab('im')
    result = _url_name(newtab)
    expected = 'IPython.terminal.interactiveshell.TerminalInteractiveShell.get_ipython'
    nose.tools.assert_equals(result, expected)


class WebApplicationTest(AsyncHTTPTestCase):
    def get_app(self):
        return newtabmagic.web_application()

    @skipif(sys.version_info[0] == 2)
    def test_index(self):
        response = self.fetch('/')
        assert b'Pydoc: Index of Modules' in response.body

    @skipif(sys.version_info[0] == 2)
    def test_text(self):
        response = self.fetch('/sys.txt')
        assert b'built-in module sys' in response.body

    @skipif(sys.version_info[0] == 2)
    def test_404(self):
        response = self.fetch('/page_does_not_exist.txt')
        expected = ('<html><title>404: Not Found</title>'
                   '<body>404: Not Found</body></html>')
        assert response.body.decode() == expected
