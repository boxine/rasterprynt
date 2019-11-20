#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='rasterprynt',
      version='1.0.5',
      description='Print raster graphics on Brother P950NW and 9800PCN',
      author='Philipp Hagemeister (Boxine GmbH)',
      author_email='philipp.hagemeister@boxine.de',
      license='MIT',
      packages=['rasterprynt'],
      install_requires=[
          'Pillow',
      ],
      url='https://github.com/boxine/rasterprynt/')
