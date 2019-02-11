import time
from os import path
from pydm import Display
from scipy.ndimage.measurements import maximum_position
from scipy.ndimage.interpolation import zoom
from qtpy.QtWidgets import QWidget, QGridLayout, QPushButton
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.label import PyDMLabel
from pydm.widgets.embedded_display import PyDMEmbeddedDisplay
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

		# Adding behavior to each motor's Move button so that values sent to 
		# PyDMLineEdit programmatically can then be sent onto the motor when 
		# the button is pressed
		embeddedMotorDisplays = ['EmbeddedMotor', 'EmbeddedMotorOuter', 'EmbeddedMotorInner']
		self.motorSetObj = []
		for k, emd in enumerate(embeddedMotorDisplays):
			embeddedDisplay = self.ui.findChild(PyDMEmbeddedDisplay,emd)
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
		
		# Set up scans dictionary
		self.scans = [{"ViewType": 'BetaView', "Axis": 'Y', "Controls": 'EmbeddedScan1D', 'ZoomedSize': 1},
					   "ViewType": 'XYView', "Axes": 'X', "Controls": 'EmbeddedScan2DInner', 'ZoomedSize': 1},
					   "ViewType": 'XYView', "Axes": 'Y', "Controls": 'EmbeddedScan2DOuter', 'ZoomedSize': 1} ] 
		
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
					
		scan_info = [motorScanStartPos, motorScanStopPos, motorScanStepSize]

		# Convert mouse click position into sample spatial position
		chosenY = self.mouse_to_spacial(mouse_info, image_pos, scan_info)
	
		# Check that clicked position is within scan limits and if so, 
		# "discretize" position so that it matches up with actual positions of
		# sample during scan and then send to motor's set entry field			
		limits = [motorScanStartPos, motorScanStopPos + motorScanStepSize]
		if ((chosenY <= max(limits)) and (chosenY >= min(limits))):
				chosenY_disc = self.discretize_pos(chosenY, motorScanStartPos, motorScanStepSize)
				self.motorSetObj[0].setText(str(chosenY_disc))
			
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
		view = self.ui.XYView.getView()				# <--- generalize here
		vRange = view.viewRange()
		imageX_pos = [float(vRange[0][0]), float(vRange[0][1]), self.xyZoomedSize[0]]
		imageY_pos = [float(vRange[1][0]), float(vRange[1][1]), self.xyZoomedSize[1]]

		# Get Scan information		
		xScanStartPos = self.ui.EmbeddedScan2DInner.findChild(PyDMLabel,"ScanStartPosRead")		# <--- generalize here
		xScanStopPos = self.ui.EmbeddedScan2DInner.findChild(PyDMLabel,"ScanStopPosRead")		# <--- generalize here
		xScanStepSize = self.ui.EmbeddedScan2DInner.findChild(PyDMLabel,"ScanStepSizeRead")		# <--- generalize here
	
		xMotorScanStepSize = float(xScanStepSize.text())
		xMotorScanStartPos = float(xScanStartPos.text())
		xMotorScanStopPos = float(xScanStopPos.text())

		yScanStartPos = self.ui.EmbeddedScan2DOuter.findChild(PyDMLabel,"ScanStartPosRead")		# <--- generalize here
		yScanStopPos = self.ui.EmbeddedScan2DOuter.findChild(PyDMLabel,"ScanStopPosRead")		# <--- generalize here
		yScanStepSize = self.ui.EmbeddedScan2DOuter.findChild(PyDMLabel,"ScanStepSizeRead")		# <--- generalize here
	
		yMotorScanStepSize = float(yScanStepSize.text())
		yMotorScanStartPos = float(yScanStartPos.text())
		yMotorScanStopPos = float(yScanStopPos.text())
					
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
				self.motorSetObj[2].setText(str(chosenX_disc))
				self.motorSetObj[1].setText(str(chosenY_disc))


# Starting to write a single get_coord function, will require

	def get_coord_xy(self, event):
		# Get x coordinate of mouse-click for XY Scan
		get_coord(self, event, self.scans[1])   
		# Get y coordinate of mouse-click for XY Scan
		get_coord(self, event, self.scans[2])	
	
	def get_coord_beta(self, event):
		# Get beta coordinate of mouse-click for Beta Scan
		get_coord(self, event, self.scans[0])	
	
	def get_coord(self, event, scan):
		scanType = scan["ViewType"]
		scanAxes = scan["Axes"]
		scanControls = scan["Controls"]
		zoomedSize = scan['ZoomedSize']
		
		# Get mouse click position in imageView widget
		imageViewer = self.ui.findChild(PyDMImageView,scanType)
		if scanAxes = 'Y':
			mouse_info = [float(event.pos().y()), imageViewer.height()]
		else
			mouse_info = [float(event.pos().x()), imageViewer.width()]
			
		# Image boundaries returned as [[xmin, xmax], [ymin, ymax]]
		view = imageViewer.getView()
		vRange = view.viewRange()
		image_pos = [float(vRange[1][0]), float(vRange[1][1]), zoomedSize]   # <---- TODO generalize indices 
		
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
				self.motorSetObj[0].setText(str(chosenPos_disc))			# <---- TODO generalize motorSetObj
	
	
