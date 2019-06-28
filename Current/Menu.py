from __future__ import absolute_import, division, print_function	#, unicode_literals

import wx

# This code is designed in such a way that all the instances of classes
# defined in this module can automatically go away after SetMenuBar is called
# on the return value from MenuBar.Create().  That is a bit tricky as we need
# the target to be passed to the various menu items for callbacks to work.

class MenuBar:
	""" MenuBar - Fancy MenuBar object"""
	def __init__(self, *menus):
		self._items = menus

	def Create(self, target):
		"""Create - create wx.MenuBar() object, populate and return it"""
		menuBar = wx.MenuBar()
		for item in self._items:
			item.Add(menuBar,target)
		return menuBar

class Menu:
	#TODO: Should I support On... and OnUpdate... event handlers and help text?
	#To do so would require item have a GetId() method in Add(...)
	#and for MenuBar.Append() to actually return an item
	def __init__(self, text, *items): #, **kwargs):
		self._text = text
		self._items = items
#		self._onEvent = kwargs.get('onEvent', None)
#		self._onUpdate = kwargs.get('onUpdate', None)
#		self._helpText = kwargs.get('helpText', "")

	def Add(self, parentMenu, target):
		menu = wx.Menu()
		for item in self._items:
			item.Add(menu, target)
		parentMenu.Append(menu, self._text)

#		# help text is never displayed, at least on Win32 ?
#		if self._onEvent:
#			target.Bind(wx.EVT_MENU,      self._onEvent,  item)
#		if self._onUpdate:
#			target.Bind(wx.EVT_UPDATE_UI, self._onUpdate, item)

class MenuItem:
	def __init__(self, id, text, helpText="", onEvent=None, onUpdate=None):
		self._id       = id
		self._text     = text
		self._helpText = helpText
		self._onEvent  = onEvent
		self._onUpdate = onUpdate

	def SetupCallbacks(self, item, target):
		if self._onEvent:
			target.Bind(wx.EVT_MENU,      self._onEvent,  item)
		if self._onUpdate:
			target.Bind(wx.EVT_UPDATE_UI, self._onUpdate, item)


class NormalItem(MenuItem):
	def Add(self, menu, target):
		item = menu.Append(self._id, self._text, self._helpText)
		self.SetupCallbacks(item, target)

class CheckedItem(MenuItem):
	def Add(self, menu, target):
		item = menu.AppendCheckItem(self._id, self._text, self._helpText)
		self.SetupCallbacks(item, target)

class RadioItem(MenuItem):
	def Add(self, menu, target):
		item = menu.AppendRadioItem(self._id, self._text, self._helpText)
		self.SetupCallbacks(item, target)

class Separator:
	def Add(self, menu, target):
		menu.AppendSeparator()

class SubMenu(MenuItem):
	def __init__(self, id, text, *items, **kwargs):
		MenuItem.__init__(self, id, text, **kwargs)
		self._items = items

	def Add(self, parentMenu, target):
		menu = wx.Menu()
		for item in self._items:
			item.Add(menu, target)

		# help text is never displayed, at least on Win32
		item = parentMenu.AppendMenu(self._id, self._text, menu, self._helpText)
		self.SetupCallbacks(item, target)
