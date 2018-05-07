#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='rasterprynt',
      version='1.0',
      description='Print raster graphics on Brother P950NW and 9800PCN',
      author='Boxine GmbH',
      author_email='it@boxine.de',
      packages=['rasterprynt'],
      install_requires=[
          'Pillow',
      ],
      url='https://github.com/boxine/rasterprynt/')
