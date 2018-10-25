'''
A class that performs tracking and drift scans
with parameters acquired from the scan queue.

Author: Nathan Rowley
Date: June 2018
'''

from CommandStation import CommandStation
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy.table import Table
from astropy import units as u
from numpy import linspace
from datetime import date
from srtutility.NTPTime import NTPTime
import io
import re
import sqlite3
import _thread

class Scan:

	def __init__(self):

		self.station = CommandStation()
		
		self.ntp = NTPTime()
		
		self.database_location = '../srtdatabase/srtdata.db'


	# Method to take a single data point at a single frequency for a single source.
	#
	# :param azal: tuple containing azimuth and altitude of scan position
	# :param freq: frequency in MHz at which to measure
	# :return scan: tuple containing a single power measurement and boolean indicating successful movement
	def singlescan(self, azal, freq):

		movesuccess = self.station.movebyazal(azal[0], azal[1])		# move station to scan position

		if movesuccess:

			scan = self.station.readpower(freq)			# read power at frequency freq

		else:

			scan = 0

		return (scan, movesuccess)


	# Method to take data points across a spectrum for a single source.
	#
	# :param azal: tuple containing azimuth and altitude of scan position
	# :param flimit: tuple containing lower and upper frequency limits in MHz
	# :param stepnum: number of steps to take over the frequency range
	# :return data: dictionary containing a single spectrum with start and end times and a time correction value
	def singlespectrum(self, azal, flimit, stepnum):

		spectrum = []

		starttime = self.ntp.getcurrenttime()	# get start time of spectrum scan

		spectrumsuccess = True

		for freq in linspace(flimit[0], flimit[1], stepnum):	# sweep through frequencies in range, taking stepnum steps

			if spectrumsuccess:

				scan = self.singlescan(azal, freq)		# do single scan at current frequency

				if scan[1] == False:

					spectrumsuccess = False

			else:

				scan = (0, False)

			spectrum.append(scan[0])	# append scan result to spectrum

		endtime = self.ntp.getcurrenttime()		# get end time of spectrum scan

		data = {'spectrum': spectrum, 'starttime': starttime, 'endtime': endtime, 'spectrumsuccess': spectrumsuccess}		# package spectrum and time data

		return data


	# Method to track a position and take data for a specific duration.
	#
	# :param scanid: the id of the current scan
	# :param pos: tuple containing galactic latitude and longitude of the position to track
	# :param flimit: tuple containing lower and upper frequency limits in MHz
	# :param stepnum: number of steps to take over the frequency range
	# :param time: unix time at which to stop scanning
	# :return trackdata: tuple containing a list of scan data and a string indicating the status of the scan
	def track(self, scanid, pos, flimit, stepnum, time):

		print('running a track scan')

		srtdb = sqlite3.connect(self.database_location)		# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		curtime = self.ntp.getcurrenttime()		# get start time of scan

		trackdata = []

		while curtime < time:	# continue scanning until current time is past the end time

			status = cur.execute("SELECT * FROM SCANIDS WHERE ID = ?", (scanid,)).fetchone()		# check current status to see if scan was cancelled

			if status['status'] == 'cancelled':		# if scan was cancelled, return data collected so far

				print('scan was cancelled')

				srtdb.close()

				return (trackdata, 'cancelled')

			azal = self.getazal(pos)		# get current azimuth and altitude of tracked position

			if azal == 'positionerror' or azal == 'moveboundserror':	# check for invalid position or movement, return if found

				srtdb.close()

				return (trackdata, azal)

			spectrumdata = self.singlespectrum(azal, flimit, stepnum)	# take a spectrum measurement

			trackdata.append(spectrumdata)		# append spectrum data to the scan

			if spectrumdata['spectrumsuccess'] == False:

				print('scan timed out')

				srtdb.close()

				return (trackdata, 'timeout')

			curtime = self.ntp.getcurrenttime()		# update current time

		print('scan complete')

		srtdb.close()

		return (trackdata, 'complete')


	# Method to take data at a single drift position for a specific duration.
	#
	# :param scanid: the id of the current scan
	# :param pos: tuple containing galactic latitude and longitude of drift position
	# :param flimit: tuple containing lower and upper frequency limits in MHz
	# :param stepnum: number of steps to take over the frequency range
	# :param time: unix time at which to stop scanning
	# :return driftdata: tuple containing a list of scan data and a string indicating the status of the scan
	def drift(self, scanid, pos, flimit, stepnum, time):

		print('running a drift scan')

		srtdb = sqlite3.connect(self.database_location)		# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		curtime = self.ntp.getcurrenttime()		# get start time of scan

		driftdata = []

		azal = self.getazal(pos)		# get azimuth and altitude of the drift position

		if azal == 'positionerror' or azal == 'moveboundserror':	# check for invalid or movement, return 

			srtdb.close()

			return (driftdata, azal)

		while curtime < time:		# continue scanning until the current time is past the end time

			status = cur.execute("SELECT * FROM SCANID WHERE ID = ?", (scanid,)).fetchone()		# check current status to see if scan was cancelled

			if status['status'] == 'cancelled':			# if scan was cancelled, return data collected so far

				print('scan was cancelled')

				srtdb.close()

				return (driftdata, 'cancelled')

			spectrumdata = self.singlespectrum(azal, flimit, stepnum)		# take a spectrum measurement

			driftdata.append(spectrumdata)		# append spectrum data to the scan

			if spectrumdata['spectrumsuccess'] == False:

				print('scan timed out')

				srtdb.close()

				return (driftdata, 'timeout')

			curtime = self.ntp.getcurrenttime()			# update current time

		print('scan complete')

		srtdb.close()

		return (driftdata, 'complete')


	# Method that performs an entire scan and stores the collected data in the database.
	#
	# :param nextscan: a dict object containing the parameters of a scan
	def donextscan(self, nextscan):

		srtdb = sqlite3.connect(self.database_location)	# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		pos = (nextscan['ras'], nextscan['dec'])	# get position of scan

		flower   = nextscan['freqlower']			# get spectrum parameters
		fupper	 = nextscan['frequpper']
		stepnum  = nextscan['stepnum']

		duration = re.split('[hms]', nextscan['duration'])		# get duration values of scan

		seconds = int(duration[0]) * 60 * 60 + int(duration[1]) * 60 + int(duration[2])

		curtime = self.ntp.getcurrenttime()

		endtime = curtime + seconds		# calculate the ending time of the scan in unix time

		cur.execute("UPDATE STATUS SET ID = ?, CODE = ?", (nextscan['id'], 'ok'))			# update the STATUS table
		srtdb.commit()

		if nextscan['type'] == 'track':

			scandata = self.track(nextscan['id'], pos, (flower, fupper), stepnum, endtime)		# do a track scan

		else:

			scandata = self.drift(nextscan['id'], pos, (flower, fupper), stepnum, endtime)		# do a drift scan

		if len(scandata[0]) != 0:

			print('saving scan data')

			starttime = Time(scandata[0][0]['starttime'], format = 'unix')					# package scan time info into astropy Time objects for format conversion
			endtime = Time(scandata[0][len(scandata) - 1]['endtime'], format = 'unix')

			nextscan['starttime'] = starttime.iso 	# store start and end times with scan params in iso format
			nextscan['endtime'] = endtime.iso
			
			tablerows = []
			
			for scan in scandata[0]:
				
				tablerows.append(scan['spectrum'])

			t = Table(rows = tablerows, meta = nextscan);		# initialize astropy Table object to store scan data with scan params as table metadata

			# for scan in scandata[0]:		# add scan data to the Table

				# t.add_row(scan['spectrum'])

			b = io.BytesIO()			# initialize byte stream for FITS file writing

			t.write(b, format='fits')	# write the Table to the byte stream in FITS format

			d = date.today()			# get today's date
			
			with open('testfits.fits', 'w') as f:
				
				f.write(b.getvalue().decode('ascii'))

			cur.execute("INSERT INTO SCANRESULTS VALUES (?,?)", (nextscan['id'], b.getvalue()))	# store scan name, date, type, and data in the db
			srtdb.commit()

		cur.execute("UPDATE SCANIDS SET STATUS = ? WHERE ID = ?", (scandata[1], nextscan['id']))
		scanname = cur.execute("SELECT * FROM SCANIDS WHERE ID = ?", (nextscan['id'],)).fetchone()['name']
		cur.execute("INSERT INTO SCANHISTORY VALUES (?,?,?,?,?,?)", (nextscan['id'], scanname, nextscan['type'], d.day, d.month, d.year))
		srtdb.commit()

		srtdb.close()


	# Helper method to get the azimuth and altitude of a position.
	#
	# :param pos: tuple containing right ascension and declination
	# :return azal: tuple containing azimuth and altitude, or a string containing an error code
	def getazal(self, pos):

		print('calculating azal')

		srtdb = sqlite3.connect(self.database_location)	# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		configdata = cur.execute("SELECT * FROM CONFIG").fetchone()		# retrieve config data from the database

		position = SkyCoord(pos[0], pos[1], frame = 'icrs')				# convert position into astropy SkyCoord object for coord transformation

		location = EarthLocation(lat = configdata['lat'], lon = configdata['lon'], height = configdata['height']) 	# convert location into astropy EarthLocation

		srtdb.close()

		unixtime = self.ntp.getcurrenttime()		# get curent time to establish AltAz reference frame

		observingtime = Time(unixtime, format = 'unix')		# create astropy Time object using converted ntp time

		azalframe = AltAz(location = location, obstime = observingtime)		# create AltAz reference frame

		try:

			position = position.transform_to(azalframe)		# transform position from galactic coords to az/alt coords

		except ValueError as e:		# if transformation is impossible, return position error

			print('positionerror')

			return 'positionerror'

		azal = (float(position.az.to_string(unit=u.deg, decimal=True)), float(position.alt.to_string(unit=u.deg, decimal=True)))		# create azal tuple
		
		if azal[1] < 0 or azal[1] > 180:	# if position is not in the sky, return position error
			
			print('positionerror')
			
			return 'positionerror'

		if azal[0] < configdata['azlower'] or azal[0] > configdata['azupper']:	# if motion would violate movement bounds, return movebounds error

			print('moveboundserror')

			return 'moveboundserror'

		if azal[1] < configdata['allower'] or azal[1] > configdata['alupper']:

			print('moveboundserror')

			return 'moveboundserror'

		print(str(azal[0]) + ', ' + str(azal[1]))

		return azal


def main():
	
	srtdb = sqlite3.connect('../srtdatabase/srtdata.db')	# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()
	
	# cur.execute("INSERT INTO SCANIDS VALUES (?,?,?)", (-50, 'scantest', 'scheduled'))
	# cur.execute("INSERT INTO SCANPARAMS VALUES (?,?,?,?,?,?,?,?,?)", (-50, 'track', 'sun', '9h46m58s', '13d22m20s', '0h0m30s', 1500, 1510, 10))
	# srtdb.commit()
	
	scan = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (-50,)).fetchone()
	
	nextscan = {}
	
	for key in scan.keys():
		
		nextscan[key.lower()] = scan[key]
	
	station = Scan()
	
	# _thread.start_new_thread(station.donextscan, (nextscan,))
	
	station.donextscan(nextscan)

# main()
