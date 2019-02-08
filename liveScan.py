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
		self.ui.XYView.mousePressEvent = self.get_coord_xy
		self.ui.XYView.process_image = self.process_xy_image
		self.ui.BetaView.mousePressEvent = self.get_coord_beta
		self.ui.BetaView.process_image = self.process_beta_image

		self.ui.liveViewButton.mousePressEvent = self.toggle_liveView

		self.motor1DRead = self.ui.EmbeddedMotor.findChild(PyDMLabel,"motorPosRead")
		self.motor1DSet = self.ui.EmbeddedMotor.findChild(PyDMLineEdit,"motorPosSet")
		self.motor1DGo = self.ui.EmbeddedMotor.findChild(QPushButton,"motorMove")
		self.motor1DGo.mousePressEvent = self.move_motor_1D

		self.motor2DOuterRead = self.ui.EmbeddedMotorOuter.findChild(PyDMLabel,"motorPosRead")
		self.motor2DOuterSet = self.ui.EmbeddedMotorOuter.findChild(PyDMLineEdit,"motorPosSet")
		self.motor2DOuterGo = self.ui.EmbeddedMotorOuter.findChild(QPushButton,"motorMove")
		self.motor2DOuterGo.mousePressEvent = self.move_motor_2DOuter

		self.motor2DInnerRead = self.ui.EmbeddedMotorInner.findChild(PyDMLabel,"motorPosRead")
		self.motor2DInnerSet = self.ui.EmbeddedMotorInner.findChild(PyDMLineEdit,"motorPosSet")
		self.motor2DInnerGo = self.ui.EmbeddedMotorInner.findChild(QPushButton,"motorMove")
		self.motor2DInnerGo.mousePressEvent = self.move_motor_2DInner

		self.betaZoomedSize = 1
		self.xyZoomedSize = [1,1]

		self.betaImageHeight = 672.0 #Needs to be set programmatically?
		self.xyImageHeight = 672.0 #Needs to be set programmatically?
		
		self.camMode = epics.PV('PelmeniDet:cam1:ImageMode')
		self.camAcq = epics.PV('PelmeniDet:cam1:Acquire')
		self.camSetting = False
		
	def ui_filename(self):
		# Point to UI file
		return 'liveScan.ui'

	def ui_filepath(self):
		# Return the full path to the UI file
		return path.join(path.dirname(path.realpath(__file__)), self.ui_filename())

	def move_motor_1D(self, event):
		self.motor1DSet.send_value()

	def move_motor_2DInner(self, event):
		self.motor2DInnerSet.send_value()

	def move_motor_2DOuter(self, event):
		self.motor2DOuterSet.send_value()

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
		yIters, xLength = new_image.shape
		magnification = math.floor(self.betaImageHeight/float(yIters))
		newer_image = self.zoomed_image(new_image, yIters, magnification)
		self.zoomedSize = newer_image.shape[0]
		return newer_image

	def process_xy_image(self, new_image):
		newer_image = new_image		
		self.xyZoomedSize = [newer_image.shape[1], newer_image.shape[0]]
		return newer_image

	def mouse_to_spacial(self, mouse, image, scan):
		chosen_pos = ((1.0 - (mouse[0] / mouse[1] * (image[1] - 
					image[0]) + image[0]) / image[2]) * (scan[0] - 
					(scan[1] + scan[2])) + scan[1] +
					scan[2])
		return chosen_pos

	def discretize_pos(self, chosen_pos, scanStartPos, scanStepSize):
		steps = (math.floor((chosen_pos - scanStartPos)/scanStepSize))
		disc_pos = steps * scanStepSize + scanStartPos
		return disc_pos

	def get_coord_beta(self, event):
		# Get mouse click position in imageView widget
		mouse_info = [float(event.pos().y()), self.ui.BetaView.height()]

		# Image boundaries returned as [[xmin, xmax], [ymin, ymax]]
		view = self.ui.BetaView.getView()
		vRange = view.viewRange()
		image_pos = [float(vRange[1][0]), float(vRange[1][1]), self.zoomedSize]
		
		# Get Scan information
		scanStartPos = self.ui.EmbeddedScan1D.findChild(PyDMLabel,"ScanStartPosRead")
		scanStopPos = self.ui.EmbeddedScan1D.findChild(PyDMLabel,"ScanStopPosRead")
		scanStepSize = self.ui.EmbeddedScan1D.findChild(PyDMLabel,"ScanStepSizeRead")
		
		motorScanStepSize = float(scanStepSize.text())
		motorScanStartPos = float(scanStartPos.text())
		motorScanStopPos = float(scanStopPos.text())
					
		motorCurrPos = float(self.motor1DRead.text())

		scan_info = [motorScanStartPos, motorScanStopPos, motorScanStepSize]

		# Convert mouse click position into sample spatial position
		chosenY = self.mouse_to_spacial(mouse_info, image_pos, scan_info)
	
		# Check that clicked position is within scan limits and if so, 
		# "discretize" position so that it matches up with actual positions of
		# sample during scan and then send to motor's set entry field			
		limits = [motorScanStartPos, motorScanStopPos + motorScanStepSize]
		if ((chosenY <= max(limits)) and (chosenY >= min(limits))):
				chosenY_disc = self.discretize_pos(chosenY, motorScanStartPos, motorScanStepSize)
				self.motor1DSet.setText(str(chosenY_disc))
			
#		print("****************************************************************")
#		print("mouseY, mouseExtent: {}, {}".format(mouseY, mouseExtent))
#		print("yMin, yMax, yExtent: {}, {}, {}".format(yMin, yMax, yExtent))
#		print("motor scan start, stop, step: {}, {}, {}".format(motorScanStartPos, motorScanStopPos, motorScanStepSize))
#		print("chosenY, limits: {}, {}".format(chosenY, limits))


	def get_coord_xy(self, event):
		# Get mouse click position in imageView widget
		mouseX_info = [float(event.pos().x()), self.ui.XYView.width()]
		mouseY_info = [float(event.pos().y()), self.ui.XYView.height()]

		# Image boundaries returned as [[xmin, xmax], [ymin, ymax]]
		view = self.ui.XYView.getView()
		vRange = view.viewRange()
		imageX_pos = [float(vRange[0][0]), float(vRange[0][1]), self.xyZoomedSize[0]]
		imageY_pos = [float(vRange[1][0]), float(vRange[1][1]), self.xyZoomedSize[1]]

		# Get Scan information		
		xScanStartPos = self.ui.EmbeddedScan2DInner.findChild(PyDMLabel,"ScanStartPosRead")
		xScanStopPos = self.ui.EmbeddedScan2DInner.findChild(PyDMLabel,"ScanStopPosRead")
		xScanStepSize = self.ui.EmbeddedScan2DInner.findChild(PyDMLabel,"ScanStepSizeRead")
	
		xMotorScanStepSize = float(xScanStepSize.text())
		xMotorScanStartPos = float(xScanStartPos.text())
		xMotorScanStopPos = float(xScanStopPos.text())

		yScanStartPos = self.ui.EmbeddedScan2DOuter.findChild(PyDMLabel,"ScanStartPosRead")
		yScanStopPos = self.ui.EmbeddedScan2DOuter.findChild(PyDMLabel,"ScanStopPosRead")
		yScanStepSize = self.ui.EmbeddedScan2DOuter.findChild(PyDMLabel,"ScanStepSizeRead")
	
		yMotorScanStepSize = float(yScanStepSize.text())
		yMotorScanStartPos = float(yScanStartPos.text())
		yMotorScanStopPos = float(yScanStopPos.text())
					
		xMotorCurrPos = float(self.motor2DInnerRead.text())
		yMotorCurrPos = float(self.motor2DOuterRead.text())

		#Inner scan (scanX) needs to be treated differently in order to handle
		#snake scans where the start/stop/step are changed for each line. By 
		#setting start to the min of actual start and stop (and similarly for 
		#the start) and taking the abs. value of step, the coordinate system
		#is kept unambiguous.
		scanX_info = [min([xMotorScanStartPos, xMotorScanStopPos]), 
					  max([xMotorScanStartPos, xMotorScanStopPos]), 
					  abs(xMotorScanStepSize)]
		scanY_info = [yMotorScanStartPos, yMotorScanStopPos, yMotorScanStepSize]

		# Convert mouse click position into sample spatial position
		chosenX = self.mouse_to_spacial(mouseX_info, imageX_pos, scanX_info)
		chosenY = self.mouse_to_spacial(mouseY_info, imageY_pos, scanY_info)

		# Check that clicked position is within scan limits and if so, 
		# "discretize" position so that it matches up with actual positions of
		# sample during scan and then send to motor's set entry field
		xLimits	= [scanX_info[0], scanX_info[1] + scanX_info[2]]		
		yLimits = [scanY_info[0], scanY_info[1] + scanY_info[2]]
		if ((chosenY <= max(yLimits)) and (chosenY >= min(yLimits)) and (chosenX <= max(xLimits)) and (chosenX >= min(xLimits))):
				chosenX_disc = self.discretize_pos(chosenX, scanX_info[0], scanX_info[2])
				chosenY_disc = self.discretize_pos(chosenY, yMotorScanStartPos, yMotorScanStepSize)
				self.motor2DInnerSet.setText(str(chosenX_disc))
				self.motor2DOuterSet.setText(str(chosenY_disc))
