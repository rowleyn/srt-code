'''
A class that performs tracking and drift scans
with parameters acquired from the scan queue.

Author: Nathan Rowley
Date: June 2018
'''

import CommandStation
import json
import ntplib
import sqlite3
from astropy.table import Table, Column, vstack

NTP_SERVER = 'ntp.carleton.edu'		# NTP server for time retrieval. Change to suit your needs

class Scan:

	def __init__(self):
		self.station = CommandStation()

	'''
	Method to take a single data point at a single frequency for a single source.

	:param azal: tuple containing azimuth and altitude of scan position
	:param freq: frequency in MHz at which to measure
	:return scan: float containing a single power measurement
	'''
	def singlescan(self, azal, freq) -> float:

		self.station.movebyazal(azal[0], azal[1])		# move station to scan position

		scan = self.station.readpower(freq)			# read power at frequency freq

		return scan

	'''
	Method to take data points across a spectrum for a single source.

	:param azal: tuple containing azimuth and altitude of scan position
	:param flimit: tuple containing lower and upper frequency limits in MHz
	:param step: float containing frequency step quantity in MHz
	:return data: dictionary containing a single spectrum with start and end times
	'''
	def singlespectrum(self, azal, flimit, step) -> dict:

		spectrum = []

		starttime = getcurrenttime()							# get start time of spectrum scan

		for freq in range(flimit[0], flimit[1], step):			# sweep through frequencies in range with step size step

			spectrum.append(singlescan(azal, freq))				# do single scan at current frequency and append result to spectrum

		endtime = getcurrenttime()								# get end time of spectrum scan

		data = {'spectrum': spectrum, 'starttime': starttime, 'endtime': endtime}		# package spectrum and times

		return data

	'''
	Method to track a position and take data for a specific duration.

	:param pos: tuple containing galactic latitude and longitude of the position to track
	:param flimit: tuple containing lower and upper frequency limits in MHz
	:param step: float containing frequency step quantity in MHz
	:param time: unix time at which to stop scanning
	:param scanid: id number of the current scan
	:return trackdata: list containing scan data
	'''
	def track(self, pos, flimit, step, time, scanid) -> list:

		srtdb = sqlite3.connect('srtdata.db')						# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		curtime = getcurrenttime()									# get start time of scan

		trackdata = []

		while curtime < time:										# continue scanning until current time is past the end time

			scan = cur.execute("SELECT ID FROM QUEUE WHERE ID = ? LIMIT 1", (scanid,)).fetchone()		# try to retrieve the current scan from the queue

			if scan == None:										# if scan was not retrieved, it was removed from queue and scan should be stopped

				break

			azal = getsourceazal(pos)								# get current azimuth and altitude of tracked position

			trackdata.append(singlespectrum(azal, flimit, step))	# take a spectrum measurement and append to the scan

			curtime = getcurrenttime()								# update current time

		srtdb.close()

		return trackdata

	'''
	Method to take data at a single drift position for a specific duration.

	:param pos: tuple containing galactic latitude and longitude of drift position
	:param flimit: tuple containing lower and upper frequency limits in MHz
	:param step: float containing frequency step quantity in MHz
	:param time: unix time at which to stop scanning
	:param scanid: id number of the current scan
	:return driftdata: list containing scan data
	'''
	def drift(self, pos, flimit, step, time, scanid) -> list:

		srtdb = sqlite3.connect('srtdata.db')						# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		curtime = getcurrenttime()									# get start time of scan

		driftdata = []

		azal = getazal(pos)											# get azimuth and altitude of the drift position

		while curtime < time:										# continue scanning until the current time is past the end time

			scan = cur.execute("SELECT ID FROM QUEUE WHERE ID = ? LIMIT 1", (scanid,)).fetchone()		# try to retrieve the current scan from the queue

			if scan == None:										# if scan was not retrieved, it was removed from queue and scan should be stopped

				break

			driftdata.append(singlespectrum(azal, flimit, step))	# take spectrum measurement and append to the scan

			curtime = getcurrenttime()								# update current time

		srtdb.close()

		return driftdata


	def donextscan():

		srtdb = sqlite3.connect('srtdata.db')									# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		nextscan = cur.execute("SELECT * FROM QUEUE LIMIT 1").fetchone()		# retrieve next scan from queue

		pos = (nextscan['gallat'], nextscan['gallon'])							# get galactic position of scan

		center   = nextscan['center']											# get spectrum parameters of scan
		stepnum  = nextscan['stepnum']
		stepsize = nextscan['stepsize']

		offset = (stepnum / 2) * stepsize										# calculate upper and lower frequency limits of scan
		flower = center - offset
		fupper = center + offset

		duration = re.split('[hms]', nextscan['duration'])						# get duration values of scan

		seconds = int(duration[0]) * 60 * 60 + int(duration[1]) * 60 + int(duration[2])

		curtime = getcurrenttime()

		endtime = curtime + seconds										# calculate the ending time of the scan in unix time

		cur.execute("UPDATE TIMEDONE SET ENDTIME = ?", (endtime,))		# update the TIMEDONE table with the ending time of this scan
		srtdb.commit()

		if nextscan['type'] == 'track':

			if nextscan['source'] != 'no source':														# if scan has a source selected, use source coords instead

				source = cur.execute("SELECT * FROM SOURCES WHERE NAME = ?", (nextscan['source'],))		# retrieve source data from the database

				pos = (source['lat'], source['lon'])													# change pos to source coords


			scandata = track(pos, (flower, fupper), stepsize, endtime, nextscan['id'])					# do a track scan

		else:

			scandata = drift(pos, (flower, fupper), stepsize, endtime, nextscan['id'])					# do a drift scan


	'''
	Helper method to get the current time from an NTP server.

	:return unixtime: current unix time
	'''
	def getcurrenttime(self):

		c = ntplib.NTPClient()
		ntptime = c.request(NTP_SERVER, version = 4)				# get current time from Carleton's NTP server
		unixtime = ntptime.tx_time									# convert ntp time to unix time

		return unixtime

	'''
	Helper method to get the azimuth and altitude of a position in galactic coords.

	:param pos: tuple containing galactic latitude and longitude
	:return azal: tuple containing azimuth and altitude
	'''
	def getazal(self, pos):

		srtdb = sqlite3.connect('srtdata.db')	# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		configdata = cur.execute("SELECT * FROM CONFIG").fetchone()						# retrieve config data from the database

		position = SkyCoord(pos[0], pos[1], frame = 'galactic')							# convert position into astropy SkyCoord object for coord transformation

		location = EarthLocation(lat = configdata['lat'], lon = configdata['lon'], height = configdata['height']) 	# convert location into astropy EarthLocation

		srtdb.close()														# database connection no longer needed

		unixtime = getcurrenttime()											# get curent time to establish AltAz reference frame

		observingtime = Time(unixtime, format = 'unix')						# create astropy Time object using converted ntp time

		azalframe = AltAz(location = location, obstime = observingtime)		# create AltAz reference frame

		position = position.transform_to(azalframe)							# transform position from galactic coords to az/alt coords

		azal = (position.az, position.al)									# create azal tuple

		return azal