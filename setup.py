"""Setup file for newtabmagic."""

from setuptools import setup
from newtabmagic import __version__

description = 'IPython CLI for viewing documentation in the browser'

with open('README.rst') as file:
    long_description = file.read()

_classifiers = [
    'Framework :: IPython',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    ]

keywords = 'CLI documentation IPython pydoc'

setup(
    name='newtabmagic',
    version=__version__,
    py_modules=['newtabmagic'],
    author='Eric Galloway',
    author_email='ericgalloway@gmail.com',
    description=description,
    long_description=long_description,
    url='https://github.com/etgalloway/newtabmagic',
    classifiers=_classifiers,
    keywords=keywords,
    zip_safe=False,
    install_requires=['ipython']
    )
