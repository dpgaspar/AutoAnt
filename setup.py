import os
import sys
import imp
import multiprocessing
from setuptools import setup, find_packages

PKG_DIR = 'autoant'
version = imp.load_source('version', os.path.join('autoant', 'version.py'))

def fpath(name):
    return os.path.join(os.path.dirname(__file__), name)

def read(fname):
    return open(fpath(fname)).read()

def desc():
    return read('README.rst')

setup(
    name='autoant',
    version=version.VERSION_STRING,
    url='https://github.com/dpgaspar/autoant/',
    license='BSD',
    author='Daniel Vaz Gaspar',
    author_email='danielvazgaspar@gmail.com',
    description='File processing automation',
    long_description=desc(),
    packages=find_packages(),
    package_data={'': ['LICENSE']},
    include_package_data=True,
    entry_points={'console_scripts': [
          'autoant_console = autoant.console:main',
      ]},
    zip_safe=False,
    platforms='any',
    install_requires=[
        'itsdangerous>=0.20'
    ],
    tests_require=[
        'nose>=1.0',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: System :: Systems Administration'
    ],
    test_suite='nose.collector'
)
