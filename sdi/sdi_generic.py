#! /usr/bin/python
"""
SDI generic data editor
"""

import wx

# Generic Editor Elements
# These are the pieces that are put together to form an editor

class EditorElement:
	def __init__(self, bc, data):
		self.bc, self.data = bc, data
		if (not hasattr(self, "auto_label")) or getattr(self, "auto_label"):
			self.bc.new_row()
			self.bc.text(data["name"]+":")
			self.build()
			self.bc.end_row()
		else:
			self.build()

class SingleLineValidated(EditorElement):
	def build(self):
		self.ctrl = wx.TextCtrl(self.bc.parent, -1)
		self.bc.sizer.Add(self.ctrl, 1, wx.EXPAND)
		self.ctrl.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
		self.ctrl.Bind(wx.EVT_CHAR, self.OnEdit)
		self.ctrl.SetValue(self.default)
		self.last_valid = self.default

	def update_validator(self):
		text = self.ctrl.GetValue()
		if self.validate(text):
			self.last_valid = text

	def OnEdit(self, e):
		self.update_validator()
		e.Skip()

	def OnKillFocus(self, e):
		self.update_validator()
		self.ctrl.SetValue(self.last_valid)

class ValueErrorValidated(SingleLineValidated):
	def validate(self, s):
		try:
			self.f(s)
			return True
		except ValueError:
			return False

class NumberBox(ValueErrorValidated):
	default = "0"
	f = float

class IntegerBox(ValueErrorValidated):
	default = "0"
	f = int

class StringBox(SingleLineValidated):
	default = ""
	def validate(self, s):
		return True

class NumberSlider(EditorElement):
	def build(self):
		self.ctrl = wx.Slider(self.bc.parent, -1, self.data["min"], self.data["min"], self.data["max"],
			style=wx.SL_AUTOTICKS|wx.SL_HORIZONTAL)
		self.format_str = "%%%is" % len(str(self.data["max"]))
		self.label = wx.StaticText(self.bc.parent, -1, self.format_str % self.data["min"])
		self.label.SetFont(self.bc.font)
		self.bc.sizer.Add(self.ctrl, 1, wx.EXPAND)
		self.bc.sizer.Add(self.label, 0, wx.EXPAND)
		self.ctrl.Bind(wx.EVT_SLIDER, self.OnSlide)

	def OnSlide(self, e):
		self.label.SetLabel(self.format_str % self.ctrl.GetValue())

class DropDownSelector(EditorElement):
	def build(self):
		choices = self.data["choices"]
		self.ctrl = wx.ComboBox(self.bc.parent, -1, choices=choices, style=wx.CB_READONLY)
		if choices:
			self.ctrl.SetValue(choices[0])
		self.bc.sizer.Add(self.ctrl, 1, wx.EXPAND)

class RadioButtonSelector(EditorElement):
	def build(self):
		choices = self.data["choices"]
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		for i, choice in enumerate(choices):
			rb = wx.RadioButton(self.bc.parent, -1, choice, **({} if i else {"style": wx.RB_GROUP}))
			sizer.Add(rb)
		self.bc.sizer.Add(sizer)

class Category(EditorElement):
	auto_label = False

	def build(self):
		self.bc.text(self.data["name"]+":")
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		sizer1.Add((20,0))
		sizer2 = wx.BoxSizer(wx.VERTICAL)
		sizer1.Add(sizer2)
		self.bc.sizer.Add(sizer1, 0, wx.EXPAND)
		sub_bc = BuildContext(self.bc.parent, sizer2)
		build_desc(sub_bc, self.data["desc"])

class

# Internals

class BuildContext:
	def __init__(self, parent, sizer):
		self.parent, self.sizer = parent, sizer
		self.font = wx.Font(14, wx.MODERN, wx.NORMAL, wx.NORMAL)
		self.sizer_stack = []

	def new_row(self):
		self.old_sizer = self.sizer
		self.sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.old_sizer.Add(self.sizer, 0, wx.EXPAND)

	def end_row(self):
		self.sizer = self.old_sizer

	def text(self, s):
		ctrl = wx.StaticText(self.parent, -1, s)
		ctrl.SetFont(self.font)
		self.sizer.Add(ctrl)

def build_desc(bc, desc):
	for line in desc:
		line[0](bc, line[1])

# Interface class
# Use this class to create a generic editor.

class GenericEditor:
	def __init__(self, parent, sizer, desc):
		self.bc = BuildContext(parent, sizer)
		self.desc = desc

	def build(self):
		build_desc(self.bc, self.desc)

if __name__ == "__main__":
	# Example usage.
	class Frame(wx.Frame):
		def __init__(self):
			wx.Frame.__init__(self, None, -1)
			sizer = wx.BoxSizer(wx.VERTICAL)
			self.SetSizer(sizer)

			ge = GenericEditor(self, sizer, [
				(TextElement, {"n
				(Category, {"name": "position", "desc": [
					(NumberBox, {"name": "x"}),
					(IntegerBox, {"name": "y"}),
					(StringBox, {"name": "z"}),
				]}),
				(NumberSlider, {"name": "w", "min": 0, "max": 100}),
				(DropDownSelector, {"name": "a", "choices": ["Foo", "Bar", "Baz"]}),
				(RadioButtonSelector, {"name": "b", "choices": ["Foo", "Bar", "Baz"]}),
			])
			ge.build()

	class App(wx.App):
		def OnInit(self):
			Frame().Show(True)
			return True

	App().MainLoop()

