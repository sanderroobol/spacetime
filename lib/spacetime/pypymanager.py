# This file is part of Spacetime.
#
# Copyright (C) 2012 Sander Roobol
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

import sys, os
import traceback
import subprocess
import multiprocessing.managers
import threading
import Queue
import random
import cPickle as pickle
import tempfile

# this module behaves as a singleton object when imported, and also serves as
# the entry point for the delegate (pypy) process

manager = None
delegate = None
is_pypy = False
jobs = None
results = None
stdoutthread = None
_executable = None
_authkey = None

class PyPyException(Exception):
	def __init__(self, exception, tb):
		super(PyPyException, self).__init__("\n{line}\n{tb}{exc}\n{line}".format(
			line='-'*60,
			tb=''.join(traceback.format_list(tb)),
			exc=repr(exception),
		))
		self.exception = exception
		self.traceback = tb

def get_authkey():
	global _authkey
	if _authkey is None:
		# generate 512 bit hexadecimal string
		_authkey = ''.join('{0:08x}'.format(random.randint(0, 2**32-1)) for i in range(16))
	return _authkey

def set_executable(executable):
	global _executable
	_executable = executable

def start(executable):
	global manager, jobs, results

	set_executable(executable)
	manager = multiprocessing.managers.BaseManager(address=('localhost', 0), authkey=get_authkey())
	_jobs = Queue.Queue()
	_results = Queue.Queue()
	manager.register('get_jobs', callable=lambda: _jobs)
	manager.register('get_results', callable=lambda: _results)

	manager.start()
	# we cannot use the queues directly, we need to get the proxies from the manager
	jobs = manager.get_jobs()
	results = manager.get_results()

def shutdown():
	global delegate, stdoutthread, manager

	if delegate:
		delegate.terminate()
		delegate.wait()
		# FIXME: do something with delegate.returncode?
		delegate = None

	if stdoutthread:
		stdoutthread.join()
		stdoutthread = None
		
	if manager:
		manager.shutdown()
		manager = None

def launch_delegate():
	global delegate, stdoutthread
	delegate = subprocess.Popen(
			[_executable, '-m', 'spacetime.pypymanager'],
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			close_fds=(not subprocess.mswindows),
		)
	delegate.stdin.write(pickle.dumps((manager.address, get_authkey()), pickle.HIGHEST_PROTOCOL))
	delegate.stdin.close()

	def readstdout(stdout):
		# a simple "for line in stdout" does not work here since it uses a large buffer,
		# this approach uses stdout.readline() which is slower but more responsive
		for line in iter(stdout.readline, ""):
			print "PyPy:", line,
		stdout.close()
	stdoutthread = threading.Thread(target=readstdout, args=(delegate.stdout,))
	stdoutthread.start()

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
	if not is_pypy and manager and check_delegate():
		jobs.put((func.__module__, func.__name__, args, kwargs))
		exception, traceback, filename = results.get()
		if exception:
			raise PyPyException(exception, traceback)
		with open(filename, 'rb') as fp:
			result = pickle.load(fp)
		os.remove(filename)
		return result
		
	# fall back to good old-fashioned DIY
	return func(*args, **kwargs)


# this is where the delegate process (pypy!) enters
if __name__ == '__main__':
	def debug(s):
		print s
		sys.stdout.flush()

	address, authkey = pickle.load(sys.stdin)
	manager = multiprocessing.managers.BaseManager(address=address, authkey=authkey)
	manager.connect()
	manager.register('get_jobs')
	manager.register('get_results')
	jobs = manager.get_jobs()
	results = manager.get_results()
	is_pypy = True
	debug("delegate running\n{0}".format(sys.version))

	# import numpypy to prepare pypy for numpy
	try:
		import numpypy
	except ImportError: # we're probably not running in PyPy, who cares
		pass

	while 1:
		# don't check if jobs.get() raises an exception, we better quit if something goes wrong here
		job = jobs.get()
		# we're now past the point of no return, we have to come up with an answer

		try:
			modname, funcname, args, kwargs = job
			debug("job: {0}.{1} {2} {3}".format(modname, funcname, args, kwargs))

			if modname == '__main__':
				result = (ImportError('cannot import from __main__'), traceback.extract_stack(), None)
				continue

			module = __import__(modname, globals(), locals(), [funcname])
			func = getattr(module, funcname)
			data = func(*args, **kwargs)
			try:
				with tempfile.NamedTemporaryFile(delete=False) as temp:
					pickle.dump(data, temp, pickle.HIGHEST_PROTOCOL)
			except:
				os.remove(temp.name)
				raise
			else:
				result = (None, None, temp.name)

		except Exception as e:
			debug("job failed with exception {0!r}".format(e))
			result = (e, traceback.extract_tb(sys.exc_info()[2]), None)
		finally:
			# by now, result is guaranteed to be defined as a 3-tuple
			# there's no exception handling: we want to abort if something goes wrong
			results.put(result)
