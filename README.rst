newtabmagic
===========

An IPython magic for viewing pydoc help pages in the browser.

Viewing Pydoc Help Pages
------------------------

Help pages can opened by providing a dotted path:

.. code:: python

    In [1]: %newtab IPython.core.debugger.Tracer

Or by providing the name of an object:

.. code:: python

    In [1]: import IPython
    In [2]: db = IPython.core.debugger
    In [3]: %newtab db.Tracer

Installation
------------

To install :code:`newtabmagic`:

.. code:: python

    In [1]: %install_ext https://raw.github.com/etgalloway/newtabmagic/master/newtabmagic.py

Startup
-------

To load :code:`newtabmagic`:

.. code:: python

    In [1]: %load_ext newtabmagic

The browser used to open new tabs needs to be specified.  To specify by
command name:

.. code:: python

    In [2]: %newtab --browser firefox

To specify by path:

.. code:: python

    In [2]: %newtab --browser C:/Program Files (x86)/Mozilla Firefox/firefox.exe

To set the pydoc server port:

.. code:: python

    In [3]: %newtab --port 8880

To start the pydoc server:

.. code:: python

    In [4]: %newtab --server start

Shutdown
--------

Shutting down IPython stops the pydoc server.

To stop the server without shutting down IPython:

.. code:: python

    In [1]: %newtab --server stop
