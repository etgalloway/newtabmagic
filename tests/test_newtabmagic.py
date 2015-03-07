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
from IPython.core.error import UsageError
import newtabmagic

if sys.version_info.major == 2:
    from StringIO import StringIO
else:
    from io import StringIO

if sys.version_info >= (3, 3):
    from unittest.mock import patch
else:
    from mock import patch

if not IPython.get_ipython():
    from IPython.testing import globalipapp
    globalipapp.start_ipython()


@contextlib.contextmanager
def server_running(newtab):
    newtab.newtab('--server start')
    try:
        yield
    finally:
        newtab.newtab('--server stop')


def _get_newtabmagic(browser='firefox', port=None):
    ip = IPython.get_ipython()
    ip.reset()
    newtab = newtabmagic.NewTabMagics(ip)
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


def _newtabmagic_message(newtab, arg):
    with patch('sys.stdout', StringIO()) as out:
        newtab.newtab(arg)
        msg = out.getvalue()
    return msg


def _newtabmagic_UsageError(newtab, args):
    """Return UsageError raised by newtabmagic command, or None if none."""
    try:
        newtab.newtab(args)
    except UsageError as e:
        error = e
    else:
        error = None
    return error


def _open_new_tab(newtab, args):
    with patch('sys.stdout', StringIO()) as out:
        with patch('subprocess.Popen') as mock_call:
            newtab.newtab(args)
        msg = out.getvalue()
    return msg, mock_call


def _newtabmagic_object_page_name(obj):
    """Return path part of help url not including extension."""
    newtab = _get_newtabmagic()
    newtab.shell.push({'obj': obj})
    with patch('subprocess.Popen') as mock_call:
        newtab.newtab('obj')
    call_args = mock_call.call_args[0][0]
    url = call_args[1]
    return url.split('/')[-1][:-5]


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
        result = _newtabmagic_message(newtab, '--port 8880')

    expected = 'Server already running. Port number not changed\n'
    nose.tools.assert_equals(result, expected)
    result = newtab.base_url()
    expected = root_original
    nose.tools.assert_equals(result, expected)


def test_server_start_stop():

    newtab = _get_newtabmagic()
    url = newtab.base_url()

    # Start server
    result = _newtabmagic_message(newtab, '--server start')

    expected = ("Starting job # ? in a separate thread.\n"
                "Server running at {}\n".format(url))
    head, tail = expected.split('?')
    nose.tools.assert_true(result.startswith(head))
    nose.tools.assert_true(result.endswith(tail))

    # Stop server
    result = _newtabmagic_message(newtab, '--server stop')

    expected = 'Server process is terminated.\n'
    nose.tools.assert_equal(result, expected)


def test_server_stop_not_started():

    newtab = _get_newtabmagic()

    result = _newtabmagic_message(newtab, '--server stop')

    expected = 'Server not started.\n'
    nose.tools.assert_equals(result, expected)


def test_server_already_started():

    newtab = _get_newtabmagic()

    with server_running(newtab):
        result = _newtabmagic_message(newtab, '--server start')

    expected = 'Server already started\n' + \
        'Server running at {}\n'.format(newtab.base_url())
    nose.tools.assert_equals(result, expected)


def test_server_already_stopped():

    newtab = _get_newtabmagic()

    newtab.newtab('--server start')
    newtab.newtab('--server stop')

    result = _newtabmagic_message(newtab, '--server stop')

    expected = 'Server process is already stopped.\n'
    nose.tools.assert_equals(result, expected)


def test_server_process_read():

    newtab = _get_newtabmagic()

    # Server not running
    result = _newtabmagic_message(newtab, '--server read')

    expected = 'Server stdout: \nServer stderr: \n'
    nose.tools.assert_equals(result, expected)

    # Server running
    with server_running(newtab):
        time.sleep(1.0)
        result = _newtabmagic_message(newtab, '--server read')

    expected = 'Server stdout: \nServer stderr: \n'
    nose.tools.assert_equals(result, expected)

    # Server stopped
    result = _newtabmagic_message(newtab, '--server read')

    expected = 'Server stdout: \nServer stderr: \n'
    nose.tools.assert_equals(result, expected)


def test_show():

    newtab = _get_newtabmagic(browser='firefox', port=8880)

    # Server not running
    result = _newtabmagic_message(newtab, '--show')

    expected = ['browser: firefox',
                'server running: False',
                'server port: 8880',
                'server root url: http://127.0.0.1:8880/',
                '']
    nose.tools.assert_equals(result.split('\n'), expected)

    # Server running
    with server_running(newtab):
        result = _newtabmagic_message(newtab, '--show')

    expected = ['browser: firefox',
                'server poll: None',
                'server running: True',
                'server port: 8880',
                'server root url: http://127.0.0.1:8880/',
                '']
    diff = [line for line in result.split('\n') if line not in expected]
    nose.tools.assert_equals(len(diff), 1)
    assert diff[0].startswith('server pid: ')


def test_newtab_name_argument():
    # Test for a single name argument

    newtab = _get_newtabmagic()
    url = newtab.base_url()

    output, mock_call = _open_new_tab(newtab, 'sys')

    nose.tools.assert_equals(output, '')

    args = [newtab.browser, url + 'sys.html']
    mock_call.assert_called_once_with(args)


def test_newtab_name_arguments():
    # Test for multiple name arguments

    newtab = _get_newtabmagic()
    url = newtab.base_url()

    name_arguments = 'sys os zip'
    output, mock_call = _open_new_tab(newtab, name_arguments)

    nose.tools.assert_equals(output, '')

    args = [newtab.browser,
            url + 'sys.html',
            url + 'os.html',
            url + 'zip.html']
    mock_call.assert_called_once_with(args)


def test_name_argument_browser_not_initialized():
    # Exception thrown if browser not initialized

    newtab = _get_newtabmagic(browser=None)
    exception = _newtabmagic_UsageError(newtab, 'sys')
    expected = ('Browser not initialized\n',)
    nose.tools.assert_equals(exception.args, expected)


def test_name_argument_browser_does_not_exist():
    # Exception thrown if browser does not exist

    newtab = _get_newtabmagic()
    newtab.newtab('--browser nonexistent')
    exception = _newtabmagic_UsageError(newtab, 'sys')
    msg = "the command 'nonexistent {}sys.html' raised an OSError\n"
    msg = msg.format(newtab.base_url())
    expected = (msg,)
    nose.tools.assert_equals(expected, exception.args)


def test_name_argument_path_not_object_in_user_namespace():
    # Name argument does not refer to an object in the user name space.

    newtab = _get_newtabmagic()
    assert 'cmath' not in newtab.shell.user_ns
    msg, mock_call = _open_new_tab(newtab, 'cmath')
    args = [newtab.browser, newtab.base_url() + 'cmath.html']
    mock_call.assert_called_once_with(args)


def test_name_argument_path_object_nonexistent_attribute():
    class C(object):
        pass
    newtab = _get_newtabmagic()
    newtab.shell.push({'c': C()})
    assert 'c' in newtab.shell.user_ns
    msg, mock_call = _open_new_tab(newtab, 'c.non_existent_attribute')
    nose.tools.assert_equals(mock_call.call_count, 0)


def test_name_argument_path_nonexistent():
    # Error message is printed; new tab command is not invoked.

    newtab = _get_newtabmagic()

    name_arg = 'does.not.exist'

    msg, mock_call = _open_new_tab(newtab, name_arg)

    # Error message is printed
    expected = 'Documentation not found: does.not.exist\n'
    nose.tools.assert_equals(msg, expected)

    # New tab not opened
    nose.tools.assert_equals(mock_call.call_count, 0)


def test_name_argument_object_module():
    # Object is a module.
    obj = sys
    assert type(obj).__name__ == 'module'

    expected = 'sys'
    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


class C1(object):
    pass


def test_name_argument_object_class():
    # Object is a class.

    obj = C1
    assert inspect.isclass(obj)
    expected = 'tests.test_newtabmagic.C1'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


def test_name_argument_object_class_instance():
    # Object is an instance of a class.
    obj = C1()

    expected = 'tests.test_newtabmagic.C1'
    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


def test_name_argument_object_builtin_function():
    # Type of object is 'builtin_function_or_method'.
    # Object is a function.
    obj = len
    assert type(obj).__name__ == 'builtin_function_or_method'
    assert 'built-in function' in repr(obj)

    expected = 'len'
    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


def test_name_argument_object_builtin_self_not_class():
    # Object type is 'builtin_function_or_method'.
    # Object is a method.
    # Object __self__ attribute is not a class.
    obj = [1, 2, 3].append
    assert type(obj).__name__ == 'builtin_function_or_method'
    assert 'built-in method' in repr(obj)
    assert not inspect.isclass(obj.__self__)

    expected = 'list.append'
    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


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

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


def f1():
    pass


def test_name_argument_object_function():
    # Object is a function
    obj = f1
    assert type(obj).__name__ == 'function'

    expected = 'tests.test_newtabmagic.f1'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


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

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


def test_name_argument_object_method_descriptor():
    # Object is a method descriptor with an __objclass__ attribute

    obj = str.split
    assert type(obj).__name__ == 'method_descriptor'
    assert hasattr(obj, '__objclass__')

    expected = 'str.split'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


def test_name_argument_object_member_descriptor():
    # Object is member descriptor with an __objclass__ attribute

    import datetime
    obj = datetime.timedelta.days
    assert type(obj).__name__ == 'member_descriptor'
    assert hasattr(obj, '__objclass__')

    expected = 'datetime.timedelta.days'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


def test_name_argument_object_wrapper_descriptor():
    # Object is a wrapper descriptor with an __objclass__ attribute.
    obj = int.__add__
    assert type(obj).__name__ == 'wrapper_descriptor'
    assert hasattr(obj, '__objclass__')

    expected = 'int.__add__'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


def test_name_argument_object_method_wrapper():
    # Test object of type 'method-wrapper'.
    # Type 'method-wrapper' only defined in CPython.

    obj = [].__add__
    assert type(obj).__name__ == 'method-wrapper'

    expected = 'list.__add__'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


class C3(object):
    def f(self):
        """method"""


def test_name_argument_object_method_py2_unbound():
    # In Python 2, object is an unbound method.
    # In Python 3, object is a function.
    # Test not needed for coverage in Python 3.

    obj = C3.f
    assert type(obj).__name__ == 'instancemethod' and \
        'unbound' in repr(obj) or sys.version_info[0] > 2
    assert type(obj).__name__ == 'function' or sys.version_info[0] == 2

    expected = 'tests.test_newtabmagic.C3.f'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


class C4(object):
    def method(self):
        pass


def test_name_argument_object_instance_method():
    # Object is an instance method.

    obj = C4().method
    assert type(obj).__name__ in ['method', 'instancemethod']
    assert not inspect.isclass(obj.__self__)

    expected = 'tests.test_newtabmagic.C4.method'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


class C5(object):
    @classmethod
    def m(cls):
        """method decorated by @classmethod"""


def test_name_argument_object_classmethod():
    # Name argument object is a 'class method'.

    obj = C5.m

    # Type of object is 'instancemethod' in Python 2
    assert type(obj).__name__ == 'instancemethod' or sys.version_info[0] != 2

    # Type of object is 'method' in Python 3+.
    assert type(obj).__name__ == 'method' or sys.version_info[0] == 2

    # The '__self__' attribute is a class.
    assert inspect.isclass(obj.__self__)

    # Object is not an instance of 'classmethod'.
    assert not isinstance(obj, classmethod)

    expected = 'tests.test_newtabmagic.C5.m'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


class C6(object):
    def __init__(self):
        self._x = 0

    @property
    def x(self):
        return self._x


def test_name_argument_object_property():
    # Object is a property with a fget attribute.
    # Python 2 does not support introspection for properties.

    obj = C6.x
    assert type(obj).__name__ == 'property'
    assert hasattr(obj, 'fget')

    if sys.version_info.major == 3:
        expected = 'tests.test_newtabmagic.C6.x'
    else:
        expected = 'property'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


class C7(object):
    class N(object):
        pass


def test_name_argument_object_nested_class_instance():
    # Object is an instance of a nested class.
    # Introspection fails for nested classes in Python 2.

    if sys.version_info[0] == 2:
        # Incorrect name attribute for nested classes in Python 2.
        # See http://bugs.python.org/msg166775
        assert repr(C7.N) == "<class 'tests.test_newtabmagic.N'>"
    else:
        assert repr(C7.N) == "<class 'tests.test_newtabmagic.C7.N'>"

    obj = C7().N()

    if sys.version_info[0] == 2:
        # Introspection fails for Python 2.
        expected = 'tests.test_newtabmagic.N'
    else:
        expected = 'tests.test_newtabmagic.C7.N'

    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


class C8(object):
    class N(object):
        def method(self):
            pass


def test_name_argument_object_nested_class_method():
    # Name argument object is a nested class method.
    # Introspection fails for nested class methods in Python 2.

    obj = C8().N().method
    assert inspect.ismethod(obj)
    if sys.version_info[0] == 2:
        expected = 'tests.test_newtabmagic.N.method'
    else:
        expected = 'tests.test_newtabmagic.C8.N.method'
    nose.tools.assert_equals(_newtabmagic_object_page_name(obj), expected)


def gf():
    """generator function"""
    yield


def test_name_argument_object_generator():
    # Name argument object is a generator.
    # Introspection not supported for generators prior to Python 3.5.

    obj = gf()
    assert type(obj).__name__ == 'generator'

    newtab = _get_newtabmagic()
    newtab.shell.push({'obj': obj})
    result, mock_call = _open_new_tab(newtab, 'obj')

    expected = 'Documentation not found: obj\n'
    nose.tools.assert_equals(result, expected)


def test_ServerProcess_port():

    process = newtabmagic.ServerProcess()
    p, q = 8880, 9999
    process.port = p
    assert process.port == p
    process.port = q
    assert process.port == q
