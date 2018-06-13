"""
A class that uses a TCP socket to command the telescope
through an Ethernet to serial converter.
Based on the sport.java class from the Java implementation of the SRT code.
Author: Nathan Rowley
"""

import time
import socket

### change these depending on which converter is attached to the telescope and how it is configured ###
SEND_PORT = 23 				# port number (int) of the converter connected to the telescope
SEND_IP = '192.168.0.8' 	# ip address (str) of the converter connnected to the telescope
DEFAULT_BUFFER_SIZE = 4096

class CommandTelescope:

	### instance variables ###

	def __init__(self):
		self.port = SEND_PORT
		self.addr = SEND_IP
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.settimeout(5)

	def sendandreceive(self, message):
		try:
			self.sock.connect((self.addr,self.port))
			print('connection successful')
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

def main():

	commander = CommandTelescope()
	print(commander.sendandreceive('hello world'))

main()