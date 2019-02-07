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

class LiveScan(Display):

	def __init__(self, parent=None, args=None):
		super(LiveScan, self).__init__(parent=parent, args=args)
		self.ui.BetaView.mousePressEvent = self.get_beta_coord
		self.ui.BetaView.process_image = self.process_beta_image
		self.ui.XYView.mousePressEvent = self.get_xy_coord
		self.ui.XYView.process_image = self.process_xy_image
		self.ui.liveViewButton.mousePressEvent = self.toggle_liveView

		self.motor1DRead = self.ui.EmbeddedMotor.findChild(PyDMLabel,"motorPosRead")
		self.motor1DSet = self.ui.EmbeddedMotor.findChild(PyDMLineEdit,"motorPosSet")
		self.motor1DGo = self.ui.EmbeddedMotor.findChild(QPushButton,"motorMove")
		self.motor1DGo.mousePressEvent = self.move_motor
	
		self.imageXSize = epics.PV('PelmeniNDSA:cam1:ArraySize0_RBV')
		self.imageYSize = epics.PV('PelmeniNDSA:cam1:ArraySize1_RBV')
		self.binYSize = epics.PV('PelmeniDet:ROI1:BinY_RBV')
		self.zoomedSize = 1
		self.imageHeight = 672.0 #Needs to be set programmatically?
		
		self.camMode = epics.PV('PelmeniDet:cam1:ImageMode')
		self.camAcq = epics.PV('PelmeniDet:cam1:Acquire')
		self.camSetting = False
		
	def ui_filename(self):
		# Point to UI file
		return 'liveScan.ui'

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

	def toggle_liveView(self, event):
		if self.camSetting:
			self.camMode.put(0)
			self.camAcq.put(0)
		else:
			self.camMode.put(2)
			self.camAcq.put(1)
		self.camSetting = not self.camSetting
		
	def process_beta_image(self, new_image):
		print(new_image.shape[0], new_image.shape[1])
		yIters, xLength = new_image.shape
		binSize = self.binYSize.get()
		magnification = math.floor(self.imageHeight/float(yIters))
		print(self.imageHeight, xLength, yIters, magnification)
		
		newer_image = self.zoomed_image(new_image, yIters, magnification)
		
		self.zoomedSize = newer_image.shape[0]
		print("Image size: {}".format(newer_image.shape))
		return newer_image

	def process_xy_image(self, new_image):
		return new_image
		
	def get_beta_coord(self, event):
        # Check that mouse-click is in image
		self.coords = [event.pos().x(), event.pos().y()]
		mouseY = float(event.pos().y())
		yExtent = self.zoomedSize

		# Image boundaries returned as [[xmin, xmax], [ymin, ymax]]
		view = self.ui.BetaView.getView()
		vRange = view.viewRange()
		yMin, yMax = float(vRange[1][0]), float(vRange[1][1])
		
		scanStartPos = self.ui.EmbeddedScan1D.findChild(PyDMLabel,"ScanStartPosRead")
		scanStopPos = self.ui.EmbeddedScan1D.findChild(PyDMLabel,"ScanStopPosRead")
		scanStepSize = self.ui.EmbeddedScan1D.findChild(PyDMLabel,"ScanStepSizeRead")
		
		motorScanStepSize = float(scanStepSize.text())
		motorScanStartPos = float(scanStartPos.text())
		motorScanStopPos = float(scanStopPos.text())
					
		motorCurrPos = float(self.motorRead.text())
		
		
#		mouseExtent = 480 ## would prefer to get this number programmatically
		mouseExtent = self.ui.BetaView.height()

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
		
	def get_xy_coord(self, event):
		return
