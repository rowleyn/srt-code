
import sqlite3

srtdb = sqlite3.connect('../srtdatabase/srtdata.db')
cur = srtdb.cursor()

config = cur.execute("SELECT * FROM CONFIG").fetchall()
print(config)

scanids = cur.execute("SELECT * FROM SCANIDS").fetchall()
print(scanids)

scanparams = cur.execute("SELECT * FROM SCANPARAMS").fetchall()
print(scanparams)

scanresults = cur.execute("SELECT * FROM SCANRESULTS").fetchall()
print(scanresults)

scanhistory = cur.execute("SELECT * FROM SCANHISTORY").fetchall()
print(scanhistory)

schedule = cur.execute("SELECT * FROM SCHEDULE").fetchall()
print(schedule)

sources = cur.execute("SELECT * FROM SOURCES").fetchall()
print(sources)

status = cur.execute("SELECT * FROM STATUS").fetchall()
print(status)
