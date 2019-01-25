import time
from os import path
from pydm import Display
from scipy.ndimage.measurements import maximum_position
from scipy.ndimage.interpolation import zoom
from qtpy.QtWidgets import QWidget, QGridLayout, QPushButton
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.label import PyDMLabel
import math
import epics
import numpy as np

class BetaScan(Display):

	def __init__(self, parent=None, args=None):
		super(BetaScan, self).__init__(parent=parent, args=args)
		self.ui.imageView.mousePressEvent = self.get_coord
		self.ui.imageView.process_image = self.process_image

		self.motorRead = self.ui.EmbeddedMotor.findChild(PyDMLabel,"motorPosRead")
		self.motorSet = self.ui.EmbeddedMotor.findChild(PyDMLineEdit,"motorPosSet")
	
		self.motorGo = self.ui.EmbeddedMotor.findChild(QPushButton,"motorMove")
		self.motorGo.mousePressEvent = self.move_motor
		
		self.imageXSize = epics.PV('PelmeniNDSA:cam1:ArraySize0_RBV')
		self.imageYSize = epics.PV('PelmeniNDSA:cam1:ArraySize1_RBV')
		self.binYSize = epics.PV('PelmeniDet:ROI1:BinY_RBV')
		self.zoomedSize = 1
		self.imageHeight = 672.0
		
		
	def ui_filename(self):
		# Point to UI file
		return 'betaScan.ui'

	def ui_filepath(self):
		# Return the full path to the UI file
		return path.join(path.dirname(path.realpath(__file__)), self.ui_filename())

	def move_motor(self, event):
		self.motorSet.send_value()

	def zoomed_image(self, new_image, ys, mag):
		new_image = np.asarray(new_image)
		slices = [slice(0, new_image.shape[0], 1/mag)]
		idxs = (np.mgrid[slices]).astype('i')
		return new_image[tuple(idxs)]
		
	def process_image(self, new_image):
		yIters, xLength = new_image.shape
		binSize = self.binYSize.get()
		magnification = math.floor(self.imageHeight/float(yIters))
		print(self.imageHeight, xLength, yIters, magnification)
		
		newer_image = self.zoomed_image(new_image, yIters, magnification)
		
		self.zoomedSize = newer_image.shape[0]
		print("Image size: {}".format(newer_image.shape))
		return newer_image

	def get_coord(self, event):
        # Check that mouse-click is in image
		self.coords = [event.pos().x(), event.pos().y()]
		mouseY = float(event.pos().y())
		yExtent = self.zoomedSize

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
		
		
#		mouseExtent = 480 ## would prefer to get this number programmatically
		mouseExtent = self.ui.imageView.height()

		chosenY = ((1.0 - (mouseY / mouseExtent * (yMax - 
					yMin) + yMin) / yExtent) * (motorScanStartPos - 
					(motorScanStopPos + motorScanStepSize)) + motorScanStopPos +
					motorScanStepSize)
					
		limits = [motorScanStartPos, motorScanStopPos + motorScanStepSize]
		if ((chosenY <= max(limits)) and (chosenY >= min(limits))):
				steps = (math.floor((chosenY - motorScanStartPos)/motorScanStepSize))
				chosenY_disc = steps * motorScanStepSize + motorScanStartPos
				self.motorSet.setText(str(chosenY_disc))
			
		print("****************************************************************")
		print("mouseY, mouseExtent: {}, {}".format(mouseY, mouseExtent))
		print("yMin, yMax, yExtent: {}, {}, {}".format(yMin, yMax, yExtent))
		print("motor scan start, stop, step: {}, {}, {}".format(motorScanStartPos, motorScanStopPos, motorScanStepSize))
		print("chosenY, limits: {}, {}".format(chosenY, limits))
