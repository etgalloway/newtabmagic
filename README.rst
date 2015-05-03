===========
newtabmagic
===========

newtabmagic is an `IPython`_ CLI for viewing `pydoc`_ documentation in
the browser.

.. _pydoc: https://docs.python.org/3/library/pydoc.html
.. _IPython: http://ipython.org/

Install
=======

As a Python package:

.. code::

    $ pip install newtabmagic

As an IPython extension:

.. code::

    In [1]: %install_ext https://raw.github.com/etgalloway/newtabmagic/master/newtabmagic.py

Use
===

Load the extension:

.. code::

    In [1]: %load_ext newtabmagic

Start the pydoc server:

.. code::

    In [2]: %newtab --server start
    Starting job # 0 in a separate thread.
    Server running at http://127.0.0.1:63146/

View documentation in the browser:

.. code::

    In [3]: %newtab IPython.core.debugger.Tracer

    In [4]: import IPython
    In [5]: tracer = IPython.core.debugger
    In [6]: %newtab tracer
