'''
A class that performs various types of scans by looping the methods
found in CommandStation.py.

Author: Nathan Rowley
'''

import CommandStation
import json
from astropy.table import Table

class Scan:

	def __init__(self):
		self.station = CommandStation()

	'''
	Method to take a single data point at a single frequency for a single source.

	:param source: name of source to measure
	:param freq: frequency at which to measure in MHz
	:return power: power measurement in degrees Kelvin
	'''
	def singlescan(self,source,freq) -> float:

		self.station.movebysource(source)		# point station at source

		power = self.station.readpower(freq)	# read power at frequency freq

		return power

	'''
	Method to take data points across the whole station spectrum for a single source.

	:param source: name of source to measure
	:return spectrum: an astropy Table containing a spectrum measurement
	'''
	def singlespectrum(self,source) -> Table:

		self.station.movebysource(source)		# point station at source

		with open('srtconfig.json') as f:		# load in config data
			station = json.load(f)

		lowf  = station['config']['freqrange']['lower']		# set spectrum range
		highf = station['config']['freqrange']['upper']

		spectrumfreq = []									# create lists to store spectrum data
		spectrumpow  = []

		for freq in range(lowf,highf,0.04):						# sweep through frequencies in range, taking 40 kHz steps

			spectrumfreq.append(freq)							# record frequency

			spectrumpow.append(self.station.readpower(freq))	# record measured power

		spectrum = Table([spectrumfreq, spectrumpow], names = ('frequency - MHz', 'power - K'))	# convert spectrum data to an astropy Table

		return spectrum

	'''
	Method to track and take data points on a single source at a single frequency for a specified amount of time.

	:param source: name of source to track and measure
	:param freq: frequency at which to measure in MHz
	:param time: amount of time to track in seconds
	:return :
	'''
	def trackscan(self, source, freq, time):


	'''
	Method to track and take data points on a single source across the whole station spectrum for a specific amount of time.

	:param source: name of source to track and measure
	:param time: amount of time to track in seconds
	:return :
	'''
	def trackspectrum(self, source, time):


	'''
	Method to take a drift scan at a single frequency for a specific amount of time.

	:param pos: tuple containing azimuth and altitude of drift position
	:param freq: frequency at which to measure in MHz
	:param time: amount of time to take data in seconds
	:return :
	'''
	def driftscan(self, pos, freq, time):


	'''
	Method to take a drift scan across the whole station spectrum for a specific amount of time.

	:param pos: tuple containing azimuth and altitude of drift position
	:param time: amount fo time to take data in seconds
	:return :
	'''
	def driftspectrum(self, pos, time):

