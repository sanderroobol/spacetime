from .generic.panels import SubplotPanel
import os, glob

class PanelManager(object):
	def __init__(self):
		self.panels_by_module = {}
		self.modules = {}
		self._list_classes = []
		self._detect_panels()
		self._list_labels = tuple(klass.label for klass in self._list_classes)

		self.mapping_id_class = {}
		self.mapping_classobjectid_id = {}
		for klass in self._list_classes:
			if klass.id in self.mapping_id_class:
				old = self.mapping_id_class[klass.id]
				raise ValueError("panel id '%s' conflict: %s.%s and %s.%s" % (klass.id, klass.__module__, klass.__name__, old.__module__, old.__name__))
			self.mapping_id_class[klass.id] = klass
			self.mapping_classobjectid_id[id(klass)] = klass.id

	def _detect_panels(self):
		# this function looks through in spacetime.modules.*.panels.* for any class that
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
			module = __import__('spacetime.modules.%s' % mname, globals(), locals(), ['panels'], -1)
			self.panels_by_module[mname] = []
			for i in dir(module.panels):
				obj = getattr(module.panels, i)
				try:
					if issubclass(obj, SubplotPanel) and hasattr(obj, 'id') and obj.id and obj.__module__ == 'spacetime.modules.%s.panels' % mname:
						self.panels_by_module[mname].append(obj)
						self._list_classes.append(obj)
				except TypeError: # obj is not a class
					pass

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
