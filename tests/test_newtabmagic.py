'''
Tests for newtabmagic

To run tests:

    nosetests test_newtabmagic.py

To skip tests that fail under Python 3.2:

    nosetests test_newtabmagic.py -a '!py32failure'

'''
# pylint: disable=C0111, C0321, R0903
import contextlib
import nose
import sys

import IPython
import newtabmagic

from IPython.testing.decorators import skipif
from nose.plugins.attrib import attr

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


def get_newtabmagic(new_tabs_enabled=False, browser=None, port=None):
    ip = IPython.get_ipython()
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
            newtab = get_newtabmagic()
            newtab.newtab('--browser ' + browser_arg)
            result = newtab.browser
            expected = path
            nose.tools.assert_equals(result, expected)


def test_set_port():
    newtab = get_newtabmagic(browser='firefox')

    root_original = newtab.base_url()
    newtab.newtab('--port 9999')
    result = newtab.base_url()
    expected = 'http://127.0.0.1:9999/'
    assert result != root_original
    nose.tools.assert_equals(result, expected)


def test_set_port_server_running():
    # Setting the port number should fail if the server is running

    newtab = get_newtabmagic(browser='firefox', port=9999)
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


def test_set_content_type():

    newtab = get_newtabmagic(browser='firefox')

    # default is 'html'
    with stdout_redirected() as out:
        newtab.newtab('--show')
    output = out.getvalue()
    assert 'content-type: html' in output

    # switch to 'text'
    with stdout_redirected() as out:
        newtab.newtab('--content-type text')
        newtab.newtab('--show')
    output = out.getvalue()
    assert 'content-type: text' in output

    # switch to 'html'
    with stdout_redirected() as out:
        newtab.newtab('--content-type html')
        newtab.newtab('--show')
    output = out.getvalue()
    assert 'content-type: html' in output

    # invalid content type
    nose.tools.assert_raises(
        IPython.core.error.UsageError,
        newtab.newtab, '--content-type invalid')


def test_server_start_stop():

    newtab = get_newtabmagic()
    url = newtab.base_url()

    # Start server
    with stdout_redirected() as out:
        newtab.newtab('--server start')

    result = out.getvalue()
    expected = ("Starting job # ? in a separate thread.\n"
       "Server running at {}\n".format(url))
    n = expected.index("?")
    nose.tools.assert_equal(result[:n], expected[:n])
    nose.tools.assert_equal(result[n+1:], expected[n+1:])

    # Stop server
    with stdout_redirected() as out:
        newtab.newtab('--server stop')

    result = out.getvalue()
    expected = 'Server process is terminated.\n'
    nose.tools.assert_equal(result, expected)


def test_server_stop_not_started():

    newtab = get_newtabmagic()

    with stdout_redirected() as out:
        newtab.newtab('--server stop')

    result = out.getvalue()
    expected = 'Server not started.\n'
    nose.tools.assert_equals(result, expected)


def test_server_already_started():

    newtab = get_newtabmagic()

    with server_running(newtab):
        with stdout_redirected() as out:
            newtab.newtab('--server start')

    expected = 'Server already started\n' + \
        'Server running at {}\n'.format(newtab.base_url())
    result = out.getvalue()
    nose.tools.assert_equals(result, expected)


def test_show():

    newtab = get_newtabmagic(browser='firefox', port=8888)

    # Server not running
    with stdout_redirected() as out:
        newtab.newtab('--show')

    result = out.getvalue()
    expected = "\n".join(['browser: firefox',
                'content-type: html',
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
                'content-type: html',
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
    # test for a single name argument

    browser = 'firefox'
    newtab = get_newtabmagic(browser=browser)
    url = newtab.base_url()

    with stdout_redirected() as out:
        newtab.newtab('sys') # name argument

    output = out.getvalue()
    nose.tools.assert_equals(output, '')

    result = newtab.command_lines
    expected = [[browser, url + 'sys.html']]
    nose.tools.assert_equals(result, expected)


def test_newtab_name_arguments():
    #test for multiple name arguments

    browser = 'firefox'
    newtab = get_newtabmagic(browser=browser)
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

    newtab = get_newtabmagic(browser='firefox')

    with stdout_redirected() as out:
        newtab.newtab('does.not.exist')

    result = out.getvalue()
    expected = 'Documentation not found: does.not.exist\n'
    nose.tools.assert_equals(result, expected)


def test_name_argument_browser_not_initialized():
    # Exception thrown if browser not initialized

    newtab = get_newtabmagic()

    try:
        newtab.newtab('sys')
    except IPython.core.error.UsageError as error:
        result = error.args

    expected = ('Browser not initialized\n',)
    nose.tools.assert_equals(result, expected)


def test_name_argument_nonexistent_browser():
    # Exception thrown if browser does not exist

    newtab = get_newtabmagic(new_tabs_enabled=True)
    newtab.newtab('--browser nonexistent')

    nose.tools.assert_raises(
        IPython.core.error.UsageError,
        newtab.newtab, 'sys')


def test_name_argument_content_type():

    browser = 'firefox'
    newtab = get_newtabmagic(browser=browser)
    url = newtab.base_url()

    newtab.newtab('--content-type html')
    newtab.newtab('sys')
    result = newtab.command_lines
    expected = [[browser, url + 'sys.html']]
    assert result == expected

    newtab.newtab('--content-type text')
    newtab.newtab('sys')
    result = newtab.command_lines
    expected = [[browser, url + 'sys.txt']]
    assert result == expected


def _url_name(newtab):
    """Return name part of url."""
    url = newtab.command_lines[0][1]
    path = urlparse(url).path
    # drop leading '/' and trailing extension
    if path.endswith('.html'):
        return path[1:-5]
    elif path.endswith('.txt'):
        return path[1:-4]


def test_name_argument_find_pydoc_url():
    # Tests to make sure that pydoc urls are
    # found for name strings.

    newtab = get_newtabmagic(browser='firefox')

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


def test_fully_qualified_name_module():
    # object is a module
    obj = sys
    result = newtabmagic.fully_qualified_name(obj)
    expected = 'sys'
    nose.tools.assert_equals(result, expected)


def test_fully_qualified_name_module_unavailable():
    # name of module in which object is defined is not available
    result = newtabmagic.fully_qualified_name(''.split)
    expected = 'str.split'
    nose.tools.assert_equals(result, expected)


def test_fully_qualified_name_builtin_module():
    # object is defined in the 'builtin' module
    obj = len
    result = newtabmagic.fully_qualified_name(obj)
    expected = 'len'
    nose.tools.assert_equals(result, expected)


def test_fully_qualified_name_not_builtin_module():
    # object is defined in a module other than 'builtin'
    obj = sys.settrace
    result = newtabmagic.fully_qualified_name(obj)
    expected = 'sys.settrace'
    nose.tools.assert_equals(result, expected)


@attr('py32failure')
def test_full_name_decorated_function():
    # In Python 3.3, object has an undecorated.__qualname__ attribute
    # In Python 2.7, object has an im_class attribute
    obj = newtabmagic.NewTabMagics.newtab
    result = newtabmagic.fully_qualified_name(obj)
    expected = 'newtabmagic.NewTabMagics.newtab'
    nose.tools.assert_equals(result, expected)


def test_fully_qualied_name_qualname_attribute():
    # In Python 3.3, object has __qualname__ attribute
    # In Python 3.2, object has __name__ attribute
    # In Python 2.7, object has __name__ attribute
    obj = sys.settrace
    result = newtabmagic.fully_qualified_name(obj)
    expected = 'sys.settrace'
    nose.tools.assert_equals(result, expected)


@skipif(sys.version_info[:2] != (2, 7))
def test_fully_qualified_name_objclass_attribute():
    # In Python 2.7, object has __objclass__ attribute
    obj = str.split
    result = newtabmagic.fully_qualified_name(obj)
    assert result == 'str.split'


@skipif(sys.version_info[:2] != (2, 7))
def test_fully_qualified_name_self_attribute():
    # In Python 2.7, object has __self__ attribute
    obj = ''.split
    result = newtabmagic.fully_qualified_name(obj)
    assert result == 'str.split'


def test_fully_qualified_name_type():
    # Object type has a __name__ attribute
    obj = 0
    result = newtabmagic.fully_qualified_name(obj)
    expected = 'int'
    assert result == expected
