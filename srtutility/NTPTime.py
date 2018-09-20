'''
A helper class for retreiving time data from ntp servers.

Author: Nathan Rowley
Date: August 2018
'''

import ntplib
from ntplib import NTPException
import datetime
import pytz

class NTPTime:
	
	# Initializes a new object with default and backup servers.
	# Change these to servers that are nearby for best performance.
	def __init__(self):
		
		self.NTP_SERVER = 'ntp.carleton.edu'
		self.BACKUP_SERVER = '0.us.pool.ntp.org'
		self.client = ntplib.NTPClient()


	def getcurrenttime(self):
		
		received = False
		
		try:
			
			ntptime = self.client.request(self.NTP_SERVER, version = 4)	# get current time from the default server
			unixtime = ntptime.tx_time									# get unix time from ntp packet
			received = True
			
		except NTPException as e:
			
			received = False
			
		if not received:
			
			try:
			
				ntptime = c.request(self.BACKUP_SERVER, version = 4)	# get current time from the backup server
				unixtime = ntptime.tx_time								# get unix time from ntp packet
				received = True
			
			except NTPException as e:
			
				received = False
			
		if not received:
			
			unixtime = datetime.now(tz=pytz.utc).timestamp()	# get timestamp by converting from utc

		return unixtime
