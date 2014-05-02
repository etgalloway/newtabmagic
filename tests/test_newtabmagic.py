'''
Tests for newtabmagic

To run tests:

    nosetests test_newtabmagic.py

'''
# pylint: disable=C0111, C0321, R0903
import contextlib
import nose
import sys

import IPython
import newtabmagic


if sys.version_info.major == 2:
    from StringIO import StringIO
else:
    from io import StringIO


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
