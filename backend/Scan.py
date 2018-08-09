'''
A class that performs tracking and drift scans
with parameters acquired from the scan queue.

Author: Nathan Rowley
Date: June 2018
'''

import CommandStation
from astropy import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy.table import Table
from datetime import date
import io
import ntplib
import sqlite3


NTP_SERVER = 'ntp.carleton.edu'		# NTP server for time retrieval. Change to suit your needs

class Scan:

	def __init__(self):
		self.station = CommandStation()

	'''
	Method to take a single data point at a single frequency for a single source.

	:param azal: tuple containing azimuth and altitude of scan position
	:param freq: frequency in MHz at which to measure
	:return scan: tuple containing a single power measurement and boolean indicating successful movement
	'''
	def singlescan(self, azal, freq) -> tuple:

		movesuccess = self.station.movebyazal(azal[0], azal[1])		# move station to scan position

		if movesuccess:

			scan = self.station.readpower(freq)			# read power at frequency freq

		else:

			scan = 0

		return (scan, movesuccess)

	'''
	Method to take data points across a spectrum for a single source.

	:param azal: tuple containing azimuth and altitude of scan position
	:param flimit: tuple containing lower and upper frequency limits in MHz
	:param step: float containing frequency step quantity in MHz
	:return data: dictionary containing a single spectrum with start and end times and a time correction value
	'''
	def singlespectrum(azal, flimit, step) -> dict:

		spectrum = []

		starttime = getcurrenttime()			# get start time of spectrum scan

		spectrumsuccess = True

		for freq in range(flimit[0], flimit[1], step):		# sweep through frequencies in range with step size step

			if spectrumsuccess:

				scan = singlescan(azal, freq)		# do single scan at current frequency

				if scan[1] == False:

					spectrumsuccess = False

			else:

				scan = (0, False)

			spectrum.append(scan[0])	# append scan result to spectrum

		endtime = getcurrenttime()		# get end time of spectrum scan

		data = {'spectrum': spectrum, 'starttime': starttime, 'endtime': endtime, 'spectrumsuccess': spectrumsuccess}		# package spectrum and time data

		return data

	'''
	Method to track a position and take data for a specific duration.

	:param scanid: the id of the current scan
	:param pos: tuple containing galactic latitude and longitude of the position to track
	:param flimit: tuple containing lower and upper frequency limits in MHz
	:param step: float containing frequency step quantity in MHz
	:param time: unix time at which to stop scanning
	:return trackdata: tuple containing a list of scan data and a string indicating the status of the scan
	'''
	def track(scanid, pos, flimit, step, time) -> tuple:

		srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		curtime = getcurrenttime()		# get start time of scan

		trackdata = []

		while curtime < time:						# continue scanning until current time is past the end time

			status = cur.execute("SELECT * FROM SCANIDS WHERE ID = ?", (scanid,)).fetchone()		# check current status to see if scan was cancelled

			if status['status'] == 'cancelled':		# if scan was cancelled, return data collected so far

				srtdb.close()

				return (trackdata, 'cancelled')

			azal = getazal(pos)						# get current azimuth and altitude of tracked position

			if azal == 'positionerror' or azal == 'moveboundserror':	# check for invalid position or movement, return if found

				srtdb.close()

				return (trackdata, azal)

			spectrumdata = singlespectrum(azal, flimit, step)		# take a spectrum measurement

			trackdata.append(spectrumdata)							# append spectrum data to the scan

			if spectrumdata['spectrumsuccess'] == False:

				srtdb.close()

				return (tackdata, 'timeout')

			curtime = getcurrenttime()			# update current time

		srtdb.close()

		return (trackdata, 'complete')

	'''
	Method to take data at a single drift position for a specific duration.

	:param scanid: the id of the current scan
	:param pos: tuple containing galactic latitude and longitude of drift position
	:param flimit: tuple containing lower and upper frequency limits in MHz
	:param step: float containing frequency step quantity in MHz
	:param time: unix time at which to stop scanning
	:return driftdata: tuple containing a list of scan data and a string indicating the status of the scan
	'''
	def drift(scanid, pos, flimit, step, time) -> tuple:

		srtdb = sqlite3.connect('srtdata.db')			# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		curtime = getcurrenttime()			# get start time of scan

		driftdata = []

		azal = getazal(pos)			# get azimuth and altitude of the drift position

		if azal == 'positionerror' or azal == 'moveboundserror':	# check for invalid or movement, return 

			srtdb.close()

			return (driftdata, azal)

		while curtime < time:							# continue scanning until the current time is past the end time

			status = cur.execute("SELECT * FROM SCANID WHERE ID = ?", (scanid,)).fetchone()		# check current status to see if scan was cancelled

			if status['status'] == 'cancelled':			# if scan was cancelled, return data collected so far

				srtdb.close()

				return (driftdata, 'cancelled')

			spectrumdata = singlespectrum(azal, flimit, step)		# take a spectrum measurement

			driftdata.append(spectrumdata)							# append spectrum data to the scan

			if spectrumdata['spectrumsuccess'] == False:

				srtdb.close()

				return (driftdata, 'timeout')

			curtime = getcurrenttime()			# update current time

		srtdb.close()

		return (driftdata, 'complete')


	'''
	Method that performs an entire scan and stores the collected data in the database.

	:param nextscan: a dict object containing the parameters of a scan
	'''
	def donextscan(nextscan):

		# srtdb = sqlite3.connect('srtdata.db')									# establish a connection and cursor into the database
		# srtdb.row_factory = sqlite3.Row
		# cur = srtdb.cursor()

		# nextscan = cur.execute("SELECT * FROM QUEUE LIMIT 1").fetchone()		# retrieve next scan from queue

		pos = (nextscan['ras'], nextscan['dec'])								# get position of scan

		flower   = nextscan['freqlower']						# get spectrum parameters
		fupper	 = nextscan['frequpper']
		stepnum  = nextscan['stepnum']

		stepsize = (fupper - flower) / stepnum					# calculate step size from spectrum params

		if stepsize < 0.04:										# if step size is below the minimum for the telescope, set to the min

			stepsize = 0.04

		duration = re.split('[hms]', nextscan['duration'])						# get duration values of scan

		seconds = int(duration[0]) * 60 * 60 + int(duration[1]) * 60 + int(duration[2])

		curtime = getcurrenttime()

		endtime = curtime + seconds															# calculate the ending time of the scan in unix time

		cur.execute("UPDATE STATUS SET ID = ?, CODE = ?", (nextscan['id'], 'ok'))			# update the STATUS table
		srtdb.commit()

		if nextscan['type'] == 'track':

			scandata = track(nextscan['id'], pos, (flower, fupper), stepsize, endtime)		# do a track scan

		else:

			scandata = drift(nextscan['id'], pos, (flower, fupper), stepsize, endtime)		# do a drift scan

		if len(scandata[0]) != 0:

			starttime = Time(scandata[0]['starttime'], format = 'unix')							# package scan time info into astropy Time objects for format conversion
			endtime = Time(scandata[len(scandata) - 1]['endtime'], format = 'unix')

			nextscan['starttime'] = startime.iso 	# store start and end times with scan params in iso format
			nextscan['endtime'] = endtime.iso

			t = Table(meta = nextscan);				# initialize astropy Table object to store scan data with scan params as table metadata

			for scan in scandata[0]:				# add scan data to the Table

				t.add_row(scan['spectrum'])

			b = io.BytesIO()						# initialize byte stream for FITS file writing

			t.write(b, format='fits')				# write the Table to the byte stream in FITS format

			d = date.today()						# get today's date

			cur.execute("INSERT INTO SCANRESULTS (?,?)", (nextscan['id'], b.getvalue()))	# store scan name, date, type, and data in the db
			srtdb.commit()

		cur.execute("UPDATE SCANID SET STATUS = ?", (scandata[1],))
		cur.execute("INSERT INTO SCANHISTORY (?,?,?,?,?,?)", (nextscan['id'], nextscan['name'], nextscan['type'], d.day, d.month, d.year))
		srtdb.commit()

		srtdb.close()


	'''
	Helper method to get the current time from an NTP server.

	:return unixtime: current unix time
	'''
	def getcurrenttime():

		c = ntplib.NTPClient()										# initialize ntplib client
		ntptime = c.request(NTP_SERVER, version = 4)				# get current time from Carleton's NTP server
		unixtime = ntptime.tx_time									# convert ntp time to unix time

		return unixtime

	'''
	Helper method to get the azimuth and altitude of a position.

	:param pos: tuple containing right ascension and declination
	:return azal: tuple containing azimuth and altitude, or a string containing an error code
	'''
	def getazal(pos):

		srtdb = sqlite3.connect('srtdata.db')	# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		configdata = cur.execute("SELECT * FROM CONFIG").fetchone()						# retrieve config data from the database

		position = SkyCoord(pos[0], pos[1], frame = 'icrs')								# convert position into astropy SkyCoord object for coord transformation

		location = EarthLocation(lat = configdata['lat'], lon = configdata['lon'], height = configdata['height']) 	# convert location into astropy EarthLocation

		srtdb.close()														# database connection no longer needed

		unixtime = getcurrenttime()											# get curent time to establish AltAz reference frame

		observingtime = Time(unixtime, format = 'unix')						# create astropy Time object using converted ntp time

		azalframe = AltAz(location = location, obstime = observingtime)		# create AltAz reference frame

		try:

			position = position.transform_to(azalframe)			# transform position from galactic coords to az/alt coords

		except ValueError as e:

			return 'positionerror'

		azal = (position.az, position.al)						# create azal tuple

		if azal[0] < configdata['azlower'] or azal[0] > configdata['azupper']:

			return 'moveboundserror'

		if azal[1] < configdata['allower'] or azal[1] > configdata['alupper']:

			return 'moveboundserror'

		return azal