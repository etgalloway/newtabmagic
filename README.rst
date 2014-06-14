newtabmagic
===========

A magic for opening pydoc help pages in new browser tabs.

Installation
------------

To install:

.. code:: python

    In [1]: %install_ext https://raw.github.com/etgalloway/newtabmagic/master/newtabmagic.py

Startup
-------

To load the extension:

.. code:: python

    In [1]: %load_ext newtabmagic

To specify the browser by command name:

.. code:: python

    In [2]: %newtab --browser firefox

To specify the browser by path:

.. code:: python

    In [2]: %newtab --browser C:/Program Files (x86)/Mozilla Firefox/firefox.exe

To set the web server port:

.. code:: python

    In [3]: %newtab --port 8889

To start the web server:

.. code:: python

    In [4]: %newtab --server start
    Starting job # 0 in a separate thread.
    Server running at http://127.0.0.1:8889/

Startup Scripts
---------------

Sample startup scripts have been provided.

The sample Python script:

.. code:: python

    $ cat start_newtabmagic.py
    ip = get_ipython()
    ip.run_cell('%load_ext newtabmagic')
    ip.run_cell('%newtab --port 8889')
    ip.run_cell('%newtab --browser firefox')
    ip.run_cell('%newtab --server start')

The sample IPython script:

.. code:: python

    $ cat start_newtabmagic.ipy
    %load_ext newtabmagic
    %newtab --port 8889
    %newtab --browser firefox
    %newtab --server start

To start :code:`newtabmagic` from the command line, pass the name of the
startup script as an argument:

.. code::

    $ python -m IPython start_newtabmagic.ipy -i

To start :code:`newtabmagic` from within IPython, use :code:`%run` magic:

.. code::

    In [1]: %run start_newtabmagic.ipy
    Starting job # 0 in a separate thread.
    Server running at http://127.0.0.1:8889/

Alternatively, to import the python startup script, use :code:`import`:

.. code::

    In [1]: import start_newtabmagic
    Starting job # 0 in a separate thread.
    Server running at http://127.0.0.1:8889/

Opening Help Pages
------------------

Help pages can opened by providing a dotted path:

.. code:: python

    In [1]: %newtab IPython.core.debugger

Or by providing the name of an object:

.. code:: python

    In [1]: import IPython
    In [2]: debugger = IPython.core.debugger
    In [3]: %newtab debugger

To get help on an object attribute:

.. code:: python

    In [4]: %newtab debugger.Tracer

Shutdown
--------

Shutting down IPython stops the web server.

To stop the web server without shutting down IPython:

.. code:: python

    In [5]: %newtab --server stop
    Server process is terminated.
