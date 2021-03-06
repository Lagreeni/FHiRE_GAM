#
# Updated: 05/17/2021
#

import logging, time, sys, threading, io, os
import PyIndi
from PyQt5 import QtCore,QtWidgets
from PyQt5.QtCore import QThread,pyqtSignal

# Inherits from module PyIndi.BaseClient class.
class IndiClient(PyIndi.BaseClient):
# CLASS IndiClient FUNCTIONS.
	def __init__(self):
		super(IndiClient, self).__init__()
	def newDevice(self, d):  # called when new device is detected
		pass
	def newProperty(self,p):
		pass
	def removeProperty(self, p):
		pass
	def newBLOB(self, bp): 
		self.blobEvent.set()
		pass
	def newSwitch(self, svp):
		pass
	def newNumber(self, nvp): 
		pass
	def newText(self, tvp):
		pass
	def newLight(self, lvp):
		pass
	def newMessage(self, d, m):
        	pass
	def serverConnected(self):	
		pass
	def serverDisconnected(self, code):
		pass

#====================================================================================#
# ----------------------------- Client Thread -------------------------------------
#====================================================================================#
class IndiConnection(QtCore.QObject): 
	sig = [pyqtSignal(int) for i in range(4)]	
	sig_filter_start, sig_abort, sig_exp, sig_mycen = sig[0:]
	
	sig_path = pyqtSignal(str)	

	sig_config_start = pyqtSignal('PyQt_PyObject')
	sig_temp = pyqtSignal('PyQt_PyObject')
	sig_config = pyqtSignal('PyQt_PyObject')
	sig_filter = pyqtSignal('PyQt_PyObject')

	def __init__(self, regionpath, parent=None):
		self.regionpath = regionpath
		self.abort = None
		super(IndiConnection, self).__init__(parent)
		self.wheel = "QHYCFW2"
		self.dwheel         = None
		self.connect_dwheel = None
		self.slot_dwheel    = None

		self.camera = "ZWO CCD ASI174MM-Cool"
		self.dcamera           = None
		self.connect_dcamera   = None
		self.cpower_dcamera    = None
		self.cool_dcamera      = None
		self.temp_dcamera      = None
		self.binning_dcamera   = None
		self.frame_dcamera     = None
		self.frametype_dcamera = None
		self.controls_dcamera  = None
		self.bit_dcamera       = None
		self.expose_dcamera    = None
		self.abort_dcamera     = None
		self.blob_dcamera      = None

		# Starts an exposure progress thread.
		self.p = threading.Thread(target=self.time_start)
		self.p.setDaemon(True)
		self.p.start()

#==================================================
# Connect to server, devices, indi properties. ====
#==================================================
	def run(self):
		# Connect to INDI server.
		start = time.time()
		time.sleep(1)
		self.indiclient = IndiClient()
		self.indiclient.setServer("localhost",7624) 
		print("Connecting...")
		self.indiclient.connectServer() 

		# Connect to filterwheel.
		time.sleep(0.5)
		self.dwheel = self.indiclient.getDevice(self.wheel)

		time.sleep(0.5)
		self.connect_dwheel = self.dwheel.getSwitch("CONNECTION")

		time.sleep(0.5)
		while not(self.dwheel.isConnected()): 
			self.connect_dwheel[0].s = PyIndi.ISS_ON 
			self.connect_dwheel[1].s = PyIndi.ISS_OFF
			self.indiclient.sendNewSwitch(self.connect_dwheel) 
			print("Connecting QHY CFW2-S (Filterwheel)")
			time.sleep(1)

		time.sleep(1)
		if(self.dwheel.isConnected()):
			print("Connected: QHY CFW2-S (Filterwheel)")
		if not(self.dwheel.isConnected()):
			print("Disconnected: QHY CFW2-S (Filterwheel)")

		# Connect FILTER_SLOT - filter wheel's current slot number.
		self.slot_dwheel = self.dwheel.getNumber("FILTER_SLOT")
		if not(self.slot_dwheel):	
			print("property setup ERROR: FILTER_SLOT")

		# Connect to camera.
		time.sleep(0.5)
		self.dcamera = self.indiclient.getDevice(self.camera)

		time.sleep(0.5)
		self.connect_dcamera = self.dcamera.getSwitch("CONNECTION")

		time.sleep(1)
		if not(self.dcamera.isConnected()): 
			self.connect_dcamera[0].s = PyIndi.ISS_ON
			self.connect_dcamera[1].s = PyIndi.ISS_OFF
			self.indiclient.sendNewSwitch(self.connect_dcamera) 
			print("Connecting (Guide Camera)")

		time.sleep(1)
		if(self.dcamera.isConnected()):
			print("Connected: ZWO CCD (Guide Camera)")
		if not(self.dcamera.isConnected()):
			print("Disconnected: ZWO CCD (Guide Camera)")

		# Connect CCD_COOLER - toggle cooler.
		self.cool_dcamera = self.dcamera.getSwitch("CCD_COOLER")
		if not(self.cool_dcamera):	
			print("property setup ERROR: CCD_COOLER")

		# Connect CCD_CONTROLS - offset, gain, bandwidth, binning.
		self.controls_dcamera = self.dcamera.getNumber("CCD_CONTROLS")
		if not(self.controls_dcamera):	
			print("property setup ERROR: CCD_CONTROLS")

		# Connect CCD_BINNING - horizontal/vertical binning.
		self.binning_dcamera = self.dcamera.getNumber("CCD_BINNING")
		if not(self.binning_dcamera):
			print("property setup ERROR: CCD_BINNING")

		# Connect CCD_FRAME_TYPE - light, bias, dark, flat.
		self.frametype_dcamera = self.dcamera.getSwitch("CCD_FRAME_TYPE")
		if not(self.frametype_dcamera):
			print("property setup ERROR: CCD_FRAME_TYPE")

		# Connect CCD_FRAME - frame dimensions.
		self.frame_dcamera = self.dcamera.getNumber("CCD_FRAME")
		if not(self.frame_dcamera):
			print("property setup ERROR: CCD_FRAME")

		# Connect CCD_TEMPERATURE - chip temp. in Celsius.
		self.temp_dcamera = self.dcamera.getNumber("CCD_TEMPERATURE")
		if not(self.temp_dcamera):	
			print("property setup ERROR: CCD_TEMPERATURE")

		# Connect CCD_EXPOSURE - seconds of exposure.
		self.expose_dcamera = self.dcamera.getNumber("CCD_EXPOSURE")
		if not(self.expose_dcamera):	
			print("property setup ERROR: CCD_EXPOSURE")	

		# Connect CCD1 - binary fits data encoded in base64.
		# Inform indi server to receive the "CCD1" blob from this device.
		self.indiclient.setBLOBMode(PyIndi.B_ALSO, self.camera, "CCD1")
		time.sleep(0.5)
		self.blob_dcamera = self.dcamera.getBLOB("CCD1")
		if not(self.blob_dcamera):
			print("property setup ERROR: CCD1 -- BLOB")

		# Connect CCD_COOLER_POWER - percentage cooler power utilized.
		self.cpower_dcamera = self.dcamera.getNumber("CCD_COOLER_POWER")
		if not(self.cpower_dcamera):
			print("property setup ERROR: CCD_COOLER_POWER")

		# Connect CCD_ABORT_EXPOSURE - abort CCD exposure.
		self.abort_dcamera = self.dcamera.getSwitch(
						"CCD_ABORT_EXPOSURE")	
		if not(self.abort_dcamera):
			print("property setup ERROR: CCD_ABORT_EXPOSURE")

		# Connect CCD_VIDEO_FORMAT - change bits per pixel.
		self.bit_dcamera = self.dcamera.getSwitch("CCD_VIDEO_FORMAT")
		if not(self.bit_dcamera):
			print("property setup ERROR: CCD_VIDEO_FORMAT")
		
		# Set up thread for creating the blob.
		self.indiclient.blobEvent = threading.Event() 
		self.indiclient.blobEvent.clear()

		self.event = threading.Event()
		self.event.clear()

		time.sleep(1)
		end = time.time()

		print ("*** Connection process complete ***\n"
		       "Time elapsed: %.2f seconds" %(end - start))

#========================================================
# Receive default properties and send to MainUiClass ====
#========================================================
		
		# Set cooler radiobutton default.
		cool = 0 if self.cool_dcamera[0].s == PyIndi.ISS_ON else 1

		# Set frame type radiobutton default.
		frametype = {
			self.frametype_dcamera[0].s:0, 
			self.frametype_dcamera[1].s:1, 
			self.frametype_dcamera[2].s:2, 
			self.frametype_dcamera[3].s:3}

		for x in frametype:
			if x == PyIndi.ISS_ON:
				typ = frametype[x]
	
		# Set default filter slot default value .
		slot = self.slot_dwheel[0].value - 1

		# Set default bit value .
		if(self.bit_dcamera[0].s == PyIndi.ISS_ON):
			bit = 8
		elif(self.bit_dcamera[1].s == PyIndi.ISS_ON):
			bit = 16

		# Send current values to MainUiClass.
		self.sig_filter_start.emit(slot)
		self.sig_config_start.emit([cool, typ, bit])	

		self.stop_thread = False		

		while True:
			# ZWO temperature/cooling.
			temp = self.get_temp()
			cpower = self.get_cooler_power()
			ctoggle = self.cooler_status()
			self.sig_temp.emit([temp, cpower, ctoggle])

			# ZWO configurations.
			xbin = self.binning_dcamera[0].value
			ybin = self.binning_dcamera[1].value

			gain   = self.controls_dcamera[0].value
			offset = self.controls_dcamera[1].value
			band   = self.controls_dcamera[2].value
	
			xposition = self.frame_dcamera[0].value  # left
			yposition = self.frame_dcamera[1].value  # top
			xframe    = self.frame_dcamera[2].value  # x
			yframe    = self.frame_dcamera[3].value  # y

			self.sig_config.emit([
				xbin, ybin, gain, offset, band,
				xposition, yposition, xframe, yframe])

			# Filterwheel indicator. 
			busy = self.filter_busy()
			self.sig_filter.emit(busy)

			if self.stop_thread == True:
				print("client thread break")
				break

			time.sleep(1) 

#==========================
# Functionalities =========
#==========================

	# Abort exposure.
	def abort_exposure(self):
		print("Aborting exposure...")
		self.abort_dcamera[0].s = PyIndi.ISS_ON
		self.indiclient.sendNewSwitch(self.abort_dcamera)
		#
		# Sending random exposure time to camera to 
		# interrupt the last blobEvent. Otherwise,
		# it gets stuck in its wait() method and doesn't
		# clear properly. Adds a delay though.
		#
		self.expose_dcamera[0].value = 1
		self.indiclient.sendNewNumber(self.expose_dcamera)
		self.abort = True
		self.sig_abort.emit(self.abort)

	# Retrievable method by TempThread -- Get current temperature.
	def get_temp(self):
		temp = self.temp_dcamera[0].value
		return temp

	# Retrievable method by TempThread -- Get current cooler power.
	def get_cooler_power(self):
		cpower = self.cpower_dcamera[0].value
		return cpower

	# Retrievable method by FilterThread -- Get status of filterwheel.
	def filter_busy(self):
		busy = False
		if(self.slot_dwheel.s == PyIndi.IPS_BUSY):
			busy = True
		if(self.slot_dwheel.s == PyIndi.IPS_OK):
			busy = False
		return busy

	# Change filter slot.
	def change_filter(self, slot):
		# Why do you send the wheel home each time?
		self.slot_dwheel[0].value = 1  
		self.indiclient.sendNewNumber(self.slot_dwheel)
		self.slot_dwheel[0].value = slot + 1
		time.sleep(0.01)
		self.indiclient.sendNewNumber(self.slot_dwheel)
		#time.sleep(0.01)

	# Turn cooler on.
	def cooler_toggle(self, on):
		if on == True:
			self.cool_dcamera[0].s = PyIndi.ISS_ON
			self.cool_dcamera[1].s = PyIndi.ISS_OFF
		else: 
			self.cool_dcamera[0].s = PyIndi.ISS_OFF
			self.cool_dcamera[1].s = PyIndi.ISS_ON	
		self.indiclient.sendNewSwitch(self.cool_dcamera)

	def cooler_status(self):
		if self.cool_dcamera[0].s == PyIndi.ISS_ON:
			on = True
		elif self.cool_dcamera[1].s == PyIndi.ISS_ON:
			on = False
		return on

	# Change bandwidth.
	def update_band(self, band):
		self.controls_dcamera[2].value = band
		self.indiclient.sendNewNumber(self.controls_dcamera)

	# Change x binning.
	def update_xbin(self, xbin):
		self.binning_dcamera[0].value = xbin
		self.indiclient.sendNewNumber(self.controls_dcamera)

	# Change y binning.
	def update_ybin(self, ybin):
		self.binning_dcamera[1].value = ybin
		self.indiclient.sendNewNumber(self.controls_dcamera)

	# Change offset.
	def update_offset(self, offset):
		self.controls_dcamera[1].value = offset
		self.indiclient.sendNewNumber(self.controls_dcamera)

	# Change gain.
	def update_gain(self, gain):
		self.controls_dcamera[0].value = gain
		self.indiclient.sendNewNumber(self.controls_dcamera)

	# Set bit/pixel.
	def bit(self, pixel):
		if pixel == 8:
			self.bit_dcamera[1].s = PyIndi.ISS_OFF
			self.bit_dcamera[0].s = PyIndi.ISS_ON
		elif pixel == 16:
			self.bit_dcamera[1].s = PyIndi.ISS_ON
			self.bit_dcamera[0].s = PyIndi.ISS_OFF
		self.indiclient.sendNewSwitch(self.bit_dcamera)

	# Set frametype --- (could have also passed a value).
	def frametype_light(self):
		self.frametype_dcamera[0].s = PyIndi.ISS_ON
		self.frametype_dcamera[1].s = PyIndi.ISS_OFF
		self.frametype_dcamera[2].s = PyIndi.ISS_OFF
		self.frametype_dcamera[3].s = PyIndi.ISS_OFF
		self.indiclient.sendNewSwitch(self.frametype_dcamera)

	def frametype_bias(self):
		self.frametype_dcamera[0].s = PyIndi.ISS_OFF
		self.frametype_dcamera[1].s = PyIndi.ISS_ON
		self.frametype_dcamera[2].s = PyIndi.ISS_OFF
		self.frametype_dcamera[3].s = PyIndi.ISS_OFF
		self.indiclient.sendNewSwitch(self.frametype_dcamera)

	def frametype_dark(self):
		self.frametype_dcamera[0].s = PyIndi.ISS_OFF
		self.frametype_dcamera[1].s = PyIndi.ISS_OFF
		self.frametype_dcamera[2].s = PyIndi.ISS_ON
		self.frametype_dcamera[3].s = PyIndi.ISS_OFF
		self.indiclient.sendNewSwitch(self.frametype_dcamera)

	def frametype_flat(self):
		self.frametype_dcamera[0].s = PyIndi.ISS_OFF
		self.frametype_dcamera[1].s = PyIndi.ISS_OFF
		self.frametype_dcamera[2].s = PyIndi.ISS_OFF
		self.frametype_dcamera[3].s = PyIndi.ISS_ON
		self.indiclient.sendNewSwitch(self.frametype_dcamera)
	
	# Set frame size - *send array rather than create a function 
	# for each variable.*
	def update_xposition(self, xposition):
		self.frame_dcamera[0].value = xposition
		self.indiclient.sendNewNumber(self.frame_dcamera)

	def update_yposition(self, yposition):
		self.frame_dcamera[2].value = yposition
		self.indiclient.sendNewNumber(self.frame_dcamera)

	def update_xframe(self, xframe):
		self.frame_dcamera[2].value = xframe
		self.indiclient.sendNewNumber(self.frame_dcamera)

	def update_yframe(self, yframe):
		self.frame_dcamera[3].value = yframe
		self.indiclient.sendNewNumber(self.frame_dcamera)

	# Change temperature.
	def change_temp(self, temp):
		try:
			self.temp_dcamera[0].value = float(temp)
			self.indiclient.sendNewNumber(self.temp_dcamera)
		except:
			if temp == '':
				self.cooler_toggle(False)
			else:
				print("Invalid ZWO temperature set.")

	# Take exposure.
	def take_exposure(self):
		start = time.time()
		print("Beginning exposure.")
	
		while(self.num_exp > 0):
			self.expose_dcamera[0].value = float(self.exp)
			self.event.set()
			self.indiclient.sendNewNumber(self.expose_dcamera)

			self.indiclient.blobEvent.wait()
			self.indiclient.blobEvent.clear()

			if self.abort == True:
				self.abort = False
				print("Exposure aborted.")
				break		
			
			for blob in self.blob_dcamera:
				fits = blob.getblobdata()
				blobfile = io.BytesIO(fits)

				# Set image prefix and directory path.
				self.complete_path = self.file_path+"/"+self.file_name+"1.fit"

				# Increment the images.
				if self.autosave == True:
					print("Autosave is on.")
					if os.path.exists(self.complete_path): 
						expand = 1
						while True:
							expand += 1
							new_file_name = self.complete_path.split('1.fit')[0]+str(expand)+".fit"
							if os.path.exists(new_file_name):
								continue
							else:
								self.complete_path = new_file_name
								break
				elif self.autosave == False:
					self.complete_path = '/home/fhire/Desktop/GAMimage_temp.fit'

				with open(self.complete_path, "wb") as f:
					f.write(blobfile.getvalue())

				#
				# Save the regions in case changed, open new image 
				# in ds9 and overlay the saved region box. 
				# **Does it replace the old image?** 
				# Load moved region box if just completed an offset.
				#

				#if self.main.offset_complete == False:
				#	os.system('xpaset -p ds9 regions save '+self.regionpath)
				os.system('xpaset -p ds9 fits '+str(self.complete_path))
				os.system('xpaset -p ds9 zoom to fit')
				os.system('xpaset -p ds9 regions load '+self.regionpath)
				os.system('xpaset -p ds9 zscale')

			print("Image Saved: %s" %self.complete_path)
			self.num_exp -= 1
			self.sig_path.emit(self.complete_path)
			end = time.time()
			print("Total time elapsed: %.2f" %(end - start))
			QtWidgets.QApplication.processEvents()

			if self.autoguide == True:
				print("Sending to centroid")
				self.sig_mycen.emit(False)
			

		time.sleep(1)

	# Separate exposure thread.
	def thread(self, exp, num_exp, file_path, file_name, autosave, autoguide):
		self.num_exp = num_exp
		self.file_path = file_path
		self.file_name = file_name
		self.exp = exp
		self.autosave = autosave
		self.autoguide = autoguide

		# Catch if no or an invalid exposure time is set.
		try:
			self.exp = float(exp)
		except:
			self.exp = 0

		if self.exp > 0:
			self.t = threading.Thread(target=self.take_exposure)
			self.t.setDaemon(True)
			#print(self.t, self.t.is_alive())
			self.t.start()
		else:
			print("Invalid exposure time set.")

	# Retrievable method by FilterThread -- status of exposure.
	def exp_busy(self):
		if(self.expose_dcamera.s == PyIndi.IPS_BUSY):
			busy = True
		elif(self.expose_dcamera.s == PyIndi.IPS_OK):
			busy = False
		return busy

	# Update remaining time, progress bar and exposure count **Set to only update when exposing.**
	def time_start(self):
		time.sleep(10)
		print("Ready to begin taking exposures")
		while 1:
			self.event.wait()
			time.sleep(0.5)
			self.event.clear()
			start = True
			self.sig_exp.emit(start)

	def stop(self):
		self.cooler_toggle(False)
		self.stop_thread = True

