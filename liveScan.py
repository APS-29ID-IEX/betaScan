import time
from os import path
from pydm import Display
from scipy.ndimage.measurements import maximum_position
from scipy.ndimage.interpolation import zoom
from qtpy.QtWidgets import QWidget, QGridLayout, QPushButton
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.label import PyDMLabel
from pydm.widgets.embedded_display import PyDMEmbeddedDisplay
from pydm.widgets.image import PyDMImageView
import math
import epics
import numpy as np

class LiveScan(Display):

	def __init__(self, parent=None, args=None):
		super(LiveScan, self).__init__(parent=parent, args=args)
		
		# Set up scan view image processing and mouse/coordinate interface calls
		self.ui.XYView.mousePressEvent = self.get_coord_xy
		self.ui.XYView.process_image = self.process_xy_image
		self.ui.BetaView.mousePressEvent = self.get_coord_beta
		self.ui.BetaView.process_image = self.process_beta_image

		# Set up live view toggling
		self.ui.liveViewButton.mousePressEvent = self.toggle_liveView

		# Set up scans dictionary
		self.scans = [{'ViewType': 'BetaView', 'Axis': 'Y', 'MotorControls': 'EmbeddedMotor',
					   'Controls': 'EmbeddedScan1D', 'ZoomedSize': 1, 'AxisIndex': 0},
					  {'ViewType': 'XYView', 'Axis': 'X', 'MotorControls': 'EmbeddedMotorInner',
					   'Controls': 'EmbeddedScan2DInner', 'ZoomedSize': 1, 'AxisIndex': 1},
					  {'ViewType': 'XYView', 'Axis': 'Y', 'MotorControls': 'EmbeddedMotorOuter',
					   'Controls': 'EmbeddedScan2DOuter', 'ZoomedSize': 1, 'AxisIndex': 2} ] 

		# Adding behavior to each motor's Move button so that values sent to 
		# PyDMLineEdit programmatically can then be sent onto the motor when 
		# the button is pressed
		self.motorSetObj = []
		for k, emd in enumerate(self.scans):
			embeddedDisplay = self.ui.findChild(PyDMEmbeddedDisplay,emd['MotorControls'])
			self.motorSetObj.append(embeddedDisplay.findChild(PyDMLineEdit,"motorPosSet"))
			motorGo = embeddedDisplay.findChild(QPushButton,"motorMove")
			motorGo.clicked.connect(self.motorSetObj[k].send_value)

		# Setting up image processing
		self.betaZoomedSize = 1
		self.xyZoomedSize = [1,1]

		self.betaImageHeight = 672.0 #Needs to be set programmatically?
		self.xyImageHeight = 672.0 #Needs to be set programmatically?
		
		# Setting up camera trigger PVs
		self.camMode = epics.PV('PelmeniDet:cam1:ImageMode')
		self.camAcq = epics.PV('PelmeniDet:cam1:Acquire')
		self.camSetting = False
		
	def ui_filename(self):
		# Point to UI file
		return 'liveScan.ui'

	def ui_filepath(self):
		# Return the full path to the UI file
		return path.join(path.dirname(path.realpath(__file__)), self.ui_filename())

	def toggle_liveView(self, event):
		if self.camSetting:
			self.camMode.put(0)
			self.camAcq.put(0)
		else:
			self.camMode.put(2)
			self.camAcq.put(1)
		self.camSetting = not self.camSetting

	def zoomed_image(self, new_image, ys, mag):
		new_image = np.asarray(new_image)
		slices = [slice(0, new_image.shape[0], 1/mag)]
		idxs = (np.mgrid[slices]).astype('i')
		return new_image[tuple(idxs)]
		
	def process_beta_image(self, new_image):
		yIters, xLength = new_image.shape
		magnification = math.floor(self.betaImageHeight/float(yIters))
		newer_image = self.zoomed_image(new_image, yIters, magnification)
		self.scans[0]['ZoomedSize'] = newer_image.shape[0]
		return newer_image

	def process_xy_image(self, new_image):
		newer_image = new_image		
#		self.xyZoomedSize = [newer_image.shape[1], newer_image.shape[0]]
		self.scans[1]['ZoomedSize'] = newer_image.shape[1]
		self.scans[2]['ZoomedSize'] = newer_image.shape[0]
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

	def get_coord_xy(self, event):
		# Get x coordinate of mouse-click for XY Scan
		self.get_coord(event, self.scans[1])   
		# Get y coordinate of mouse-click for XY Scan
		self.get_coord(event, self.scans[2])	
	
	def get_coord_beta(self, event):
		# Get beta coordinate of mouse-click for Beta Scan
		self.get_coord(event, self.scans[0])	
	
	def get_coord(self, event, scan):
		scanType = scan["ViewType"]
		scanAxis = scan["Axis"]
		scanControls = scan["Controls"]
		axisIndex = scan["AxisIndex"]
		zoomedSize = scan['ZoomedSize']
	
		# Get mouse click position in imageView widget and set viewIndex
		imageViewer = self.ui.findChild(PyDMImageView,scanType)
		if scanAxis == 'Y':
			mouse_info = [float(event.pos().y()), imageViewer.height()]
			viewIndex = 1
		else:
			mouse_info = [float(event.pos().x()), imageViewer.width()]
			viewIndex = 0
		# Image boundaries returned as [[xmin, xmax], [ymin, ymax]]
		view = imageViewer.getView()
		vRange = view.viewRange()
		image_pos = [float(vRange[viewIndex][0]), float(vRange[viewIndex][1]), zoomedSize]   # <---- TODO generalize indices 
		
		# Get Scan information
		scanEmbeddedDisplay = self.ui.findChild(PyDMEmbeddedDisplay,scanControls)
		scanStartPos = scanEmbeddedDisplay.findChild(PyDMLabel,"ScanStartPosRead")
		scanStopPos = scanEmbeddedDisplay.findChild(PyDMLabel,"ScanStopPosRead")
		scanStepSize = scanEmbeddedDisplay.findChild(PyDMLabel,"ScanStepSizeRead")
		
		motorScanStepSize = float(scanStepSize.text())
		motorScanStartPos = float(scanStartPos.text())
		motorScanStopPos = float(scanStopPos.text())
					
		scan_info = [motorScanStartPos, motorScanStopPos, motorScanStepSize]

		# Convert mouse click position into sample spatial position
		chosenPos = self.mouse_to_spacial(mouse_info, image_pos, scan_info)
	
		# Check that clicked position is within scan limits and if so, 
		# "discretize" position so that it matches up with actual positions of
		# sample during scan and then send to motor's set entry field			
		limits = [motorScanStartPos, motorScanStopPos + motorScanStepSize]
		if ((chosenPos <= max(limits)) and (chosenPos >= min(limits))):
				chosenPos_disc = self.discretize_pos(chosenPos, motorScanStartPos, motorScanStepSize)
				self.motorSetObj[axisIndex].setText(str(chosenPos_disc))			# <---- TODO generalize motorSetObj
	
	
