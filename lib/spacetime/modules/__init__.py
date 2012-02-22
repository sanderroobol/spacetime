# This file is part of Spacetime.
#
# Copyright (C) 2010-2012 Leiden University.
# Written by Sander Roobol.
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

from .generic.panels import SubplotPanel
import os, glob

class Loader(object):
	def __init__(self):
		self.panels_by_module = {}
		self.modules = {}
		self._list_classes = []
		self._detect_modules()
		self._list_labels = tuple(klass.label for klass in self._list_classes)

		self.mapping_id_class = {}
		self.mapping_classobjectid_id = {}
		for klass in self._list_classes:
			if klass.id in self.mapping_id_class:
				old = self.mapping_id_class[klass.id]
				raise ValueError("panel id '{0.id}' conflict: {0.__module__}.{0.__name__} and {1.__module__}.{1.__name__}".format(klass, old))
			self.mapping_id_class[klass.id] = klass
			self.mapping_classobjectid_id[id(klass)] = klass.id

	def _detect_modules(self):
		# this function looks in spacetime.modules.*.panels.* for any class that
        # 1. inherits from SubplotPanel
		# 2. has a id attribute
		# 3. is found in the same module where it is defined (suppose
		#    modules.A.panels imports modules.B.panels.B, than B will be ignored
		#    a when looking through A.panels.*)
		
		mdir = os.path.dirname(__file__)
		panel_files = glob.glob(os.path.join(mdir, '*', 'panels.py'))
		modules = [os.path.split(os.path.split(f)[0])[1] for f in panel_files]
		for mname in modules:
			self.modules[mname] = getattr(__import__('spacetime.modules', globals(), locals(), [mname], -1), mname)
			module = __import__('spacetime.modules.{0}'.format(mname), globals(), locals(), ['panels'], -1)
			self.panels_by_module[mname] = []
			for i in dir(module.panels):
				obj = getattr(module.panels, i)
				if isinstance(obj, type) and issubclass(obj, SubplotPanel) and hasattr(obj, 'id') and obj.id and obj.__module__ == 'spacetime.modules.{0}.panels'.format(mname):
					self.panels_by_module[mname].append(obj)
					self._list_classes.append(obj)

	def list_classes(self):
		return self._list_classes

	def list_labels(self):
		return self._list_labels

	def get_class_by_id(self, id):
		return self.mapping_id_class[id]

	def get_id_by_instance(self, obj):
		return self.mapping_classobjectid_id[id(obj.__class__)]

	def get_module_by_name(self, name):
		return self.modules[name]
