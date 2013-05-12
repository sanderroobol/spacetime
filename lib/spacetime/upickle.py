# Universal pickling between numpy@CPython and numpypy (numpy@PyPy).
# Written by Sander Roobol. Public domain.

try:
	import cPickle as pickle
except ImportError:
	import pickle

try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO

import sys
import platform
import inspect

__all__ = ['dump', 'dumps', 'load', 'loads', 'HIGHEST_PROTOCOL', 'PickleError']

dump = pickle.dump
dumps = pickle.dumps
HIGHEST_PROTOCOL = pickle.HIGHEST_PROTOCOL
PickleError = pickle.PickleError

if platform.python_implementation() == 'PyPy':
	# numpy -> numpypy
	def _translate(module, name):
		parts = module.split('.')
		if parts[0] == 'numpy':
			parts[0] = 'numpypy'
		module = '.'.join(parts)
		if module == 'numpypy.core.multiarray':
			module = '_numpypy.multiarray'
		return module, name

else:
	# numpypy -> numpy
	def _translate(module, name):
		parts = module.split('.')
		if parts[0] == 'numpypy' or parts[0] == '_numpypy':
			parts[0] = 'numpy'
		module = '.'.join(parts)
		if module == 'numpy.multiarray':
			module = 'numpy.core.multiarray'
		return module, name


if inspect.isbuiltin(pickle.Unpickler):
	# real cPickle: cannot subclass
	def _find_global(module, name):
		module, name = _translate(module, name)
		__import__(module)
		return getattr(sys.modules[module], name)

	def load(fileobj):
		unpickler = pickle.Unpickler(fileobj)
		unpickler.find_global = _find_global
		return unpickler.load()

else:
	# pure python implementation: ordinary pickle or pypy's cPickle
	class _Unpickler(pickle.Unpickler):
		def find_class(self, module, name):
			module, name = _translate(module, name)
			return pickle.Unpickler.find_class(self, module, name)

	def load(fileobj):
		unpickler = _Unpickler(fileobj)
		return unpickler.load()


def loads(str):
	return load(StringIO(str))
