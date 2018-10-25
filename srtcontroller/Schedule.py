'''
A class that schedules scans submitted by clients.

Author: Nathan Rowley
Date: August 2018
'''

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy import units as u
from srtutility.NTPTime import NTPTime
import sqlite3
import re
import datetime
import pytz
from astral import Astral


class Schedule:


	# Initializes a Schedule instance for building scan schedules.
	#
	# :param starttime: start time of the schedule period in unix time
	# :param endtime: end time of the schedule period in unix time
	def __init__(self, starttime, endtime):

		startblock = self.Block(None, starttime, starttime)			# create Blocks to mark the start and end of the schedule

		endblock = self.Block(None, endtime, endtime)

		self.schedule = [startblock, endblock]
		
		self.localtz = pytz.timezone('America/Chicago')		# set local timezone for display time conversions
		
		self.database_location = '../srtdatabase/srtdata.db'


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

		srtdb = sqlite3.connect(self.database_location)			# establish a connection and cursor into the database
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

		scantype = scanparams['type']

		print(str(starttime) + ' ' + str(endtime) + ' ' + scanparams['ras'] + ' ' + scanparams['dec'] + ' ' + scantype)

		status = 'durationerror'

		print('attempting to schedule a scan')

		for i in range(len(self.schedule) - 1):					# loops through the spaces between each Block in the schedule

			print('checking for space after block ' + str(i))

			while starttime >= self.schedule[i].endtime + 300 and endtime <= self.schedule[i+1].starttime - 300:	# loops through five-minute steps of the time between two blocks (padded by five minutes on either side)

				print('there is space, checking for validity')

				result = self.checkscan(scanparams['ras'], scanparams['dec'], scantype, starttime, endtime)		# check to see if the scan is valid within a particular time window

				print(result)

				if status == 'durationerror' or status == 'positionerror':		# error hierarchy is movebounds > position > duration

					status = result

				if result == 'scheduled':		# if the scan is valid, create a new Block for the scan and insert it into the schedule

					print('found a valid spot!')

					status = result

					newblock = Schedule.Block(scanid, starttime, endtime)
					
					starttime = datetime.datetime.fromtimestamp(starttime, pytz.utc).astimezone(self.localtz).strftime('%H:%M')	# convert time values to local time strings
					endtime = datetime.datetime.fromtimestamp(endtime, pytz.utc).astimezone(self.localtz).strftime('%H:%M')

					cur.execute("INSERT INTO SCHEDULE VALUES (?,?,?)", (scanid, starttime, endtime))	# update the schedule and scan status in the db
					srtdb.commit()

					srtdb.close()

					self.schedule.insert(i+1, newblock)

					return status

				starttime += 300			# if scan is not valid within the time frame, adjust the frame five minutes forward
				endtime += 300

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
	# :param ras: right ascension of the scan to be checked
	# :param dec: declination of the scan to be checked
	# :param scantype: a string designating the type of scan
	# :param starttime: start time of the scan in unix time
	# :param endtime: end time of the scan in unix time
	# :return: a string indicating the status of the scan
	def checkscan(self, ras, dec, scantype, starttime, endtime):

		srtdb = sqlite3.connect(self.database_location)	# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		configdata = cur.execute("SELECT * FROM CONFIG").fetchone()		# retrieve config data from the database

		position = SkyCoord(ras, dec, frame = 'icrs')					# convert position into astropy SkyCoord object for coord transformation

		location = EarthLocation(lat = configdata['lat'], lon = configdata['lon'], height = configdata['height']) 	# convert location into astropy EarthLocation

		srtdb.close()

		middletime = (starttime + endtime) / 2

		starttime = Time(starttime, format = 'unix')						# convert times into astropy Time objects
		startframe = AltAz(location = location, obstime = starttime)		# create astropy AltAz frame objects for each time

		if scantype == 'track':

			middletime = Time(middletime, format = 'unix')						# necessary to check a midpoint for altitude bounds due to circumpolar positions possibly dipping too low
			middleframe = AltAz(location = location, obstime = middletime)
			endtime = Time(endtime, format = 'unix')
			endframe = AltAz(location = location, obstime = endtime)

		try:														# attempt to transform the position to the AltAz frame of each time
			
			startpos = position.transform_to(startframe)

			if scantype == 'track':

				middlepos = position.transform_to(middleframe)
				endpos = position.transform_to(endframe)

		except ValueError as e:										# if the position can't be transformed, return a position error

			return 'positionerror'

		azbounds = (configdata['azlower'], configdata['azupper'])		# repackage movement bounds
		albounds = (configdata['allower'], configdata['alupper'])
		
		startaz = float(startpos.az.to_string(unit=u.deg, decimal=True))
		startal = float(startpos.alt.to_string(unit=u.deg, decimal=True))
		
		if scantype == 'track':
			
			middleaz = float(middlepos.az.to_string(unit=u.deg, decimal=True))
			middleal = float(middlepos.alt.to_string(unit=u.deg, decimal=True))
			endaz = float(endpos.az.to_string(unit=u.deg, decimal=True))
			endal = float(endpos.alt.to_string(unit=u.deg, decimal=True))
			
		if startal < 0 or startal > 180:		# if a position has a negative altitude, object is not in the sky, so return position error
			
			return 'positionerror'
			
		if scantype == 'track' and (middleal < 0 or middleal > 180 or endal < 0 or endal > 180):
			
			return 'positionerror'

		valid = True 													# check that the scan stays within telscope movement bounds

		valid = valid and startaz >= azbounds[0] and startaz <= azbounds[1]
		valid = valid and startal >= albounds[0] and startal <= albounds[1]

		if scantype == 'track':

			valid = valid and middleaz >= azbounds[0] and middleaz <= azbounds[1]
			valid = valid and middleal >= albounds[0] and middleal <= albounds[1]
			valid = valid and endaz >= azbounds[0] and endaz <= azbounds[1]
			valid = valid and endal >= albounds[0] and endal <= albounds[1]

		if not valid:
			
			print(str(startaz) + ' ' + str(startal))

			return 'moveboundserror'

		return 'scheduled'


def main():

	srtdb = sqlite3.connect('../srtdatabase/srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	config = cur.execute("SELECT * FROM CONFIG").fetchone()

	a = Astral()

	today = datetime.date.today()

	nighttimes = a.night_utc(today, config['lat'], config['lon'])
	
	print(nighttimes[0].isoformat() + ' ' + nighttimes[1].isoformat())

	dusk = nighttimes[0].timestamp()
	dawn = nighttimes[1].timestamp()

	schedule = Schedule(dusk, dawn)
	
	cur.execute("DELETE FROM SCHEDULE")

	# cur.execute("INSERT INTO SOURCES VALUES (?,?,?)", ('sigma octantis', '21h8m47s', '-88d57m23s'))
	# cur.execute("INSERT INTO SCANIDS VALUES (?,?,?)", (-30, 'invalidtest', 'submitted'))
	# cur.execute("INSERT INTO SCANPARAMS VALUES (?,?,?,?,?,?,?,?,?)", (-30, 'track', 'sigma octantis', '21h8m47s', '-88d57m23s', '1h0m0s', 1500, 1510, 10))
	# cur.execute("UPDATE CONFIG SET LAT = ?, LON = ?", (44.45, -93.16))
	# cur.execute("INSERT INTO SOURCES VALUES (?,?,?)", ('polaris', '2h31m49s', '89d15m50s'))
	# cur.execute("INSERT INTO SCANIDS VALUES (?,?,?)", (-20, 'scheduletest', 'submitted'))
	# cur.execute("INSERT INTO SCANPARAMS VALUES (?,?,?,?,?,?,?,?,?)", (-20, 'track', 'polaris', '2h31m49s', '89d15m50s', '0h30m0s', 1500, 1510, 10))
	# srtdb.commit()
	
	ntp = NTPTime()

	schedule.schedulescan(-20, ntp.getcurrenttime())
	schedule.schedulescan(-30, ntp.getcurrenttime())

	for block in schedule.schedule:

		print(str(block.scanid) + ' ' + str(block.starttime) + ' ' + str(block.endtime))

# main()
