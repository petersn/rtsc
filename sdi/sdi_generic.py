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
		self.bc.elements.append(self)
		if (not hasattr(self, "auto_label")) or getattr(self, "auto_label"):
			self.bc.new_row()
			self.bc.text(data["name"]+":")
			self.build()
			self.bc.end_row()
		else:
			self.build()

	def extract_data(self):
		return {self.data["name"]: self.get_value()}

class SingleLineValidated(EditorElement):
	def build(self):
		self.ctrl = wx.TextCtrl(self.bc.parent, -1)
		self.bc.sizer.Add(self.ctrl, 1, wx.EXPAND if self.expand else 0)
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
	expand = False
	def validate(self, s):
		try:
			self.f(s)
			return True
		except ValueError:
			return False

	def get_value(self):
		return self.f(self.last_valid)

class NumberBox(ValueErrorValidated):
	default = "0"
	f = float

class IntegerBox(ValueErrorValidated):
	default = "0"
	f = int

class StringBox(ValueErrorValidated):
	default = ""
	expand = True
	f = str

class CtrlGetValueMixin:
	def get_value(self):
		return self.ctrl.GetValue()

class NumberSlider(EditorElement, CtrlGetValueMixin):
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
		self.ctrl.SetSelection(0)
		self.bc.sizer.Add(self.ctrl, 1, wx.EXPAND)

	def get_value(self):
		return self.ctrl.GetSelection()

class RadioButtonSelector(EditorElement):
	def build(self):
		choices = self.data["choices"]
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.radio_buttons = []
		for i, choice in enumerate(choices):
			rb = wx.RadioButton(self.bc.parent, -1, choice, **({} if i else {"style": wx.RB_GROUP}))
			self.radio_buttons.append(rb)
			sizer.Add(rb)
		self.bc.sizer.Add(sizer)

	def get_value(self):
		return [rb.GetValue() for rb in self.radio_buttons].index(True)

class Checkbox(EditorElement, CtrlGetValueMixin):
	# We have to do weird shenanigains to get the wx.CheckBox's label
	# to act like the little text label we'd otherwise create, so we
	# have to set auto_label = False here, unfortunately.
	auto_label = False

	def build(self):
		# Don't use BuildContext's new_row, because it adds a spacer,
		# which here is built into the CheckBox's label.
		self.ctrl = wx.CheckBox(self.bc.parent, -1, label=self.data["name"]+":", style=wx.ALIGN_RIGHT)
		self.ctrl.SetFont(self.bc.font)
		self.bc.sizer.Add(self.ctrl)

class List(EditorElement):
	auto_label = False

	def build(self):
		self.bc.new_row()
		self.bc.text(self.data["name"]+":")
		self.bc.end_row()
#		self.ctrl = wx.gizmos.EditableListBox(self.bc.parent, -1, style=wx.gizmos.EL_ALLOW_NEW|wx.gizmos.EL_ALLOW_DELETE)
		self.ctrl = wx.ListBox(self.bc.parent, -1, style=wx.LB_MULTIPLE)
		self.bc.sizer.Add(self.ctrl, 1, wx.EXPAND)
		self.bc.new_row()
		self.buttons = [wx.Button(self.bc.parent, -1, s) for s in ["Add", "Delete", "Move Up", "Move Down"]]
		for b in self.buttons:
			self.bc.sizer.Add(b, 1, wx.EXPAND)
		for b, f in zip(self.buttons, (self.OnAdd, self.OnDelete, self.OnMoveUp, self.OnMoveDown)):
			b.Bind(wx.EVT_BUTTON, f)
		self.bc.end_row()

	def OnAdd(self, e):
		import random
		self.ctrl.AppendAndEnsureVisible("<empty datum %i>" % random.randint(0, 1000))

	def OnDelete(self, e):
		# Iterate in reverse order because Deletions don't commute!
		for index in sorted(self.ctrl.GetSelections(), reverse=True):
			self.ctrl.Delete(index)

	def OnMoveUp(self, e):
		self.move_selections(direction=-1)

	def OnMoveDown(self, e):
		self.move_selections(direction=1)

	def move_selections(self, direction=1):
		dont_move = self.ctrl.GetCount()-1 if direction == 1 else 0
		selection = []
		for index in sorted(self.ctrl.GetSelections(), reverse=direction > 0):
			if index == dont_move:
				selection.append(index)
				dont_move += -direction # Propagate the not-motion
				continue 
			s = self.ctrl.GetString(index)
			self.ctrl.Delete(index)
			self.ctrl.Insert(s, index+direction)
			selection.append(index+direction)
		self.ctrl.SetSelection(wx.NOT_FOUND)
		map(self.ctrl.Select, selection)

	def get_value(self):
		return []

class Category(EditorElement):
	auto_label = False

	def build(self):
		self.bc.new_row()
		self.bc.text(self.data["name"]+":")
		self.bc.end_row()
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		sizer1.Add((20,0))
		sizer2 = wx.BoxSizer(wx.VERTICAL)
		sizer1.Add(sizer2)
		self.bc.sizer.Add(sizer1, 0, wx.EXPAND)
		self.sub_bc = BuildContext(self.bc.parent, sizer2)
		build_desc(self.sub_bc, self.data["desc"])

	def get_value(self):
		return self.sub_bc.extract_data()

class TextLabel(EditorElement):
	auto_label = False

	def build(self):
		self.bc.new_row()
		self.bc.text(self.data["label"])
		self.bc.end_row()

	def extract_data(self):
		return {}

# Internals

class BuildContext:
	def __init__(self, parent, sizer):
		self.elements = []
		self.parent, self.sizer = parent, sizer
		self.font = wx.Font(14, wx.MODERN, wx.NORMAL, wx.NORMAL)
		self.sizer_stack = []

	def new_row(self):
		self.old_sizer = self.sizer
		self.sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add((2,0)) # Small spacing.
		self.old_sizer.Add(self.sizer, 0, wx.EXPAND)

	def end_row(self):
		self.sizer = self.old_sizer

	def text(self, s):
		ctrl = wx.StaticText(self.parent, -1, s)
		ctrl.SetFont(self.font)
		self.sizer.Add(ctrl)

	def extract_data(self):
		d = {}
		for element in self.elements:
			d.update(element.extract_data())
		return d

def build_desc(bc, desc):
	for line in desc:
		line[0](bc, line[1])

# Interface class
# Use this class to create a generic editor.

class GenericEditor:
	def __init__(self, parent, sizer, desc):
		self.bc = BuildContext(parent, sizer)
		self.desc = desc
		self.extract_data = self.bc.extract_data

	def build(self):
		build_desc(self.bc, self.desc)

if __name__ == "__main__":
	# Example usage.
	class Frame(wx.Frame):
		def __init__(self):
			wx.Frame.__init__(self, None, -1)
			sizer = wx.BoxSizer(wx.VERTICAL)
			self.SetSizer(sizer)

			self.ge = GenericEditor(self, sizer, [
				(TextLabel, {"label": "Edit this position easily."}),
				(Category, {"name": "position", "desc": [
					(NumberBox, {"name": "x"}),
					(IntegerBox, {"name": "y"}),
					(StringBox, {"name": "z"}),
				]}),
				(NumberSlider, {"name": "w", "min": 0, "max": 100}),
				(DropDownSelector, {"name": "a", "choices": ["Foo", "Bar", "Baz"]}),
				(RadioButtonSelector, {"name": "b", "choices": ["Foo", "Bar", "Baz"]}),
				(Checkbox, {"name": "int"}),
				(List, {"name": "foo"}),
				(List, {"name": "qux"}),
			])
			self.ge.build()

			menubar = wx.MenuBar()
			file = wx.Menu()
			file.Append(101, 'Print', '' )
			menubar.Append(file, "&File")
			self.SetMenuBar(menubar)
			wx.EVT_MENU(self, 101, self.Print)

		def Print(self, e):
			import pprint
			pprint.pprint(self.ge.extract_data())

	class App(wx.App):
		def OnInit(self):
			Frame().Show(True)
			return True

	App().MainLoop()

