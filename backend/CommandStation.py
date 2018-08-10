'''
A class that uses a TCP socket to command the station
through an Ethernet to serial

Author: Nathan Rowley
Date: June 2018
'''

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import socket
import time
import ntplib
import sqlite3
import serial


### change these depending on which converter is attached to the telescope and how it is configured ###

# SEND_PORT = 23 				# port number (int) of the converter connected to the station
# SEND_IP = '192.168.0.8' 	# ip address (str) of the converter connnected to the station
# DEFAULT_BUFFER_SIZE = 4096
# DEFAULT_TIMEOUT = 10

class CommandStation:

	def __init__(self):
		# self.port = SEND_PORT
		# self.addr = SEND_IP
		# self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# self.sock.settimeout(DEFAULT_TIMEOUT)

	
	'''
	Method that commands the station to move to a particular azimuth and altitude.

	:param newaz: target azimuth
	:param newal: target altitude
	:return successful: a boolean indicating whether movement was successfully completed
	'''
	def movebyazal(newaz, newal) -> bool:

		### get current station position ###

		srtdb = sqlite3.connect('srtdata.db')	# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		configdata = cur.execute("SELECT * FROM CONFIG").fetchone()			# retrieve config data from the database

		curaz = configdata['az']				# get current azimuth and altitude
		cural = configdata['al']

		print(str(curaz) + ' ' + str(cural))

		azset = False
		alset = False

		successful = True

		if curaz == newaz:		# check to make sure station needs to move

			azset = True

		if cural == newal:

			alset = True

		### move station to correct azimuth and altitude ###
		
		if not azset:

			if (newaz - curaz) > 0:	# determine azimuth increase (direction = 1) or decrease (direction = 0)

				azdirection = 1

			else:

				azdirection = 0

			azcount = int(floor(abs(newaz - curaz) * 11.7))	# determine azimuth count value for the stamp controller

		if not alset:

			if (newal - cural > 0):	# determine altitude increase (direction = 3) or decrease (direction = 2)

				aldirection = 3

			else:

				aldirection = 2

			alcount = int(floor(abs(newal - cural) * 11.7)) 	# calculate altitude count value

		ser = serial.Serial('/dev/ttyAMA0', baudrate = 2400, timeout = 1)

		# self.sock.connect((self.addr,self.port))		# open connection to the serial to ethernet converter

		while not azset or not alset:					# while loop will always set azimuth first if not already set, then altitude if not already set

			if not azset:

				message = ' move ' + str(azdirection) + ' ' + str(azcount) + '\n'	# move to new azimuth

			elif not alset:

				message = ' move ' + str(aldirection) + ' ' + str(alcount) + '\n'	# move to new altitude

			print(message)

			ser.open()

			ser.write(message.encode('ascii'))

			# self.sock.send(message.encode('ascii'))					# send message to stamp via serial to ethernet converter
			print('data sent')

			received = False
			response = ''

			while not received:

				rbyte = ser.read()

				if len(rbyte) > 0:

					response += rbyte.decode('ascii')

				else:

					if len(response) > 0:

						received = True

			ser.close()
			
			# response = self.sock.recv(DEFAULT_BUFFER_SIZE).decode('ascii').strip().split()		# receive and format response data

			response = response.strip().split()

			print('reply received')
			
			if response[0] == 'M':								# response indicates successful completion of movement

				if not azset:

					curaz = newaz
					azset = True

				elif not alset:

					cural = newal
					alset = True

			else:												# response indicates stamp timeout, pause scan and wait until it is unpaused

				cur.execute("UPDATE STATUS SET CODE = ?", ('timeout',))

				if not azset:

					if azdirection == 1:

						curaz = int(floor(curaz + (int(response[1]) / 11.7)))

					else:

						curaz = int(floor(curaz - (int(response[1]) / 11.7)))

				else:

					if aldirection == 3:

						cural = int(floor(cural - (int(response[1]) / 11.7)))

					else:

						cural = int(floor(cural - (int(response[1]) / 11.7)))

				successful = False

				break

		### update current station position ###

		cur.execute("UPDATE CONFIG SET AZ = ?, AL = ?", (curaz, cural))		# update position values in database
		srtdb.commit()

		srtdb.close()														# database connection no longer needed

		### close socket ###

		# try:
		# 	self.sock.shutdown(socket.SHUT_RDWR)
		# 	self.sock.close()
		# except OSError:
		# 	pass  				# server already closed socket

		return successful

	
	'''
	Method that takes a source from the config sources list and moves the station to the position of that source.

	:param sourcename: name of source as labelled in the SOURCES table in srtdata.db
	:return:
	'''
	def movebysource(self, sourcename) -> None:

		### get current station information ###

		srtdb = sqlite3.connect('srtdata.db')	# establish a connection and cursor into the database
		srtdb.row_factory = sqlite3.Row
		cur = srtdb.cursor()

		configdata = cur.execute("SELECT * FROM CONFIG").fetchone()							# retrieve config data from the database
		sourcedata = cur.execute("SELECT * FROM SOURCES WHERE NAME = ?", (sourcename,))		# retrieve source data from the database

		source = SkyCoord(sourcedata['ras'],sourcedata['dec'],frame = 'icrs')				# convert source into astropy SkyCoord object for coord transformation

		location = EarthLocation(lat = configdata['lat'], lon = configdata['lon'], height = configdata['height']) 	# convert location into astropy EarthLocation

		srtdb.close()													# database connection no longer needed

		c = ntplib.NTPClient()
		ntptime = c.request('ntp.carleton.edu',version = 4)				# get current time from Carleton's NTP server
		unixtime = ntptime.tx_time - 18000								# convert ntp time to unix time

		observingtime = Time(unixtime,format = 'unix')					# create astropy Time object using converted ntp time

		azalt = AltAz(location = location, obstime = observingtime)		# create AltAz reference frame

		source = source.transform_to(azalt)								# transform source from ras/dec coords to az/alt coords

		### command station with az/alt coords ###

		self.movebyazal(source.az,source.alt)

	
	'''
	Method that commands the station to take a single power reading at a single frequency.

	:para freq: frequency at which to takea reading
	:return power: float containing the power reading at the frequency freq
	'''
	def readpower(freq) -> float:

		### prepare command message ###

		j = int((freq / 0.04) + 0.5)			# calculate integer value j necessary for conversion to byte sections to feed stamp controller
		atten = 0								# currently no means of setting attenuation constant, 0 is default of no attenuation
		b8 = atten
		b9 = j & 0x3f							# upper 3 bits of j
		b10 = (j >> 6) & 0xff					# next byte of j
		b11 = (j >> 14) & 0xff					# lower byte of j

		message = []							# message must be constructed as a list to properly send command
		message.append('freq')
		message.append(b11)
		message.append(b10)
		message.append(b9)
		message.append(b8)

		### send commmand message and receive response ###

		# self.sock.connect((self.addr,self.port))
		# for e in message:
		# 	self.sock.send(e.encode('ascii'))

		ser = serial.Serial('/dev/ttyAMA0', baudrate = 2400, timeout = 1)

		ser.open()

		for e in message:

			ser.write(e.encode('ascii'))

		received = False
		response = []

		while not received:

			rbyte = ser.read()

			if len(rbyte) > 0:

				response.append(int(rbyte))

			else:

				if len(response) > 0:

					received = True

		ser.close()

		# deprecated
		'''
		# receive response from stamp via serial to ethernet converter
		# stamp sends back one thing at a time, so a loop is necessary to receive all the data
		response = []
		for x in range(300):
			try:
				j = self.sock.recv(DEFAULT_BUFFER_SIZE)
				print(j.decode('ascii').strip())
				response.append(j.decode('ascii').strip())
			except OSError:
				break											# TCP socket times out after stamp stops sending
		'''

		# response = self.sock.recv(DEFAULT_BUFFER_SIZE).decode('ascii').strip().split()		# receive and format response data

		### close socket ###

		# try:
		# 	self.sock.shutdown(socket.SHUT_RDWR)
		# 	self.sock.close()
		# except OSError:
		# 	pass  				# server already closed socket

		### calculate power from received values and return ###

		w2 = response[0]
		w1 = response[1] * 256 + response[2]
		power = 1e6 * (w2 / w1)
		gaincor = 1							# currently no means of setting gain correction. likely will be set to 1 anyway
		if atten == 0:
			power = gaincor * power
		else:
			power = gaincor * power * 10	# number 10 used in java code for unknown reasons

		return power

### main function for testing ###

def main():

	command = CommandStation()

	print('test: azimuth only, small increase/decrease, large increase/decrease')
	command.movebyazal(200,90)			# small azimuth increase
	command.movebyazal(180,90)			# small azimuth decrease
	command.movebyazal(360,90)			# large azimuth increase
	command.movebyazal(180,90)			# large azimuth decrease

	print('test: altitude only, small increase/decrease, large increase/decrease')
	command.movebyazal(180,120)			# small altitude increase
	command.movebyazal(180,90)			# small altitude decrease
	command.movebyazal(180,180)			# large altitude increase
	command.movebyazal(180,90)			# large altitude decrease

	print('test: azimuth and altitude same direction, small increase/decrease, large increase/decrease')
	command.movebyazal(200,120)			# small azimuth and altitude increase
	command.movebyazal(180,90)			# small azimuth and altitude decrease
	command.movebyazal(360,180)			# large azimuth and altitude increase
	command.movebyazal(180,90)			# large azimuth and altitude decrease

	print('test: azimuth and altitude opposite direction, small increase/decrease, large increase/decrease')
	command.movebyazal(200,30)			# small azimuth increase and small altitude decrease
	command.movebyazal(180,90)			# small azimuth decrease and small altitude increase
	command.movebyazal(360,0)			# large azimuth increase and large altitude decrease
	command.movebyazal(180,90)			# large azimuth decrease and large altitude increase

#main()