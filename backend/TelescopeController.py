'''
The code that maintains the telescope's schedule of scans and issues the order to perform scans.
It is the main execution loop for the telescope-side code.

Author: Nathan Rowley
Date: August 2018
'''

from Scan import Scan
from NTPTime import NTPTime
import Schedule
import datetime
import time
import _thread
import sqlite3
from astral import Astral
from astropy.time import Time

ntp = NTPTime()


#
# The main method of the telescope code. All telescope actions ultimately originate from this method.
#
def main():

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	telescope = Scan()			# initialize a Scan object for running scans

	config = cur.execute("SELECT * FROM CONFIG").fetchone()		# fetch config data from the db

	a = Astral()					# initalize an Astral object for computer day and night times

	today = datetime.date.today()	# get today's date

	daytimes = a.daylight_utc(today, config['lat'], config['lon'])			# compute date and night times in UTC using the Astral object
	nighttimes = a.night_utc(today, config['lat'], config['lon'])

	print('Daystart: ' + daytimes[0].isoformat() + ', Dayend: ' + daytimes[1].isoformat())
	print('Nightstart:' + nighttimes[0].isoformat() + ', Nightend: ' + nighttimes[1].isoformat())

	dusk = nighttimes[0].timestamp()	# get unix times for day and night
	dawn = nighttimes[1].timestamp()
	sunrise = daytimes[0].timestamp()
	sunset = daytimes[1].timestamp()

	dayschedule = Schedule.Schedule(sunrise + 7200, sunset - 7200)		# instantiate day and night schedules
	nightschedule = Schedule.Schedule(dusk, dawn)

	currentscanid = None


	### MAIN EXECUTION LOOP FOR TELESCOPE-SIDE CODE ###

	while True:

		time.sleep(0.5)			# sleep for half a second to reduce looping speed


		### set whether it is day or night ###

		curtime = ntp.getcurrenttime()

		if curtime >= dusk and curtime <= dawn:

			currentschedule = nightschedule

		else:

			currentschedule = dayschedule


		### create new schedules if current schedules are completed ###

		config = cur.execute("SELECT * FROM CONFIG").fetchone()		# get config data from the db

		newday = datetime.date.today()								# get today's date

		if newday.day != today.day or newday.month != today.month or newday.year != today.year:	# if the day has changed, create new day schedule

			print('it\'s a new day! setting up new daytime schedule')

			today = newday

			daytimes = a.daylight_utc(today, config['lat'], config['lon'])

			sunrise = Time(daytimes[0], format = 'datetime', scale = 'utc').unix
			sunset = Time(daytimes[1], format = 'datetime', scale = 'utc').unix

			dayschedule = Schedule(sunrise + 7200, sunset - 7200)

		if curtime > dawn:											# if the night is over, create new night schedule

			print('good morning! setting up new nighttime schedule')

			nighttimes = a.night_utc(today, config['lat'], config['lon'])

			dusk = Time(nighttimes[0], format = 'datetime', scale = 'utc').unix
			dawn = Time(nighttimes[1], format = 'datetime', scale = 'utc').unix

			nightschedule = Schedule(dusk, dawn)


		### remove cancelled scans from schedules ###

		print('might be time to cancel some scans')

		cancelscans(dayschedule)
		cancelscans(nightschedule)


		### insert a new scan into the schedule ###

		print('is there a new scan to add?')

		newscan = cur.execute("SELECT * FROM SCANIDS WHERE STATUS = ?", ('submitted',)).fetchone()

		if newscan != None:				# check if a scan has been submitted

			print('yes there is!')

			scanparams = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (newscan['id'],)).fetchone()

			if scanparams['source'] == 'sun':		# if source is the sun, schedule during the day

				status = dayschedule.schedulescan(scanparams['id'], curtime)

			else:		# if source is not the sun, schedule at night

				status = nightschedule.schedulescan(scanparams['id'], curtime)
				
			if status != 'scheduled':
				
				today = datetime.date.today()
				cur.execute("INSERT INTO SCANHISTORY VALUES (?,?,?,?,?,?)", (newscan['id'], scanparams['name'], scanparams['type'], today.day. today.month, today.year))

			cur.execute("UPDATE SCANIDS SET STATUS = ? WHERE ID = ?", (status, newscan['id']))
			srtdb.commit()


		### remove current scan from the schedule when it finishes ###

		print('did the current scan finish running?')

		if currentscanid != None:		# check to see if a scan is supposed to be running

			currentscan = cur.execute("SELECT * FROM SCANIDS WHERE ID = ?", (currentscanid,)).fetchone()

			if currentscan == None or currentscan['status'] != 'running':	# if scan is not running anymore, remove from schedule and reset currentscanid

				print('yes it did!')

				cur.execute("DELETE FROM SCHEDULE WHERE ID = ?", (currentscanid,))
				srtdb.commit()

				currentschedule.deschedulescan(currentscanid)

				currentscanid = None


		### run the next scan in the schedule ###

		print('time to run a scan?')

		currentscanid = runscan(currentschedule)


# Helper method that checks for any cancelled scans that must be removed from a schedule.
#
# :param schedule: the schedule to check for cancelled scans
# :return:
def cancelscans(schedule):

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	today = datetime.date.today()

	for block in schedule.schedule:				# check all blocks for cancellation

		if block.scanid != None:

			status = cur.execute("SELECT * FROM SCANIDS WHERE ID = ?", (block.scanid,)).fetchone()		# fetch scan status from the db

			if status['status'] == 'cancelled':

				print('found a cancelled scan')

				scantype = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (block.scanid,)).fetchone()['type']		# if scan is cancelled, remove from the schedule and add to history

				cur.execute("DELETE FROM SCHEDULE WHERE ID = ?", (block.scanid,))
				cur.execute("INSERT INTO SCANHISTORY VALUES (?,?,?,?,?,?)", (block.scanid, status['name'], scantype, today.day, today.month, today.year))
				srtdb.commit()

				schedule.deschedulescan(block.scanid)

	srtdb.close()


# Helper method that checks a schedule and runs a scan scheduled at the current time
#
# :param schedule: the schedule to check for scans to run
# :return currentscanid: the id of the currently running scan
def runscan(schedule):

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	curtime = ntp.getcurrenttime()

	currentscanid = None

	for block in schedule.schedule:			# check eachblock for start time

		if block.scanid != None:

			if curtime >= block.starttime - 5 and curtime <= block.starttime + 5:		# if the start time is now, try to run the scan

				status = cur.execute("SELECT * FROM STATUS").fetchone()

				if status['code'] == 'timeout':						# if telescope is currently timed out, cancel the scan

					print('cancelling next scan due to timeout')

					today = datetime.date.today()

					scantype = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (block.scanid,)).fetchone()['type']

					cur.execute("INSERT INTO SCANHISTORY VALUES (?,?,?,?,?,?)", (block.scanid, status['name'], scantype, today.day, today.month, today.year))
					cur.execute("UPDATE SCANIDS SET STATUS = ? WHERE ID = ?", ('timeout', block.scanid))
					srtdb.commit()

				else:			# if no timeout is in effect, spawn a new thread to run the next scan

					print('spawning thread to run next scan')

					cur.execute("UPDATE SCANIDS SET STATUS = ? WHERE ID = ?", ('running', block.scanid))	# set scan status to running
					srtdb.commit()

					scanparams = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (block.scanid,)).fetchone()		# get scan params for the db
					
					nextscan = {}
					
					for key in scanparams:		# build dict object of scan params
						
						nextscan[key.lower()] = scanparams[key]

					_thread.start_new_thread(telescope.donextscan, (nextscan,))		# spawn a new thread running the donextscan() method

				currentscanid = block.scanid

				break

	srtdb.close()

	return currentscanid
	

main()
