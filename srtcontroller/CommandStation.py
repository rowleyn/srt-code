'''
A class that uses a serial port to command the telescope's
stamp controller. Handles both movement and measurement commands.

Author: Nathan Rowley
Date: June 2018
'''

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import time
import sqlite3
import serial
import math

class CommandStation:
	
	database_location = '../srtdatabase/srtdata.db'
	
	# Method that commands the station to move to a particular azimuth and altitude.
	#
	# :param newaz: target azimuth
	# :param newal: target altitude
	# :return successful: a boolean indicating whether movement was successfully completed
	def movebyazal(self, newaz, newal):

		### get current station position ###

		srtdb = sqlite3.connect(database_location)	# establish a connection and cursor into the database
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

			azcount = int(math.floor(abs(newaz - curaz) * 11.7))	# determine azimuth count value for the stamp controller

		if not alset:

			if (newal - cural > 0):	# determine altitude increase (direction = 3) or decrease (direction = 2)

				aldirection = 3

			else:

				aldirection = 2

			alcount = int(math.floor(abs(newal - cural) * 11.7)) 	# calculate altitude count value

		ser = serial.Serial('/dev/ttyAMA0', baudrate = 2400, timeout = 1)		# initialize and open a serial port to the stamp controller

		while not azset or not alset:					# while loop will always set azimuth first if not already set, then altitude if not already set

			if not azset:

				message = ' move ' + str(azdirection) + ' ' + str(azcount) + '\n'	# move to new azimuth

			elif not alset:

				message = ' move ' + str(aldirection) + ' ' + str(alcount) + '\n'	# move to new altitude

			print(message)

			ser.write(message.encode('ascii'))		# write message to the serial port

			print('movement data sent')

			received = False
			response = ''

			while not received:		# loop to receive response one byte at a time

				rbyte = ser.read()	# read from serial port

				if len(rbyte) > 0:	# if a byte was received, decode and append to response

					response += rbyte.decode('ascii')

				else:	# if no byte was received and a response has been received already, stop reading

					if len(response) > 0:

						received = True

			ser.close()		# close the serial port

			# response = response.strip().split()

			print('reply received')
			
			if response == message:
				
				curaz = newaz
				cural = newal
				print(str(curaz) + ' ' + str(cural))
				break
			
			if response[0] == 'M':		# response indicates successful completion of movement

				if not azset:

					curaz = newaz
					azset = True

				elif not alset:

					cural = newal
					alset = True

			else:					# response indicates stamp timeout, set telescope status to timeout and exit

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

		return successful

	
	# Method that commands the station to take a single power reading at a single frequency.
	#
	# :para freq: frequency at which to takea reading
	# :return power: float containing the power reading at the frequency freq
	def readpower(self, freq):

		### prepare command message ###

		j = int((freq / 0.04) + 0.5)			# calculate integer value j necessary for conversion to byte sections to feed stamp controller
		atten = 0								# currently no means of setting attenuation constant, 0 is default of no attenuation
		b8 = atten
		b9 = j & 0x3f							# upper 3 bytes of j
		b10 = (j >> 6) & 0xff					# next byte of j
		b11 = (j >> 14) & 0xff					# lower byte of j

		# message = []							# message must be constructed as a list to properly send command
		# message.append('freq')
		# message.append('f')
		# message.append('r')
		# message.append('e')
		# message.append('q')
		# message.append(b11)
		# message.append(b10)
		# message.append(b9)
		# message.append(b8)
		
		message = ' freq ' + str(b11) + ' ' + str(b10) + ' ' + str(b9) + ' ' + str(b8) + '\n'

		print(message)

		ser = serial.Serial('/dev/ttyAMA0', baudrate = 2400, timeout = 1)	# initialize and open a serial port to the stamp controller

		# for e in message:

		# 	ser.write(e.encode('ascii'))
		
		ser.write(message.encode('ascii'))

		received = False
		# response = []
		
		response = ''

		while not received:		# loop to receive response one byte at a time

			rbyte = ser.read()	# read from serial port

			if len(rbyte) > 0:

				# response.append(int(rbyte))
				response += rbyte.decode('ascii')

			else:

				if len(response) > 0:

					received = True

		ser.close()

		### calculate power from received values and return ###
		
		if response == message:
			
			print('power received')

			response = [100, 1, 244]
			
		else:
			
			print('power failed')
			
			return 0

		w2 = response[0]
		w1 = response[1] * 256 + response[2]
		power = 1e6 * (w2 / w1)				# calculate power from response values
		gaincor = 1							# currently no means of setting gain correction. likely will be set to 1 anyway
		if atten == 0:
			power = gaincor * power
		else:
			power = gaincor * power * 10	# number 10 used in java code for unknown reasons

		return power

### main function for testing ###

# def main():

# 	command = CommandStation()

# 	print('test: azimuth only, small increase/decrease, large increase/decrease')
# 	command.movebyazal(200,90)			# small azimuth increase
# 	command.movebyazal(180,90)			# small azimuth decrease
# 	command.movebyazal(360,90)			# large azimuth increase
# 	command.movebyazal(180,90)			# large azimuth decrease

# 	print('test: altitude only, small increase/decrease, large increase/decrease')
# 	command.movebyazal(180,120)			# small altitude increase
# 	command.movebyazal(180,90)			# small altitude decrease
# 	command.movebyazal(180,180)			# large altitude increase
# 	command.movebyazal(180,90)			# large altitude decrease

# 	print('test: azimuth and altitude same direction, small increase/decrease, large increase/decrease')
# 	command.movebyazal(200,120)			# small azimuth and altitude increase
# 	command.movebyazal(180,90)			# small azimuth and altitude decrease
# 	command.movebyazal(360,180)			# large azimuth and altitude increase
# 	command.movebyazal(180,90)			# large azimuth and altitude decrease

# 	print('test: azimuth and altitude opposite direction, small increase/decrease, large increase/decrease')
# 	command.movebyazal(200,30)			# small azimuth increase and small altitude decrease
# 	command.movebyazal(180,90)			# small azimuth decrease and small altitude increase
# 	command.movebyazal(360,0)			# large azimuth increase and large altitude decrease
# 	command.movebyazal(180,90)			# large azimuth decrease and large altitude increase

#main()
