from distutils.core import setup, Extension
import os

NUMPY_INCLUDE_PATH = '/usr/lib/python2.7/dist-packages/numpy/core/include/numpy/'

cutils = Extension('pygif.cutils',
                     sources = ['lib/cutils.c'],
                     include_dirs = [NUMPY_INCLUDE_PATH])

setup(name='pygif',
      version = '0.0',
      description = 'Python GIF Library',
      author = 'Tim Credo',
      package_dir = {'pygif': 'lib'},
      packages = ['pygif'],
      ext_modules = [cutils],
      requires = ['numpy','Image'])
