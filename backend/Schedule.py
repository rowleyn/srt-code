'''
A class that schedules scans submitted by clients.

Author: Nathan Rowley
Date: August 2018
'''

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import sqlite3
import re


class Schedule:


	# Initializes a Schedule instance for building scan schedules.
	#
	# :param starttime: start time of the schedule period in unix time
	# :param endtime: end time of the schedule period in unix time
	def __init__(self, starttime, endtime):

		startblock = self.Block(None, starttime, starttime)			# create Blocks to mark the start and end of the schedule

		endblock = self.Block(None, endtime, endtime)

		self.schedule = [startblock, endblock]


	# Internal class for storing scan and time info in a Schedule
	#
	# :param scanid: the id of the scan in this block, or None if the block is an endmarker
	# :param starttime: start time of the scan in unix time
	# :param endtime: end time of the scan in unix time
	class Block:

		def __init__(self, scanid, starttime, endtime):

			self.scanid = scanid
			self.starttime = starttime
			self.endtime = endtime


	# Method for adding a scan to the schedule. Inserts the scan at the earliest possible valid time.
	#
	# :param scanid: the id of the scan to be added to the schedule
	# :param curtime: the current unix time
	# :return status: the status of the scan indicating success or failure to schedule
	def schedulescan(self, scanid, curtime):

		srtdb = sqlite3.connect('srtdata.db')						# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		scanparams = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (scanid,)).fetchone()

		duration = re.split('[hms]', scanparams['duration'])								# get duration values of scan

		seconds = int(duration[0]) * 60 * 60 + int(duration[1]) * 60 + int(duration[2])		# calculate durationin seconds

		if curtime > self.schedule[0].endtime:

			starttime = curtime + 300						# start time is the current time if past the start of night

		else:

			starttime = self.schedule[0].endtime + 300		# start time of new Block is after the first Block

		endtime = starttime + seconds

		pos = (scanparams['ras'], scanparams['dec'])

		scantype = scanparams['type']

		status = 'durationerror'

		print('attempting to schedule a scan')

		for i in range(len(self.schedule) - 2):							# loops through the spaces between each Block in the schedule

			while starttime >= self.schedule[i].endtime + 300 and endtime <= self.schedule[i+1].starttime - 300:		# loops through five-minute steps of the time between two blocks (padded by five minutes on either side)

				result = checkscan(pos, scantype, starttime, endtime)			# check to see if the scan is valid within a particular time window

				if status == 'durationerror' or status == 'positionerror':		# error hierarchy is movebounds > poisition > duration

					status == result

				if result == 'scheduled':		# if the scan is valid, create a new Block for the scan and insert it into the schedule

					print('found a spot!')

					status == result

					newblock = Block(scanid, starttime, endtime)
					
					startime = re.split('\.|\s', Time(starttime, scale='utc', format='unix').iso)[1]
					endtime = re.split('\.|\s', Time(endtime, scale='utc', format='unix').iso)[1]

					cur.execute("INSERT INTO SCHEDULE VALUES (?,?,?)", (scanid, starttime, endtime))	# update the schedule and scan status in the db
					srtdb.commit()

					srtdb.close()

					self.schedule.insert(i+1, newblock)

					return status

				startime += 60			# if scan is not valid within the time frame, adjust the frame a minute forward
				endtime += 60

			starttime = self.schedule[i+1].endtime + 300	# update starttime to after the next Block

			if starttime < curtime:							# if curtime not yet reached, reset starttime to curtime

				starttime = curtime + 300

			endtime = starttime + seconds					# update endtime to reflect new starttime

		print('couldn\'t find a spot. error code: ' + status)

		srtdb.close()

		return status
		

	# Method that removes a scan from the schedule with an id matching scanid.
	#
	# :param scanid: the id of the scan to be removed
	# :return:
	def deschedulescan(self, scanid):

		for i in range(len(self.schedule - 2)):

			if self.schedule[i].scanid == scanid:

				print('scan removed from schedule')

				del self.schedule[i]
				break


	# Helper method for checking the validity of a scan.
	# Checks that the scan's position is in the sky and that the scan does not go out of movement bounds.
	#
	# :param pos: a tuple containing the RA/dec position of the scan
	# :param scantype: a string designating the type of scan
	# :param starttime: start time of the scan in unix time
	# :param endtime: end time of the scan in unix time
	# :return: a string indicating the status of the scan
	def checkscan(pos, scantype, starttime, endtime):

		srtdb = sqlite3.connect('srtdata.db')	# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		configdata = cur.execute("SELECT * FROM CONFIG").fetchone()						# retrieve config data from the database

		position = SkyCoord(pos[0], pos[1], frame = 'icrs')								# convert position into astropy SkyCoord object for coord transformation

		location = EarthLocation(lat = configdata['lat'], lon = configdata['lon'], height = configdata['height']) 	# convert location into astropy EarthLocation

		srtdb.close()														# database connection no longer needed

		middletime = (starttime + endtime) / 2

		starttime = Time(starttime, format = 'unix')						# convert times into astropy Time objects
		startframe = AltAz(location = location, obstime = starttime)		# create astropy AltAz frame objects for each time

		if scantype == 'track':

			middletime = Time(middletime, format = 'unix')						# necessary to check a midpoint for altitude bounds due to circumpolar positions possibly dipping too low
			middeframe = AltAz(location = location, obstime = middletime)
			endtime = Time(endtime, format = 'unix')
			endframe = AltAz(location = location, obstime = endtime)

		try:														# attempt to transform the position to the AltAz frame of each time
			
			startpos = position.transform_to(startframe)

			if scantype == 'track':

				middlepos = position.transform_to(middleframe)
				endpos = position.transform_to(endframe)

		except ValueError as e:										# if the position can't be transformed, return False

			return 'positionerror'

		azbounds = (configdata['azlower'], configdata['azupper'])		# repackage movement bounds
		albounds = (configdata['allower'], configdata['alupper'])

		valid = True 													# check that the scan stays within telscope movement bounds

		valid = valid and startpos.az >= azbounds[0] and startpos.az <= azbounds[1]
		valid = valid and startpos.al >= albounds[0] and startpos.al <= albounds[1]

		if scantype == 'track':

			valid = valid and middlepos.az >= azbounds[0] and middlepos.az <= azbounds[1]
			valid = valid and middlepos.al >= albounds[0] and middlepos.al <= albounds[1]
			valid = valid and endpos.az >= azbounds[0] and endpos.az <= azbounds[1]
			valid = valid and endpos.al >= albounds[0] and endpos.al <= albounds[1]

		if not valid:

			return 'moveboundserror'

		return 'scheduled'
