import time
from os import path
from pydm import Display
from scipy.ndimage.measurements import maximum_position


class BetaScan(Display):

	def __init__(self, parent=None, args=None):
		super(BetaScan, self).__init__(parent=parent, args=args)
		self.ui.imageView.mousePressEvent = self.show_coord

	def ui_filename(self):
		# Point to our UI file
		return 'betaScan.ui'

	def ui_filepath(self):
		# Return the full path to the UI file
		return path.join(path.dirname(path.realpath(__file__)), self.ui_filename())

	def show_coord(self, event):
        # Check that mouse-click is in image
		self.coords = [event.pos().x(), event.pos().y()]
		mouseY = float(event.pos().y())
		yExtent = float(self.ui.ImageYSize.text())

		# Image boundaries returned as [[xmin, xmax], [ymin, ymax]]
		view = self.ui.imageView.getView()
		vRange = view.viewRange()
		yMin, yMax = float(vRange[1][0]), float(vRange[1][1])
		
		motorScanStepSize = float(self.ui.ScanStepSize.text())
		motorScanStartPos = float(self.ui.ScanStartPos.text())
		motorScanStopPos = float(self.ui.ScanStopPos.text())
		
		mouseExtent = 480
		
		chosenY = (1.0 - (mouseY / mouseExtent *(yMax-yMin) + yMin) / yExtent) * (motorScanStartPos - motorScanStopPos) + motorScanStopPos
	
		mouse_txt = "Mouse click at:"
		mouse_txt += " ({}, {})".format(self.coords[0], self.coords[1])
		mouse_txt += "\n Image vertical extent (y_min, y_max): \n"
		mouse_txt += "({}, {})".format(yMin, yMax)

		yPos_txt = "Mouse click converted to y-position of: "
		yPos_txt += " {}".format(chosenY)

		self.ui.MouseLabel.setText(mouse_txt)
		self.ui.TargetLabel.setText(yPos_txt) 
