'''
The code that maintains the telescope's schedule of scans and issues the order to perform scans.
It is the main execution loop for the telescope-side code.

Author: Nathan Rowley
Date: August 2018
'''

import Scan
import Schedule
import ntplib
import datetime
import time
import _thread
from astral import Astral
from astropy.time import Time


NTP_SERVER = 'ntp.carleton.edu'		# NTP server for time retrieval. Change to suit your needs


'''
The main method of the telescope code. All telescope actions ultimately originate from this method.
'''
def main():

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	telescope = Scan()			# initialize a Scan object for running scans

	config = cur.execute("SELECT * FROM CONFIG LIMIT 1").fetchone()		# fetch config data from the db

	a = Astral()					# initalize an Astral object for computer day and night times

	today = datetime.date.today()	# get today's date

	daytimes = a.daylight_utc(today, config['lat'], config['lon'])			# compute date and night times in UTC using the Astral object
	nighttimes = a.night_utc(today, config['lat'], config['lon'])

	dusk = Time(nighttimes[0], format = 'datetime', scale = 'utc').unix 	# transform times to unix time using astropy Time objects
	dawn = Time(nighttimes[1], format = 'datetime', scale = 'utc').unix
	sunrise = Time(daytimes[0], format = 'datetime', scale = 'utc').unix
	sunset = Time(daytimes[1], format = 'datetime', scale = 'utc').unix

	dayschedule = Schedule(sunrise + 7200, sunset - 7200)					# instantiate day and night schedules
	nightschedule = Schedule(dusk, dawn)

	currentscanid = None


	### MAIN EXECUTION LOOP FOR TELESCOPE-SIDE CODE ###

	while True:

		time.sleep(0.5)			# sleep for half a second to reduce looping speed


		### set whether it is day or night ###

		curtime = getcurrenttime()

		if curtime >= dusk and curtime <= dawn:

			currentschedule = nightschedule

		else:

			currentschedule = dayschedule


		### create new schedules if current schedules are completed ###

		config = cur.execute("SELECT * FROM CONFIG LIMIT 1").fetchone()		# get config data from the db

		newday = datetime.time.today()										# get today's date

		if newday.day != today.day or newday.month != today.month or newday.year != today.year:	# if the day has changed, create new day schedule

			today = newday

			daytimes = a.daylight_utc(today, config['lat'], config['lon'])

			sunrise = Time(daytimes[0], format = 'datetime', scale = 'utc').unix
			sunset = Time(daytimes[1], format = 'datetime', scale = 'utc').unix

			dayschedule = Schedule(sunrise + 7200, sunset - 7200)

		if curtime > dawn:													# if the night if over, create new night schedule

			nighttimes = a.night_utc(today, config['lat'], config['lon'])

			dusk = Time(nighttimes[0], format = 'datetime', scale = 'utc').unix
			dawn = Time(nighttimes[1], format = 'datetime', scale = 'utc').unix

			nightschedule = Schedule(dusk, dawn)


		### remove cancelled scans from schedules ###

		cancelscans(dayschedule)
		cancelscans(nightschedule)


		### insert a new scan into the schedule ###

		newscan = cur.execute("SELECT * FROM SCANIDS WHERE STATUS = ?", ('submitted',)).fetchone()

		if newscan != None:

			scanparams = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (newscan['id'],)).fetchone()

			if scanparams['source'] == 'sun':

				status = dayschedule.schedulescan(scanparams['id'], curtime)

			else:

				status = nightschedule.schedulescan(scanparams['id'], curtime)

			cur.execute("UPDATE SCANIDS WHERE ID = ? SET STATUS = ?", (newscan['id'], status))
			srtdb.commit()


		### remove current scan from the schedule when it finishes ###

		if currentscanid != None:

			currentscan = cur.execute("SELECT * FROM SCANIDS WHERE ID = ?", (currentscanid,)).fetchone()

			if currentscan == None or currentscan['status'] != 'running':

				cur.execute("DELETE FROM SCHEDULE WHERE ID = ?", (currentscanid,))
				srtdb.commit()

				currentschedule.deschedulescan(currentscanid)

				currentscanid = None


		### run the next scan in the schedule ###

		currentscanid = runscan(currentschedule)





'''
Helper method that checks for any cancelled scans that must be removed from a schedule.

:param schedule: the schedule to check for cancelled scans
:return:
'''
def cancelscans(schedule):

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	today = datetime.date.today()

	for block in schedule:						# check all blocks for cancellation

		if block.scanid != None:

			status = cur.execute("SELECT * FROM SCANIDS WHERE ID = ?", block.scanid).fetchone()		# fetch scan status from the db

			if status['status'] == 'cancelled':

				params = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (block.scanid,))		# if scan is cancelled, remove from the schedule and add to history

				cur.execute("DELETE FROM SCHEDULE WHERE ID = ?", (block.scanid,))
				cur.execute("INSERT INTO SCANHISTORY VALUES (?,?,?,?,?,?)", (block.scanid, params['name'], params['type'], today.day, today.month, today.year))
				srtdb.commit()

				schedule.deschedulescan(block.scanid)

	srtdb.close()


'''
Helper method that checks a schedule and runs a scan scheduled at the current time

:param schedule: the schedule to check for scans to run
:return currentscanid: the id of the currently running scan
'''
def runscan(schedule)

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	curtime = getcurrenttime()

	currentscanid = None

	for block in schedule:					# check eachblock for start time

		if block.scanid != None:

			if curtime >= block.starttime - 5 and curtime <= block.starttime + 5:		# if the start time is now, run the scan

				status = cur.execute("SELECT * FROM STATUS").fetchone()

				if status['code'] == 'timeout':

					today = datetime.date.today()

					params = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (block.scanid,))

					cur.execute("INSERT INTO SCANHISTORY VALUES (?,?,?,?,?,?)", (block.scanid, params['name'], params['type'], today.day, today.month, today.year))
					cur.execute("UPDATE SCANIDS WHERE ID = ? SET STATUS = ?", (block.scanid, 'timeout'))
					srtdb.commit()

				else:

					cur.execute("UPDATE SCANIDS WHERE ID = ? SET STATUS = ?", (block.scanid, 'running'))	# set scan status to running
					srtdb.commit()

					nextscan = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (block.scanid,))		# get scan params for the db

					_thread.start_new_thread(telescope.donextscan, (nextscan,))				# spawn a new thread running the donextscan() method

				currentscanid = block.scanid

				break

	srtdb.close()

	return currentscanid


'''
Helper method to get the current time from an NTP server.

:return unixtime: current unix time
'''
def getcurrenttime():

	c = ntplib.NTPClient()								# initialize ntplib client
	ntptime = c.request(NTP_SERVER, version = 4)		# get current time from Carleton's NTP server
	unixtime = ntptime.tx_time							# convert ntp time to unix time

	return unixtime