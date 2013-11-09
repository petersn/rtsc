#! /usr/bin/python

_new_tag = 0
def new():
	global _new_tag
	_new_tag += 1
	return _new_tag

class Entity:
	def __init__(self, sid):
		"""
		The idea of an Entity is that it has event receivers, and is capable of serializing itself.
		"""
		self.sid = sid
		self.default_constructor()

	# Methods to redefine:

	def receive(self, event):
		print "Entity base class received event:", event

	def serialize(self):
		raise Exception("cannot serialize the Entity base class")

class Integer(Entity):
	def default_constructor(self):
		self.value = 0

	def serialize(self):
		return "%s" % self.value

	def deserialize(self, s):
		return int(s)

