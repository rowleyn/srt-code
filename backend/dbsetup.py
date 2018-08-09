
import sqlite3
import io
import zipfile

srt = sqlite3.connect('srtdata.db')


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

srt.execute('''CREATE TABLE SCANIDS(
	ID INT PRIMARY KEY	NOT NULL,
	NAME		TEXT	NOT NULL,
	STATUS 		TEXT	NOT NULL);''')

srt.execute('''CREATE TABLE SCANPARAMS(
	ID 			INT		NOT NULL,
	TYPE		TEXT	NOT NULL,
	SOURCE		TEXT	NOT NULL,
	RAS			TEXT	NOT NULL,
	DEC			REAL	NOT NULL,
	DURATION	TEXT	NOT NULL,
	FREQLOWER	REAL	NOT NULL,
	FREQUPPER	INT		NOT NULL,
	STEPNUM		REAL	NOT NULL);''')

srt.execute('''CREATE TABLE SCANRESULTS(
	ID 		INT 	NOT NULL,
	DATA 	BLOB	NOT NULL);''')

srt.execute('''CREATE TABLE SCANHISTORY(
	ID 		INT 	NOT NULL,
	NAME	TEXT	NOT NULL,
	TYPE 	TEXT	NOT NULL,
	DAY		INT 	NOT NULL,
	MONTH	INT 	NOT NULL,
	YEAR	INT 	NOT NULL);''')

srt.execute('''CREATE TABLE SCHEDULE(
	ID 			INT		NOT NULL,
	STARTTIME	TEXT	NOT NULL,
	ENDTIME		TEXT	NOT NULL);''')

srt.execute('''CREATE TABLE SOURCES(
	NAME TEXT PRIMARY KEY	NOT NULL,
	RAS				TEXT	NOT NULL,
	DEC				REAL	NOT NULL);''')

srt.execute('''CREATE TABLE STATUS(
	ID		INT 	NOT NULL,
	CODE	TEXT	NOT NULL);''')

# srt.execute("INSERT INTO HISTORY (ID,NAME,TYPE,DAY,MONTH,YEAR,STATUS) \
# 		VALUES 	(10,'testhistory1','drift',27,7,2018,'complete')")

# srt.execute("INSERT INTO HISTORY (ID,NAME,TYPE,DAY,MONTH,YEAR,STATUS) \
# 		VALUES 	(20,'testhistory2','track',27,7,2018,'timeout')")

# srt.execute("INSERT INTO HISTORY (ID,NAME,TYPE,DAY,MONTH,YEAR,STATUS) \
# 		VALUES 	(30,'testhistory1','drift',26,7,2018,'outofbounds')")

# srt.execute("INSERT INTO HISTORY (ID,NAME,TYPE,DAY,MONTH,YEAR,STATUS) \
# 		VALUES 	(40,'testhistory1','drift',25,7,2018,'invalidposition')")

# srt.execute("INSERT INTO HISTORY (ID,NAME,TYPE,DAY,MONTH,YEAR,STATUS) \
# 		VALUES 	(50,'testhistory1','drift',25,7,2018,'invalidsource')")

# srt.execute("INSERT INTO HISTORY (ID,NAME,TYPE,DAY,MONTH,YEAR,STATUS) \
# 		VALUES 	(60,'testhistory1','drift',24,7,2018,'complete')")

# srt.execute("INSERT INTO SCANS (ID,NAME,DAY,MONTH,YEAR,DATA) \
# 		VALUES	(1,'testscan1', 11, 7, 2018, ?)", (b"This is a test fits file.",))

# srt.execute("INSERT INTO STATUS (ID,ENDTIME,PAUSED) \
# 		VALUES	(1234567890,0,0)")

# srt.execute("INSERT INTO CONFIG (NAME,LAT,LON,HEIGHT,AZ,AL,AZLOWER,AZUPPER,ALLOWER,ALUPPER,FREQLOWER,FREQUPPER) \
# 		VALUES	('Carleton Small Radio Telescope', 0, 0, 0, 180, 90, 0, 360, 0, 180, 0, 10000 )")

# srt.execute("INSERT INTO QUEUE (ID,NAME,TYPE,SOURCE,RAS,DEC,DURATION,FREQLOWER,FREQUPPER,STEPNUM) \
# 		VALUES	(1234567890, 'test1', 'track', 'crab', '0h0m0s', 0, '01h01m01s', 1400, 1440, 1000 )")

# srt.execute("INSERT INTO QUEUE (ID,NAME,TYPE,SOURCE,RAS,DEC,DURATION,FREQLOWER,FREQUPPER,STEPNUM) \
# 		VALUES	(0987654321, 'test2', 'drift', 'source', '0h0m0s', 0, '01h01m01s', 1400, 1440, 1000 )")

# srt.execute("INSERT INTO SOURCES (NAME,RAS,DEC) \
# 		VALUES	('test', '0h0m0s', 0)")

# srt.commit()

# b = io.BytesIO(b"")

# f = zipfile.ZipFile(b, 'w')

# scans = srt.execute("SELECT * FROM SCANS")
# for row in scans:
# 	print(row)
# 	print(row[4])
# 	f.writestr('testfile.fits', row[5])
# 	print(f.read('testfile.fits'))
# 	print(b.getvalue())

# stationdata = srt.execute("SELECT * FROM CONFIG")
# for row in stationdata:
# 	print(row)

# scans = srt.execute("SELECT * FROM QUEUE")
# for row in scans:
# 	print(row)

# sourcelist = srt.execute("SELECT * FROM SOURCES")
# for source in sourcelist:
# 	print(source)

# status = srt.execute("SELECT * FROM STATUS")
# for values in status:
# 	print(values)

# history = srt.execute("SELECT * FROM HISTORY")
# for scan in history:
# 	print(scan)

srt.close()