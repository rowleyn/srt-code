"""
A class that uses a TCP socket to command the station
through an Ethernet to serial converter.

Author: Nathan Rowley
"""

import socket
import json
import sys
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time

### change these depending on which converter is attached to the telescope and how it is configured ###
SEND_PORT = 23 				# port number (int) of the converter connected to the station
SEND_IP = '192.168.0.8' 	# ip address (str) of the converter connnected to the station
DEFAULT_BUFFER_SIZE = 4096

class CommandStation:

	### instance variables ###


	def __init__(self):
		self.port = SEND_PORT
		self.addr = SEND_IP
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.settimeout(1)

	#######################################################
	'''
	Method that commands the station to move to a particular azimuth and altitude.
	:param az: target azimuth
	:param al: target altitude
	:return:
	'''
	def movebyazal(self, az, al) -> None:

		### get current station position ###

		with open('srtconfig.json') as f:				#get station data from config
			station = json.load(f)
		curaz = station['config']['azal']['azimuth']	#get current azimuth
		cural = station['config']['azal']['altitude']	#get current altitude

		print(str(curaz)+' '+str(cural))

		azset = False
		alset = False
		if curaz == az:		#check to make sure station needs to move
			azset = True
		if cural == al:
			alset = True

		### move station to correct azimuth and altitude ###
		
		if not azset:
			if (az - curaz) > 0:	#determine azimuth increase (direction = 1) or decrease (direction = 0)
				direction = 1
			else:
				direction = 0
			azcount = int(round(abs(az - curaz)*11.7))	#determine azimuth count value for the stamp controller
		elif not alset:
			if (al - cural > 0):	#determine altitude increase (direction = 3) or decrease (direction = 2)
				direction = 3
			else:
				direction = 2
			alcount = int(round(abs(al - cural)*11.7)) 	#determine altitude count value

		self.sock.connect((self.addr,self.port))		#open connection to the serial to ethernet converter

		while (not azset or not alset):

			if not azset:
				message = ' move ' + str(direction) + ' ' + str(azcount) + '\n'	#move to new azimuth
			elif not alset:
				message = ' move ' + str(direction) + ' ' + str(alcount) + '\n'	#move to new altitude
			print(message)
			self.sock.send(message.encode('ascii'))					#send message to stamp via serial to ethernet converter
			print('data sent')

			#receive response from stamp via serial to ethernet converter
			#stamp sends back one thing at a time, so a loop is necessary to receive all the data
			response = []
			for x in range(300):
				try:
					j = self.sock.recv(DEFAULT_BUFFER_SIZE)
					print(j.decode('ascii').strip())
					response.append(j.decode('ascii').strip())
				except OSError:
					break
			print('reply received')
			
			if response[0] == 'M':						#response indicates successful completion of movement
				if not azset:
					azset = True
				elif not alset:
					alset = True
			else:										#response indicates stamp timeout, must resend message with updated values
				if response[1] != response[3]:			#update count based on returned value
					if not azset:
						azcount = azcount - int(response[1])
					elif not alset:
						alcount = alcount - int(response[1])
				else:									#if target is reached despite timeout
					if not azset:
						azset = True
					elif not alset:
						alset = True

		### update current station position ###

		station['config']['azal']['azimuth'] = curaz		#update srtconfig.json with new azimuth and altitude values
		station['config']['azal']['altitude'] = cural
		with open('srtconfig.json','w') as f:					#rewrite srtconfig.json with new information
			json.dump(station,f,indent=4)

		### closes socket ###

		try:
			self.sock.shutdown(socket.SHUT_RDWR)
			self.sock.close()
		except OSError:
			pass  #server already closed socket

	##############################################################
	'''
	Method that takes a source from the config sources list and moves the station to the position of that source.
	:param sourcename: name of source as labelled in the srtconfig.json sources list
	:return:
	'''
	def movebysource(self, sourcename) -> None:

		### get current station information ###

		with open('srtconfig.json') as f:								#get station data from config
			station = json.load(f)

		source = station['config']['sources']['sourcename']				#look up source by name
		source = SkyCoord(source['ras'],source['dec'],frame = 'icrs')	#convert source into astropy SkyCoord object for coord transformation

		location = station['config']['station']							#look up station location data
		location = EarthLocation(lat = location['lat'], lon = location['lon'], height = location['height']) 	#convert location into astropy EarthLocation

		observingtime = Time()#need to figure out how to do this											#create astropy Time object containing current local time

		azalt = AltAz(location = location, obstime = observingtime)		#create AltAz reference frame

		source = source.transform_to(azalt)								#transform source from ras/dec coords to az/alt coords

		### command station with az/alt coords ###

		self.movebyazal(math.floor(source.az),math.floor(source.alt))

	##################################################################
	'''
	Method that commands the station to take a single power reading at a single frequency.
	:para freq: frequency 
	'''
	def readpower(self, freq) -> float:

		### prepare command message ###

		j = int((freq / 0.04) + 0.5)			#calculate integer value j necessary for conversion to byte sections to feed stamp controller
		atten = 0								#currently no means of setting attenuation constant, 0 is default of no attenuation
		b8 = atten
		b9 = j & 0x3f							#upper 3 bits of j
		b10 = (j >> 6) & 0xff					#next byte of j
		b11 = (j >> 14) & 0xff					#lower byte of j

		message = []							#message must be constructed as a list to properly send command
		message.append('freq')
		message.append(b11)
		message.append(b10)
		message.append(b9)
		message.append(b8)

		### send commmand message and receive response ###

		self.sock.connect((self.addr,self.port))
		for e in message:
			self.sock.send(e.encode('ascii'))

		#receive response from stamp via serial to ethernet converter
		#stamp sends back one thing at a time, so a loop is necessary to receive all the data
		response = []
		for x in range(300):
			j = self.sock.recv(DEFAULT_BUFFER_SIZE)
			if from_bytes(j) == -1:
				break
			else:
				response[x] = j.decode('ascii')

		#close the socket if it hasn't been already closed by the server
		#only closes if no more data is being received
		try:
			self.sock.shutdown(socket.SHUT_RDWR)
			self.sock.close()
		except OSError:
			pass  #server already closed socket

		### calculate power from received values and return ###

		w2 = int(response[0])
		w1 = int(response[1]) * 256 + int(response[2])
		power = 1e6 * (w2 / w1)
		gaincor = 1							#currently no means of setting gain correction. likely will be set to 1 anyway
		if atten == 0:
			power = gaincor * power
		else:
			power = gaincor * power * 10	#number 10 used in java code for unknown reasons

		return power




	def sendandreceive(self, message):
		try:
			self.sock.connect((self.addr,self.port))
		except ConnectionError as e:
			print("Issue connecting to " + self.addr + ":" + str(self.port) + " with message: " + message)
			print(e.__class__.__name__+": "+str(e))
			exit(1)
		except OSError as e:
			# Catches other errors including bad server address
			print("Issue connecting to " + self.addr + ":" + str(self.port) + " with message: " + message)
			print(e.__class__.__name__ + ": " + str(e))
			exit(1)
		self.sock.send(message.encode('ascii'))

		returned = self.sock.recv(DEFAULT_BUFFER_SIZE)
		response = returned.decode('ascii')

		# Close the socket if it hasn't been already closed by the server
		# Only closes if no more data is being received
		try:
			self.sock.shutdown(socket.SHUT_RDWR)
			self.sock.close()
		except OSError:
			pass  # Server already closed socket

		return response

### main function for testing ###

def main():

	command = CommandStation()
	'''
	print('test: azimuth only, small increase/decrease, large increase/decrease')
	command.movebyazal(200,90)			#small azimuth increase
	command.movebyazal(180,90)			#small azimuth decrease
	command.movebyazal(360,90)			#large azimuth increase
	command.movebyazal(180,90)			#large azimuth decrease
	'''
	print('test: altitude only, small increase/decrease, large increase/decrease')
	command.movebyazal(180,120)			#small altitude increase
	command.movebyazal(180,90)			#small altitude decrease
	command.movebyazal(180,180)			#large altitude increase
	command.movebyazal(180,90)			#large altitude decrease

	print('test: azimuth and altitude same direction, small increase/decrease, large increase/decrease')
	command.movebyazal(200,120)			#small azimuth and altitude increase
	command.movebyazal(180,90)			#small azimuth and altitude decrease
	command.movebyazal(360,180)			#large azimuth and altitude increase
	command.movebyazal(180,90)			#large azimuth and altitude decrease

	print('test: azimuth and altitude opposite direction, small increase/decrease, large increase/decrease')
	command.movebyazal(200,30)			#small azimuth increase and small altitude decrease
	command.movebyazal(180,90)			#small azimuth decrease and small altitude increase
	command.movebyazal(360,0)			#large azimuth increase and large altitude decrease
	command.movebyazal(180,90)			#large azimuth decrease and large altitude increase

main()