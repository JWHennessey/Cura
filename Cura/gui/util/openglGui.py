from __future__ import absolute_import
from __future__ import division

import wx
from wx import glcanvas
import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *

from Cura.gui.util import opengl

glButtonsTexture = None

class glGuiPanel(glcanvas.GLCanvas):
	def __init__(self, parent):
		attribList = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24, glcanvas.WX_GL_STENCIL_SIZE, 8)
		glcanvas.GLCanvas.__init__(self, parent, attribList = attribList)
		self._parent = parent
		self._context = glcanvas.GLContext(self)
		self._glGuiControlList = []
		self._buttonSize = 64

		wx.EVT_PAINT(self, self._OnGuiPaint)
		wx.EVT_SIZE(self, self._OnSize)
		wx.EVT_ERASE_BACKGROUND(self, self._OnEraseBackground)
		wx.EVT_MOUSE_EVENTS(self, self._OnGuiMouseEvents)
		wx.EVT_MOTION(self, self._OnGuiMouseMotion)

	def _OnGuiMouseEvents(self,e):
		if e.ButtonDown() and e.LeftIsDown():
			for ctrl in self._glGuiControlList:
				if ctrl.OnMouseDown(e.GetX(), e.GetY()):
					return

	def _OnGuiMouseMotion(self,e):
		self.Refresh()
		for ctrl in self._glGuiControlList:
			if ctrl.OnMouseMotion(e.GetX(), e.GetY()):
				return
		self.OnMouseMotion(e)

	def _OnGuiPaint(self, e):
		dc = wx.PaintDC(self)
		self.SetCurrent(self._context)
		self.OnPaint(e)
		self._drawGui()
		glFlush()
		self.SwapBuffers()

	def _drawGui(self):
		glDisable(GL_DEPTH_TEST)
		glEnable(GL_BLEND)
		glDisable(GL_LIGHTING)
		glColor4ub(255,255,255,255)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		size = self.GetSize()
		glOrtho(0, size.GetWidth()-1, size.GetHeight()-1, 0, -1000.0, 1000.0)
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()

		for glButton in self._glGuiControlList:
			glButton.draw()

	def _OnEraseBackground(self,event):
		#Workaround for windows background redraw flicker.
		pass

	def _OnSize(self,e):
		self.Refresh()

	def OnMouseEvents(self,e):
		pass

	def OnMouseMotion(self, e):
		pass
	def OnPaint(self, e):
		pass

class glButton(object):
	def __init__(self, parent, imageID, tooltip, x, y, callback):
		self._tooltip = tooltip
		self._parent = parent
		self._imageID = imageID
		self._x = x
		self._y = y
		self._callback = callback
		self._parent._glGuiControlList.append(self)
		self._selected = False
		self._focus = False
		self._hidden = False

	def setSelected(self, value):
		self._selected = value

	def setHidden(self, value):
		self._hidden = value

	def getSelected(self):
		return self._selected

	def draw(self):
		global glButtonsTexture
		if self._hidden:
			return
		if glButtonsTexture is None:
			glButtonsTexture = opengl.loadGLTexture('glButtons.png')

		cx = (self._imageID % 4) / 4
		cy = int(self._imageID / 4) / 4
		bs = self._parent._buttonSize

		glPushMatrix()
		glTranslatef(self._x * bs * 1.3 + bs * 0.8, self._y * bs * 1.3 + bs * 0.8, 0)
		glBindTexture(GL_TEXTURE_2D, glButtonsTexture)
		glEnable(GL_TEXTURE_2D)
		scale = 0.8
		if self._selected:
			scale = 1.0
		elif self._focus:
			scale = 0.9
		glScalef(bs * scale, bs * scale, bs * scale)
		glColor4ub(255,255,255,255)
		glBegin(GL_QUADS)
		glTexCoord2f(cx+0.25, cy)
		glVertex2f( 0.5,-0.5)
		glTexCoord2f(cx, cy)
		glVertex2f(-0.5,-0.5)
		glTexCoord2f(cx, cy+0.25)
		glVertex2f(-0.5, 0.5)
		glTexCoord2f(cx+0.25, cy+0.25)
		glVertex2f( 0.5, 0.5)
		glEnd()
		glDisable(GL_TEXTURE_2D)
		if self._focus:
			glColor4ub(0,0,0,255)
			glTranslatef(0, -0.55, 0)
			opengl.glDrawStringCenter(self._tooltip)
		glPopMatrix()

	def _checkHit(self, x, y):
		if self._hidden:
			return False
		bs = self._parent._buttonSize
		return -bs * 0.5 <= x - (self._x * bs * 1.3 + bs * 0.8) <= bs * 0.5 and -bs * 0.5 <= y - (self._y * bs * 1.3 + bs * 0.8) <= bs * 0.5

	def OnMouseMotion(self, x, y):
		if self._checkHit(x, y):
			self._focus = True
			return True
		self._focus = False
		return False

	def OnMouseDown(self, x, y):
		if self._checkHit(x, y):
			self._callback()