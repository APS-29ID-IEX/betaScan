import time
from os import path
from pydm import Display
from scipy.ndimage.measurements import maximum_position
from qtpy.QtWidgets import QWidget, QGridLayout, QPushButton
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.label import PyDMLabel
import math
import epics

class BetaScan(Display):

	def __init__(self, parent=None, args=None):
		super(BetaScan, self).__init__(parent=parent, args=args)
		self.ui.imageView.mousePressEvent = self.get_coord

		self.motorRead = self.ui.EmbeddedMotor.findChild(PyDMLabel,"motorPosRead")
		self.motorSet = self.ui.EmbeddedMotor.findChild(PyDMLineEdit,"motorPosSet")
	
		self.motorGo = self.ui.EmbeddedMotor.findChild(QPushButton,"motorMove")
		self.motorGo.mousePressEvent = self.move_motor
		
		self.imageYSize = epics.PV('PelmeniNDSA:cam1:ArraySize1_RBV')
		
		
	def ui_filename(self):
		# Point to our UI file
		return 'betaScan.ui'

	def ui_filepath(self):
		# Return the full path to the UI file
		return path.join(path.dirname(path.realpath(__file__)), self.ui_filename())

	def move_motor(self, event):
		self.motorSet.send_value()

	def get_coord(self, event):
        # Check that mouse-click is in image
		self.coords = [event.pos().x(), event.pos().y()]
		mouseY = float(event.pos().y())
		# Need data from ca://PelmeniNDSA:cam1:ArraySize1_RBV since ImageYSize
		# PyDMLabel has been removed:
		#yExtent = float(self.ui.ImageYSize.text())
		yExtent = self.imageYSize.get()


		# Image boundaries returned as [[xmin, xmax], [ymin, ymax]]
		view = self.ui.imageView.getView()
		vRange = view.viewRange()
		yMin, yMax = float(vRange[1][0]), float(vRange[1][1])
		
		scanStartPos = self.ui.EmbeddedScan.findChild(PyDMLabel,"ScanStartPosRead")
		scanStopPos = self.ui.EmbeddedScan.findChild(PyDMLabel,"ScanStopPosRead")
		scanStepSize = self.ui.EmbeddedScan.findChild(PyDMLabel,"ScanStepSizeRead")
		
		motorScanStepSize = float(scanStepSize.text())
		motorScanStartPos = float(scanStartPos.text())
		motorScanStopPos = float(scanStopPos.text())
					
		motorCurrPos = float(self.motorRead.text())
		
		mouseExtent = 480 ## would prefer to get this number programmatically
		
		chosenY = ((1.0 - (mouseY / mouseExtent * (yMax - 
					yMin) + yMin) / yExtent) * (motorScanStartPos - 
					(motorScanStopPos + motorScanStepSize)) + motorScanStopPos +
					motorScanStepSize)
					
		limits = [motorScanStartPos, motorScanStopPos + motorScanStepSize]
		if ((chosenY <= max(limits)) and (chosenY >= min(limits))):
				steps = (math.floor((chosenY - motorScanStartPos)/motorScanStepSize))
				chosenY_disc = steps * motorScanStepSize + motorScanStartPos
				self.motorSet.setText(str(chosenY_disc))
		
		mouse_txt = "Mouse click at:"
		mouse_txt += " ({}, {})".format(self.coords[0], self.coords[1])
		mouse_txt += "\n Image vertical extent (y_min, y_max): \n"
		mouse_txt += "({}, {})".format(yMin, yMax)

		yPos_txt = "Mouse click converted to y-position of (clicked value, actual position): \n"
		yPos_txt += " {}, {}".format(chosenY, motorCurrPos)
