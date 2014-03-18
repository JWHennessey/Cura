import wx
import numpy
import time
import os
import traceback
import threading
import math
import platform

import re
import subprocess
import sys
import power
import datetime
import shutil


from Cura.util import profile
from Cura.util import meshLoader
from Cura.util import objectScene
from Cura.util import sliceEngine
from Cura.util import removableStorage
from Cura.util import gcodeInterpreter
from Cura.gui.util import previewTools
from Cura.gui.util import opengl
from Cura.gui.util import openglGui
from Cura.gui.tools import youmagineGui
from Cura.gui.tools import imageToMesh
from Cura.gui.util import webcam
from Cura.gui.util import taskbar
from Cura.util import machineCom
from Cura.util import gcodeInterpreter
from Cura.util import resources

#The printProcessMonitor is used from the main GUI python process. This monitors the printing python process.
# This class also handles starting of the 2nd process for printing and all communications with it.
class printProcessMonitor():
    def __init__(self, callback = None):
        self.handle = None
        self._state = 'CLOSED'
        self._z = 0.0
        self._callback = callback
        self._id = -1
        self._gcode = []
        self._gcodePos = 0
        self.model = None

    def loadFile(self, filename, id):
        if self.handle is None:
            if platform.system() == "Darwin" and hasattr(sys, 'frozen'):
                cmdList = [os.path.join(os.path.dirname(sys.executable), 'Cura')]
            else:
                cmdList = [sys.executable, '-m', 'Cura.cura']
            cmdList.append('-r')
            cmdList.append(filename)
            if platform.system() == "Darwin":
                if platform.machine() == 'i386':
                    cmdList.insert(0, 'arch')
                    cmdList.insert(1, '-i386')
            #Save the preferences before starting the print window so we use the proper machine settings.
            profile.savePreferences(profile.getPreferencePath())
            self.handle = subprocess.Popen(cmdList, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.thread = threading.Thread(target=self.Monitor)
            self.thread.start()
        else:
            self.handle.stdin.write('LOAD:%s\n' % filename)
        self._id = id

    def Monitor(self):
        p = self.handle
        line = p.stdout.readline()
        while len(line) > 0:
            line = line.rstrip()
            #print line
            try:
                if line.startswith('Z:'):
                    self._z = float(line[2:])
                    self._callCallback()
                elif line.startswith('STATE:'):
                    self._state = line[6:]
                    self._callCallback()
                elif line.startswith('NEWGCODE:'):
                    self._gcode = []
                    self._gcodePos = long(line[9:])
                elif line.startswith('GCODE:'):
                    self._gcode.append(line[6:])
                elif line.startswith('GCODE-TUPLE:'):
                    self._gcode.append(tuple(line[12:].split(':')))
                #else:
                    #print '>' + line.rstrip()
            except:
                print sys.exc_info()
            line = p.stdout.readline()
        line = p.stderr.readline()
        while len(line) > 0:
            print '>>' + line.rstrip()
            line = p.stderr.readline()
        p.communicate()
        self.handle = None
        self.thread = None

    def getID(self):
        return self._id

    def getZ(self):
        return self._z

    def getState(self):
        return self._state

    def getGcode(self):
        return self._gcode

    def getGcodePos(self):
        return self._gcodePos

    def _callCallback(self):
        if self._callback is not None:
            self._callback()
