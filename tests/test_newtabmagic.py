"""Tests for newtabmagic.

To run tests:

    nosetests

"""
# pylint: disable=C0111, C0321, R0903
import contextlib
import inspect
import nose
import socket
import sys
import time

import IPython
import newtabmagic

from IPython.testing.decorators import skipif

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
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 0
        s.bind(('', port))
        _, port = s.getsockname()
        newtab.newtab('--port ' + str(port))
    return newtab


def _newtab_url_name(newtab):
    """Return name part of url."""
    url = newtab.command_lines[0][1]
    path = urlparse(url).path
    # drop leading '/' and trailing '.html'
    return path[1:-5]


def test_set_browser():

    paths = [
        'chrome',
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
            newtab.newtab('--port 8880')

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


def test_server_process_read():

    newtab = _get_newtabmagic()

    # Server not running
    with stdout_redirected() as out:
        newtab.newtab('--server read')
    result = out.getvalue()
    expected = 'Server stdout: \nServer stderr: \n'
    nose.tools.assert_equals(result, expected)

    # Server running
    with server_running(newtab):
        time.sleep(1.0)
        with stdout_redirected() as out:
            newtab.newtab('--server read')
    result = out.getvalue()
    expected = 'Server stdout: \nServer stderr: \n'
    nose.tools.assert_equals(result, expected)

    # Server stopped
    with stdout_redirected() as out:
        newtab.newtab('--server read')

    result = out.getvalue()
    expected = 'Server stdout: \nServer stderr: \n'
    nose.tools.assert_equals(result, expected)


def test_show():

    newtab = _get_newtabmagic(browser='firefox', port=8880)

    # Server not running
    with stdout_redirected() as out:
        newtab.newtab('--show')

    result = out.getvalue().split('\n')
    expected = ['browser: firefox',
                'server running: False',
                'server port: 8880',
                'server root url: http://127.0.0.1:8880/',
                '']
    nose.tools.assert_equals(result, expected)

    # Server running
    with server_running(newtab):
        with stdout_redirected() as out:
            newtab.newtab('--show')

    expected = ['browser: firefox',
                'server poll: None',
                'server running: True',
                'server port: 8880',
                'server root url: http://127.0.0.1:8880/',
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
        newtab.newtab('sys')  # name argument

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
        newtab.newtab('sys os zip')  # name arguments

    output = out.getvalue()
    nose.tools.assert_equals(output, '')

    result = newtab.command_lines
    expected = [[browser, url + 'sys.html'],
                [browser, url + 'os.html'],
                [browser, url + 'zip.html']]
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


def test_name_argument_browser_does_not_exist():
    # Exception thrown if browser does not exist

    newtab = _get_newtabmagic(new_tabs_enabled=True)
    newtab.newtab('--browser nonexistent')

    nose.tools.assert_raises(
        IPython.core.error.UsageError,
        newtab.newtab, 'sys')


def test_name_argument_path_not_object_in_user_namespace():
    # Name argument does not refer to an object in the user name space.

    newtab = _get_newtabmagic()
    assert 'cmath' not in newtab.shell.user_ns
    newtab.newtab('cmath')
    result = _newtab_url_name(newtab)
    expected = 'cmath'
    nose.tools.assert_equals(expected, result)


def test_name_argument_path_object_nonexistent_attribute():
    class C(object):
        pass
    newtab = _get_newtabmagic()
    newtab.shell.push({'c': C()})
    assert 'c' in newtab.shell.user_ns
    newtab.newtab('c.non_existent_attribute')
    nose.tools.assert_equals(newtab.command_lines, [])


def test_name_argument_path_nonexistent():
    # Error message is printed; new tab command is not invoked.

    newtab = _get_newtabmagic()

    name_arg = 'does.not.exist'
    with stdout_redirected() as out:
        newtab.newtab(name_arg)
    msg = out.getvalue()

    # Error message is printed
    result = msg
    expected = 'Documentation not found: does.not.exist\n'
    nose.tools.assert_equals(result, expected)

    # New tab not opened
    nose.tools.assert_equals(newtab.command_lines, [])


def _newtabmagic_help_page_name(obj):
    """Return path part of help url not including extension."""

    newtab = _get_newtabmagic()
    newtab.shell.push({'obj': obj})
    newtab.newtab('obj')
    path = _newtab_url_name(newtab)
    return path


def test_name_argument_object_module():
    # Object is a module.
    obj = sys
    assert type(obj).__name__ == 'module'

    expected = 'sys'
    page = _newtabmagic_help_page_name(obj)
    nose.tools.assert_equals(page, expected)


class C1(object):
    pass


def test_name_argument_object_class():
    # Object is a class.

    obj = C1
    assert inspect.isclass(obj)
    expected = 'tests.test_newtabmagic.C1'
    page = _newtabmagic_help_page_name(obj)
    nose.tools.assert_equals(page, expected)


def test_name_argument_object_builtin_function():
    # Type of object is 'builtin_function_or_method'.
    # Object is a function.
    obj = len
    assert type(obj).__name__ == 'builtin_function_or_method'
    assert 'built-in function' in repr(obj)

    expected = 'len'
    page = _newtabmagic_help_page_name(obj)
    nose.tools.assert_equals(page, expected)


def test_name_argument_object_builtin_self_not_class():
    # Object type is 'builtin_function_or_method'.
    # Object is a method.
    # Object __self__ attribute is not a class.
    obj = [1, 2, 3].append
    assert type(obj).__name__ == 'builtin_function_or_method'
    assert 'built-in method' in repr(obj)
    assert not inspect.isclass(obj.__self__)

    expected = 'list.append'
    page = _newtabmagic_help_page_name(obj)
    nose.tools.assert_equals(page, expected)


class C2(object):
    pass


def test_name_argument_object_builtin_self_is_class():
    # Object type is 'builtin_function_or_method'.
    # Object is a method.
    # Object __self__ attribute is a class.
    obj = C2.mro
    assert type(obj).__name__ == 'builtin_function_or_method'
    assert 'built-in method' in repr(obj)
    assert inspect.isclass(obj.__self__)

    expected = 'tests.test_newtabmagic.C2.mro'
    page = _newtabmagic_help_page_name(obj)
    nose.tools.assert_equals(page, expected)


def f1():
    pass


def test_name_argument_object_function():
    # Object is a function
    obj = f1
    assert type(obj).__name__ == 'function'

    expected = 'tests.test_newtabmagic.f1'
    page = _newtabmagic_help_page_name(obj)
    nose.tools.assert_equals(page, expected)


def test_name_argument_object_function_wrapped_attribute_py3():
    # Test needed for coverage in Python 3 only.
    # Object has a __wrapped__ attribute (in Python 2 and 3).
    # In Python 3, object type is 'function'.
    # In Python 2.7, object is an 'instancemethod'.
    # In Python 2.7, object has an im_class attribute.

    obj = IPython.core.magics.ScriptMagics.shebang
    assert hasattr(obj, '__wrapped__')
    assert type(obj).__name__ == 'function' or sys.version_info[0] == 2

    expected = 'IPython.core.magics.script.ScriptMagics.shebang'
    page = _newtabmagic_help_page_name(obj)
    nose.tools.assert_equals(page, expected)


def test_ServerProcess_port():

    process = newtabmagic.ServerProcess()
    p, q = 8880, 9999
    process.port = p
    assert process.port == p
    process.port = q
    assert process.port == q
