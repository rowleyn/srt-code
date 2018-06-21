'''
A class that performs tracking and drift scans at
particular frequencies and of the whole station spectrum.

Author: Nathan Rowley
Date: June 2018
'''

import CommandStation
import json
import ntplib
from astropy.table import Table, Column, vstack

class Scan:

	def __init__(self):
		self.station = CommandStation()

	'''
	Method to take a single data point at a single frequency for a single source.

	:param pos: tuple containing azimuth and altitude of scan position
	:param freq: frequency in MHz at which to measure
	:return scan: astropy Table object containing a single power measurement
	'''
	def singlescan(self, pos, freq) -> Table:

		self.station.movebyazal(pos[0], pos[1])		# move station to scan position

		scan = self.station.readpower(freq)			# read power at frequency freq
		curtime = getcurrenttime()					# get time of scan
		
		freqcol = Column([freq], name = 'frequency', unit = 'MHz')	# convert lists to astropy Column objects
		powcol  = Column([scan], name = 'temperature', unit = 'K')
		timecol = Column([curtime], name = 'time', unit = 's')

		scan = Table((freqcol, powcol, timecol))					# create astropy Table object containing scan data

		return scan

	'''
	Method to take data points across a spectrum for a single source.

	:param source: tuple containing azimuth and altitude of scan position
	:param flimit: tuple containing lower and upper frequency limits in MHz for the scan
	:param step: frequency step quantity in MHz for the scan
	:return spectrum: astropy Table object containing a single spectrum measurement
	'''
	def singlespectrum(self, pos, flimit, step) -> Table:

		scan     = Table()										# intialize astropy Table objects to store spectrum data
		spectrum = Table()

		curtime = getcurrenttime()								# get time of spectrum scan

		for freq in range(flimit[0], flimit[1], step):						# sweep through frequencies in range, taking 40 kHz steps

			scan = singlescan(pos, freq)						# get scan at current frequency

			scan['time'][1] = curtime							# set time to current time

			spectrum = vstack([spectrum, scan])					# append scan to the spectrum

		return spectrum

	'''
	Method to track and take data points on a single source at a single frequency until a specified time.

	:param source: name of source to track and measure
	:param freq: frequency in MHz at which to measure
	:param time: unix time at which to stop scanning
	:return scan: astropy Table object containing a scan of source over time
	'''
	def trackscan(self, source, freq, time) -> Table:

		scan = Table()						# initialize data Table

		curtime = getcurrenttime()			# get start time of scan

		while curtime < time:				# continue scanning until the current time is past the end time

			pos = getsourceazal(source)		# get azal coords for source

			scan = vstack([scan, singlescan(pos, freq)])		# take reading and append to the scan

			curtime = getcurrenttime()		# update current time

		return scan

	'''
	Method to track and take data points on a single source across the whole station spectrum until a specific time.

	:param source: name of source to track and measure
	:param flimit: tuple containing lower and upper frequency limits in MHz for the scan
	:param step: frequency step quantity in MHz for the scan
	:param time: unix time at which to stop scanning
	:return spectrum: astropy Table object containing a scan of the source's spectrum over time
	'''
	def trackspectrum(self, source, flimit, step, time) -> Table:

		curtime = getcurrenttime()			# get start time of scan

		spectrum = Table()					# initialize data Table

		while curtime < time:				# continue scanning until the current time is past the end time

			pos = getsourceazal(source)		# get azal coords for source

			spectrum = vstack([spectrum, singlespectrum(pos, flimit, step)])	# take spectrum and append to the scan

			curtime = getcurrenttime()		# update current time

		return spectrum

	'''
	Method to take a drift scan at a single frequency until a specific time.

	:param pos: tuple containing azimuth and altitude of drift position
	:param freq: frequency in MHz at which to measure
	:param time: unix time at which to stop scanning
	:return scan: astropy Table object containing a drift scan
	'''
	def driftscan(self, pos, freq, time) -> Table:

		scan = Table()						# initialize data Table

		curtime = getcurrenttime()			# get start time of scan

		while curtime < time:				# continue scanning until the current time is past the end time

			scan = vstack([scan, singlescan(pos, freq)])		# take reading and append to the scan

			curtime = getcurrenttime()		# update current time

		return scan

	'''
	Method to take a drift scan across the whole station spectrum until a specific time.

	:param pos: tuple containing azimuth and altitude of drift position
	:param flimit: tuple containing lower and upper frequency limits in MHz for the scan
	:param step: frequency step quantity in MHz for the scan
	:param time: unix time at which to stop scanning
	:return spectrum: astropy table object containing a drift scan of spectrum over time
	'''
	def driftspectrum(self, pos, flimit, step, time) -> Table:

		curtime = getcurrenttime()			# get start time of scan

		spectrum = Table()					# initialize data Table

		while curtime < time:				# continue scanning until the current time is past the end time

			spectrum = vstack([spectrum, singlespectrum(pos, flimit, step)])	# take spectrum and append to the scan

			curtime = getcurrenttime()		# update current time

		return spectrum

	'''
	Helper method to get the current time from an NTP server.

	:return unixtime: current unix time
	'''
	def getcurrenttime(self):

		c = ntplib.NTPClient()
		ntptime = c.request('ntp.carleton.edu',version = 4)				# get current time from Carleton's NTP server
		unixtime = ntptime.tx_time - 18000								# convert ntp time to unix time

		return unixtime

	'''
	Helper method to get the azimuth and altitude of a source.

	:param source: name of source
	:return pos: tuple containing azimuth and altitude of source
	'''
	def getsourceazal(self, source):

		with open('srtconfig.json') as f:								# get station data from config
			stationdata = json.load(f)

		source = stationdata['config']['sources'][sourcename]			# look up source by name
		source = SkyCoord(source['ras'],source['dec'],frame = 'icrs')	# convert source into astropy SkyCoord object for coord transformation

		location = stationdata['config']['station']																# look up station location data
		location = EarthLocation(lat = location['lat'], lon = location['lon'], height = location['height']) 	# convert location into astropy EarthLocation

		unixtime = getcurrenttime()										# get curent time to establish AltAz reference frame

		observingtime = Time(unixtime,format = 'unix')					# create astropy Time object using converted ntp time

		azalt = AltAz(location = location, obstime = observingtime)		# create AltAz reference frame

		source = source.transform_to(azalt)								# transform source from ras/dec coords to az/alt coords

		pos = (source.az, source.al)									# create position tuple

		return pos