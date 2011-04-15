# FIXME: 
# The submodules should not be imported when importing this module.
# Instead the PanelMapper should be explicitly initiated on request (by the
# GUI) and should take care of automagically importing all submodules in this
# directory.

from . import generic, interfacephysics, lpmcamera, lpmgascabinet, quadera

class PanelManager(object):
	_list_classes = (
		lpmcamera.panels.CameraFramePanel,
		lpmcamera.panels.CameraTrendPanel,
		quadera.panels.QMSPanel,
		lpmgascabinet.panels.GasCabinetPanel,
		interfacephysics.panels.OldGasCabinetPanel,
		interfacephysics.panels.ReactorEnvironmentPanel,
		interfacephysics.panels.TPDirkPanel,
		interfacephysics.panels.CVPanel,
	)

	_list_labels = tuple(klass.label for klass in _list_classes)

	mapping_id_class = dict((klass.id, klass) for klass in _list_classes)
	mapping_classname_id = dict((klass.__name__, id) for klass in _list_classes)
	mapping_label_class = dict((klass.label, klass) for klass in _list_classes)

	def list_classes(self):
		return self._list_classes

	def list_labels(self):
		return self._list_labels

	def get_class_by_id(self, id):
		return self.mapping_id_class[id]

	def get_id_by_instance(self, obj):
		return self.mapping_classname_id[obj.__class__.__name__]

	def get_class_by_label(self, label):
		return self.mapping_label_class[label]
