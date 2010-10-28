class Struct(object):
	def __init__(self, **kwargs):
		super(Struct, self).__setattr__('data', kwargs)

	def __getattribute__(self, name):
		if name.startswith('__'):
			return super(Struct, self).__getattribute__(name)
		try:
			return super(Struct, self).__getattribute__('data')[name]
		except KeyError:
			s = Struct()
			super(Struct, s).__setattr__('parent', self)
			super(Struct, s).__setattr__('name', name)
			return s

	def __setattr__(self, name, value):
		super(Struct, self).__getattribute__('data')[name] = value

		i = self
		while 1:
			try:
				name = super(Struct, i).__getattribute__('name')
			except AttributeError:
				break
			else:
				parent = super(Struct, i).__getattribute__('parent')
				super(Struct, parent).__getattribute__('data')[name] = i
				super(Struct, i).__delattr__('name')
				i = parent

	def __delattr__(self, name):
		del super(Struct, self).__getattribute__('data')[name]

	__getitem__ = __getattribute__
	__setitem__ = __setattr__
	__delitem__ = __delattr__

	def __repr__(self):
		return "Struct" + repr(super(Struct, self).__getattribute__('data'))
	
	def __nonzero__(self):
		return bool(super(Struct, self).__getattribute__('data'))

if __name__ == '__main__':
	### run some tests
	s = Struct()
	s.a = 1
	s.b.c = 2
	s.c.d.e.f = 3
	assert repr(s) == "Struct{'a': 1, 'c': Struct{'d': Struct{'e': Struct{'f': 3}}}, 'b': Struct{'c': 2}}"
	assert repr(s.c.d) == "Struct{'e': Struct{'f': 3}}"
	assert bool(s.c.d)
	assert not bool(s.c.e)
	s.b = 4
	del s.c.d
	assert repr(s) == "Struct{'a': 1, 'c': Struct{}, 'b': 4}"
