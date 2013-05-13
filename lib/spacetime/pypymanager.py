# This file is part of Spacetime.
#
# Copyright (C) 2012-2013 Sander Roobol
#
# Spacetime is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Spacetime is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import traceback
import subprocess
import threading
if __name__ != '__main__': # otherwise the relative import will fail
	from . import upickle

# this module behaves as a singleton object when imported, and also serves as
# the entry point for the delegate (pypy) process

delegate = None
stderrthread = None
_executable = None

class PyPyException(Exception):
	def __init__(self, exception, tb):
		super(PyPyException, self).__init__("\n{line}\n{tb}{exc}\n{line}".format(
			line='-'*60,
			tb=''.join(traceback.format_list(tb)),
			exc=repr(exception),
		))
		self.exception = exception
		self.traceback = tb

def set_executable(executable):
	global _executable
	_executable = executable

def shutdown_delegate():
	global delegate, stderrthread

	if delegate:
		if delegate.poll() is None:
			delegate.terminate()
			delegate.wait()
		# FIXME: do something with delegate.returncode?
		delegate = None

	if stderrthread:
		stderrthread.join()
		stderrthread = None

def launch_delegate():
	global delegate, stderrthread
	shutdown_delegate() # cleanup any old delegates first

	delegate = subprocess.Popen(
			[_executable, os.path.realpath(__file__)],
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			close_fds=(not subprocess.mswindows),
		)

	def readstderr(stderr):
		# a simple "for line in stderr" does not work here since it uses a large buffer,
		# this approach uses stderr.readline() which is slower but more responsive
		for line in iter(stderr.readline, ""):
			print "PyPy:", line,
		stderr.close()
	stderrthread = threading.Thread(target=readstderr, args=(delegate.stderr,))
	stderrthread.start()

def check_delegate():
	if delegate.poll() is None:
		return True
	# FIXME: do something with delegate.returncode?
	launch_delegate()
	if delegate.poll() is None:
		return True
	else:
		# FIXME: show warning, delegate could not be restarted
		return False

def run(func, *args, **kwargs):
	if delegate and check_delegate():
		put(delegate.stdin, (func.__module__, func.__name__, args, kwargs))
		exception, traceback, result = get(delegate.stdout)
		if exception:
			raise PyPyException(exception, traceback)
		return result
		
	# fall back to good old-fashioned DIY
	return func(*args, **kwargs)

def put(pipe, obj):
	upickle.dump(obj, pipe, upickle.HIGHEST_PROTOCOL)
	pipe.flush()

def get(pipe):
	return upickle.load(pipe)


# this is where the delegate process (pypy!) enters
if __name__ == '__main__':
	def debug(s):
		sys.stderr.write(s)
		sys.stderr.flush()

	# locate spacetime
	file = os.path.realpath(__file__)
	dir = os.path.dirname(file)
	prefix = os.path.dirname(dir)
	if prefix not in sys.path:
		debug("adding '{0}' to path\n".format(prefix))
		sys.path.append(prefix)
	import spacetime.upickle as upickle

	debug("delegate running\n{0}\n".format(sys.version))

	# import numpypy to prepare pypy for numpy
	try:
		import numpypy
	except ImportError: # we're probably not running in PyPy, who cares
		pass

	while 1:
		# don't check if jobs.get() raises an exception, we better quit if something goes wrong here
		job = get(sys.stdin)
		# we're now past the point of no return, we have to come up with an answer

		try:
			modname, funcname, args, kwargs = job
			debug("job: {0}.{1} {2} {3}\n".format(modname, funcname, args, kwargs))

			if modname == '__main__':
				result = (ImportError('cannot import from __main__'), traceback.extract_stack(), None)
				continue

			module = __import__(modname, globals(), locals(), [funcname])
			func = getattr(module, funcname)
			result = (None, None, func(*args, **kwargs))
		except Exception as e:
			debug("job failed with exception {0!r}\n".format(e))
			result = (e, traceback.extract_tb(sys.exc_info()[2]), None)
		finally:
			# by now, result is guaranteed to be defined as a 3-tuple
			# there's no exception handling: we want to abort if something goes wrong
			put(sys.stdout, result)
