'''
This module initializes the database for the website and telescope controller.
If the database does not already exist, the module initializes it along with
the proper tables and populates the CONFIG and STATUS tables.

Author: Nathan Rowley
Date: September 2018
'''

import sqlite3
from os.path import isfile

if not isfile('../srtdatabase/srtdata.db'):				# check if database exists

	srt = sqlite3.connect('../srtdatabase/srtdata.db')	# initialize database

	### initialize tables ###
	
	### CONFIG table contains basic telescope state information ###
	srt.execute('''CREATE TABLE CONFIG(
		NAME		TEXT	NOT NULL,
		LAT			REAL	NOT NULL,
		LON			REAL	NOT NULL,
		HEIGHT		REAL	NOT NULL,
		AZ			REAL	NOT NULL,
		AL			REAL	NOT NULL,
		AZLOWER		REAL	NOT NULL,
		AZUPPER		REAL	NOT NULL,
		ALLOWER		REAL	NOT NULL,
		ALUPPER		REAL	NOT NULL,
		FREQLOWER	REAL	NOT NULL,
		FREQUPPER	REAL	NOT NULL);''')

	### SCANIDS table contains list of scan ids, names and statuses ###
	srt.execute('''CREATE TABLE SCANIDS(
		ID INT PRIMARY KEY	NOT NULL,
		NAME		TEXT	NOT NULL,
		STATUS 		TEXT	NOT NULL);''')

	### SCANPARAMS table contains scan parameters for running scans ###
	srt.execute('''CREATE TABLE SCANPARAMS(
		ID 			INT		NOT NULL,
		TYPE		TEXT	NOT NULL,
		SOURCE		TEXT	NOT NULL,
		RAS			TEXT	NOT NULL,
		DEC			TEXT	NOT NULL,
		DURATION	TEXT	NOT NULL,
		FREQLOWER	REAL	NOT NULL,
		FREQUPPER	REAL	NOT NULL,
		STEPNUM		INT 	NOT NULL);''')

	### SCANRESULTS table contains data from completed scans ###
	srt.execute('''CREATE TABLE SCANRESULTS(
		ID 		INT 	NOT NULL,
		DATA 	BLOB	NOT NULL);''')

	### SCANHISTORY table contains date information of scan success or failure ###
	srt.execute('''CREATE TABLE SCANHISTORY(
		ID 		INT 	NOT NULL,
		NAME	TEXT	NOT NULL,
		TYPE 	TEXT	NOT NULL,
		DAY		INT 	NOT NULL,
		MONTH	INT 	NOT NULL,
		YEAR	INT 	NOT NULL);''')

	### SCHEDULE table contains the current scan schedule ###
	srt.execute('''CREATE TABLE SCHEDULE(
		ID 			INT		NOT NULL,
		STARTTIME	TEXT	NOT NULL,
		ENDTIME		TEXT	NOT NULL);''')

	### SOURCES table contains list of source names and positions ###
	srt.execute('''CREATE TABLE SOURCES(
		NAME TEXT PRIMARY KEY	NOT NULL,
		RAS				TEXT	NOT NULL,
		DEC				TEXT	NOT NULL);''')

	### STATUS table contains current telescope status ###
	srt.execute('''CREATE TABLE STATUS(
		ID		INT 	NOT NULL,
		CODE	TEXT	NOT NULL);''')
	
	### populate STATUS and CONFIG tables ###
	srt.execute("INSERT INTO STATUS VALUES (?,?)", (-1,'ok'))

	srt.execute("INSERT INTO CONFIG (NAME,LAT,LON,HEIGHT,AZ,AL,AZLOWER,AZUPPER,ALLOWER,ALUPPER,FREQLOWER,FREQUPPER) \
			VALUES	('Carleton Small Radio Telescope', 44.45, -93.16, 0, 180, 90, 0, 360, 0, 180, 0, 10000 )")

	srt.commit()

	srt.close()
