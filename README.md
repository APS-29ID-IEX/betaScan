# PyDM tests

Initial test were with a beta scan only:
 - betaScan.ui - Test setup for control of a betaScan on the 29ID's Scienta
 - betaScan.py - Code to support some extra functionality in betaScan.ui
 - scan_control_inline.ui - small display for scan record control, meant to be embedded in betaScan.ui
 - motor_inline.ui - small display for motor, meant to be embedded in betaScan.ui
 - hv_inline.ui - small display for choosing pixel and bin width for beta scans

Added tabs, live view, and XY scan:
 - liveScan.ui - Test setup for control of beta and xy scans of 29ID's Scienta
 - liveScan.py - Code to support added functionality (zooming, setting motor location via mouse)
 - hv_stack.ui - small display for choosing pixel and bin width for beta scans 
 - motor_stack.ui - small display for motor control, meant to be embedded in liveScan.ui 
 - scan_1D_control_stack.ui - small display for a single axis scan record control, meant to be embedded in liveScan.ui
