'''
This is the web app that handles requests for data and actions from the web page.
It uses Flask to handle these requests and send back updates.

Author: Nathan Rowley
Date: June 2018
'''

from flask import Flask, render_template, make_response, send_file, request, redirect, url_for, session
from astral import Astral
import json
import sqlite3
import zipfile
import io
import os
import re
import random
from datetime import date

app = Flask(__name__)

app.secret_key = os.urandom(16)

admin_username = 'admin'
admin_password = 'something'

normal_username = 'student'
normal_password = 'something'

max_users = 10
current_users = 0

# url for loggin in, all urls redirect to this one if a user is not logged in
@app.route('/login', methods=['GET','POST'])
def login():

	if request.method == 'GET':

		return render_template('login.html')

	else:

		if request.form['username'] == admin_username:

			if request.form['password'] == admin_password:

				if current_users <= max_users:

					session['username'] = admin_username

					current_users = current_users + 1

					return redirect(url_for('main_page'))

				else:

					return 'toomanyusers'

		if request.form['username'] == normal_username:

			if request.form['password'] == normal_password:

				if current_users <= max_users:

					session['username'] = normal_username

					current_users = current_users + 1

					return redirect(url_for('main_page'))

				else:

					return 'toomanyusers'

		return 'failure'

# url for logging out, 
@app.route('/logout')
def logout():

	session.pop('username', None)

	current_users = current_users - 1

	return 'logged out'

# default url
@app.route('/')
def main_page():

	return render_template('srt.html')

# url for the home page, activated when a user clicks on the home tab
@app.route('/home')
def home_page():

	return render_template('home.html')

# url for the config page, activated when a user clicks on the config tab
@app.route('/config')
def config_page():

	return render_template('config.html')

# url for the config page, activated when a user clicks on the scan tab
@app.route('/scan')
def scan_page():

	return render_template('scan.html')

# url for the status bar, activated periodically via automatic ajax calls on every page
@app.route('/status', methods=['POST'])
def get_status():

	srtdb = sqlite3.connect('srtdata.db')	# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	responsepython = {}

	configdata = cur.execute("SELECT * FROM CONFIG").fetchone()						# retrieve station config data and add it to the response
	responsepython = {'az': configdata['az'], 'al': configdata['al']}

	currentscan = cur.execute("SELECT * FROM SCANIDS WHERE STATUS = ?", ('running',)).fetchone()	# retrieve the id of the currently running scan, if it exists
	
	if currentscan == None:
		
		responsepython['status'] = 'noactive'
		
	else:
		
		scantimes = cur.execute("SELECT * FROM SCHEDULE WHERE ID = ?", (currentscan['id'],))
		
		responsepython['name'] = currentscan['name']
		responsepython['starttime'] = scantimes['starttime']
		responsepython['endtime'] = scantimes['endtime']

	srtdb.close()												# database connection no longer needed

	responsejson = json.JSONEncoder().encode(responsepython)	# convert response into json

	response = make_response(responsejson)						# convert response into a Flask Response object

	return response

# url for submitting a new scan, returns the schedule of scans
@app.route('/submitscan', methods=['POST'])
def submit_scan():

	newscan = request.get_json(force=True)	# get json-formatted scan parameters

	srtdb = sqlite3.connect('srtdata.db')	# establish a connection and a cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	valid = True							# check client data for validity before adding to the database

	valid = valid and len(newscan['name']) <= 30
	valid = valid and (newscan['type'] == 'track' or newscan['type'] == 'drift')
	valid = valid and len(newscan['source']) <= 30
	valid = valid and (re.fullmatch('0*(?:[0-9]|1\d|2[0-3])h0*(?:[0-9]|[1-5]\d)m0*(?:[0-9]|[1-5]\d)s|0*24h0+m0+s', newscan['ras']) != None)
	valid = valid and (re.fullmatch('-?0*(?:[0-9]|[1-8]\d)d0*(?:[0-9]|[1-5]\d)m0*(?:[0-9]|[1-5]\d)s|-?0*90d0+m0+s', newscan['dec']) != None)
	valid = valid and (re.fullmatch('0*[0-7]h0*(?:[0-9]|[1-5]\d)m0*(?:[0-9]|[1-5]\d)s|0*8h0+m0+s', newscan['duration']) != None)
	valid = valid and (re.fullmatch('[0-9]+\.?[0-9]*', newscan['freqlower']) != None) and int(newscan['freqlower']) >= 0 and int(newscan['freqlower']) <= 10000
	valid = valid and (re.fullmatch('[0-9]+\.?[0-9]*', str(newscan['frequpper'])) != None) and int(newscan['frequpper']) >= 0 and int(newscan['frequpper']) <= 10000
	valid = valid and newscan['freqlower'] <= newscan['frequpper']
	valid = valid and (re.fullmatch('1[0-9]*', newscan['stepnumber']) != None) and int(newscan['stepnumber']) >= 1 and int(newscan['stepnumber']) <= 1000000

	if valid:

		uniqueid = False

		while not uniqueid:

			scanid = random.randint(1,1000000000000)

			existingid = cur.execute("SELECT * FROM SCANIDS WHERE ID = ? LIMIT 1", (scanid,)).fetchone()

			if existingid == None:

				uniqueid = True

		if newscan['source'] != 'no source':

			if newscan['source'] == 'sun':

				newscan['ras'] = 'sunras'
				newscan['dec'] = 'sundec'

			else:

				sourcepos = cur.execute("SELECT * FROM SOURCES WHERE NAME = ?", (newscan['source'],)).fetchone()

				if sourcepos == None:

					today = date.today()

					cur.execute("INSERT INTO SCANIDS VALUES (?,?,?)", (scanid, newscan['name'], 'sourceerror'))
					cur.execute("INSERT INTO SCANHISTORY VALUES (?,?,?,?,?,?)", (scanid, newscan['name'], newscan['type'], today.day, today.month, today.year))
					srtdb.commit()

					srtdb.close()

					return scheduleGetter()

				newscan['ras'] = sourcepos['ras']
				newscan['dec'] = sourcepos['dec']

		config = cur.execute("SELECT * FROM CONFIG").fetchone()

		if newscan['freqlower'] < config['freqlower'] or newscan['frequpper'] > config['frequpper']:

			today = date.today()

			cur.execute("INSERT INTO SCANIDS VALUES (?,?,?)", (scanid, newscan['name'], 'freqboundserror'))
			cur.execute("INSERT INTO SCANHISTORY VALUES (?,?,?,?,?,?)", (scanid, newscan['name'], newscan['type'], today.day, today.month, today.year))
			srtdb.commit()

			srtdb.close()

			return scheduleGetter()

		# build a new row for the database containing scan parameters
		params = (scanid, newscan['name'], newscan['type'], newscan['source'], newscan['ras'], int(newscan['dec']), newscan['duration'], int(newscan['freqlower']), int(newscan['frequpper']), int(newscan['stepnumber']))

		cur.execute("INSERT INTO SCANIDS VALUES (?,?,?)", (scanid, newscan['name'], 'submitted'))
		cur.execute("INSERT INTO SCANPARAMS VALUES (?,?,?,?,?,?,?,?,?,?)", params)	# insert new scan into database and commit change
		srtdb.commit()

	srtdb.close()	# database connection no longer needed

	return scheduleGetter()

# url for updating the list of scheduled scans, activated periodically via automatic ajax calls by the scan page
@app.route('/schedule', methods=['GET','POST'])
def get_schedule():

	return scheduleGetter()

# url for cancelling a scan, returns the schedule of scans
@app.route('/deschedulescan', methods=['POST'])
def deschedule_scan():

	scanid = int(request.get_data()) 		# get id of scan to be removed

	srtdb = sqlite3.connect('srtdata.db')	# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	valid = True

	valid = valid and (re.fullmatch('1[0-9]*', str(scanid)) != None) and scanid >= 1 and scanid <= 1000000000000

	if valid:

		cur.execute("UPDATE SCANIDS WHERE ID = ? SET STATUS = ?", (scanid, 'cancelled'))	# set scan status to cancelled
		srtdb.commit()

	srtdb.close()	# database connection no longer needed

	return scheduleGetter()

# url for updating the list of sources in the scan page dialog form
@app.route('/sources', methods=['POST'])
def get_sources():

	return sourceGetter()

# url for uploading a new source or updating an existing source, returns the newly updated source list
@app.route('/uploadsource', methods=['POST'])
def add_source():

	newsource = request.get_json(force=True)	# get json-formatted source parameters

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	valid = True

	valid = valid and len(newsource['name']) <= 30
	valid = valid and (re.fullmatch('(?:[0-9]|1\d|2[0-4])h(?:[0-9]|[1-5]\d|60)m(?:[0-9]|[1-5]\d|60)s', newsource['ras']) != None)
	valid = valid and (re.fullmatch('-?[0-9]+\.?[0-9]*', newsource['dec']) != None)

	if valid:

		source = cur.execute("SELECT NAME FROM SOURCES WHERE NAME = ? LIMIT 1", (newsource['name'],)).fetchone()							# check database for preexisting source

		if source == None:

			cur.execute("INSERT INTO SOURCES VALUES (?,?,?)", (newsource['name'], newsource['ras'], newsource['dec']))						# insert new source if preexisting is not found

		else:

			cur.execute("UPDATE SOURCES SET RAS = ?, DEC = ? WHERE NAME = ?", (newsource['ras'], newsource['dec'], newsource['name']))		# otherwise update existing source

		srtdb.commit()

	srtdb.close()				# database connection no longer needed

	return sourceGetter()

# url for removing a source from the database, returns the newly updated source list
@app.route('/removesource', methods=['POST'])
def remove_source():

	sourcename = request.get_data().decode('ascii') 	# get name of source to be removed

	srtdb = sqlite3.connect('srtdata.db')				# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	valid = True

	valid = valid and len(sourcename) <= 30

	if valid:

		cur.execute("DELETE FROM SOURCES WHERE NAME = ?", (sourcename,))	# remove source with matching name and commit change
		srtdb.commit()

	srtdb.close()				# database connection no longer needed

	return sourceGetter()

# url for updating the configuration parameters, returns the newly updated parameters
@app.route('/updateconfig', methods=['POST'])
def update_config():

	newconfig = request.get_json(force=True)	# get json-formatted source parameters

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	valid = True

	# return subsets of config params based on keyword
	if newconfig[0] == 'nameloc':

		valid = valid and len(newconfig[1]) <= 100						# check client data for validity
		valid = valid and newconfig[2] >= -90 and newconfig[2] <= 90
		valid = valid and newconfig[3] >= -180 and newconfig[3] <= 180
		valid = valid and newconfig[4] >= 0 and newconfig[4] <= 10000

		if valid:

			cur.execute("UPDATE CONFIG SET NAME = ?, LAT = ?, LON = ?, HEIGHT = ?", (newconfig[1], newconfig[2], newconfig[3], newconfig[4]))

	elif newconfig[0] == 'movelimits':

		valid = valid and newconfig[1] >= 0 and newconfig[1] <= 360			# check client data for validity
		valid = valid and newconfig[2] >= 0 and newconfig[1] <= 360
		valid = valid and newconfig[1] <= newconfig[2]
		valid = valid and newconfig[3] >= 0 and newconfig[3] <= 180
		valid = valid and newconfig[4] >= 0 and newconfig[4] <= 180
		valid = valid and newconfig[3] <= newconfig[4]

		if valid:

			cur.execute("UPDATE CONFIG SET AZLOWER = ?, AZUPPER = ?, ALLOWER = ?, ALUPPER = ?", (newconfig[1], newconfig[2], newconfig[3], newconfig[4]))

	else:

		valid = valid and newconfig[1] <= 0 and newconfig[1] >= 10000		# check client data for validity
		valid = valid and newconfig[2] <= 0 and newconfig[2] >= 10000
		valid = valid and newconfig[1] <= newconfig[2]

		if valid:

			cur.execute("UPDATE CONFIG SET FREQLOWER = ?, FREQUPPER = ?", (newconfig[1], newconfig[2]))

	srtdb.commit()

	srtdb.close()								# database connection no longer needed

	return configGetter(newconfig[0])

# url for getting config data to populate tables on the config page
@app.route('/getconfig', methods=['POST'])
def get_config():

	return configGetter(request.get_data().decode('ascii'))

# url for downloading a set of scans as a zip file
@app.route('/downloadscans', methods=['POST'])
def download_scans():

	idlist = request.get_json(force=True)		# get json-formatted list of scan names

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	b = io.BytesIO()
	f = zipfile.ZipFile(b,'w')					# open a new zip archive in memory

	filenames = {}

	for scanid in idlist:						# write each scan as a .fits file to the archive

		scanresult = cur.execute("SELECT * FROM SCANRESULTS WHERE ID = ?", (scanid,)).fetchone()
		scanname = cur.execute("SELECT * FROM SCANIDS WHERE ID = ?", (scanid,)).fetchone()
		scandate = cur.execute("SELECT * FROM SCANDATES WHERE ID = ?", (scanid,)).fetchone()

		filename = scanname['name'] + '_' + str(scandate['month']) + '_' + str(scandate['day']) + '_' + str(scandate['year'])

		if filename not in filenames:

			filenames[filename] = 1

		else:

			filenames[filename] += 1

		filename += '_' + str(filenames[filename]) + '.fits'

		f.writestr(filename, scanresult['data'])

	f.close()									# close the zip archive to avoid problems

	srtdb.close()								# database connection no longer needed

	response = make_response(b.getvalue())		# package zip archive in a Flask Response object

	return response

# url for searching completed scans by name and date range
@app.route('/searchscans', methods=['POST'])
def search_scans():

	searchparams = request.get_json(force=True)		# get json-formatted list of search params

	srtdb = sqlite3.connect('srtdata.db')			# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	valid = True

	valid = valid and len(searchparams['name']) <= 30
	valid = valid and (re.fullmatch('(?:any)|\d\d\d\d', searchparams['year']) != None)
	valid = valid and (re.fullmatch('(?:any)|[1-9]|1[0-2]', searchparams['month']) != None)

	if valid:

		if searchparams['name'] == '':					# search in the specified date range, either with or without name param

			if searchparams['month'] == 'any':

				if searchparams['year'] == 'any':

					scandates = cur.execute("SELECT * FROM SCANHISTORY").fetchall()

				else:

					scandates = cur.execute("SELECT * FROM SCANHISTORY WHERE YEAR = ?", (searchparams['year'],)).fetchall()

			else:

				scandates = cur.execute("SELECT * FROM SCANHISTORY WHERE MONTH = ?, YEAR = ?", (searchparams['month'], searchparams['year'])).fetchall()

		else:

			if searchparams['month'] == 'any':

				if searchparams['year'] == 'any':

					scandates = cur.execute("SELECT * FROM SCANHISTORY WHERE NAME = ?", (searchparams['name'],)).fetchall()

				else:

					scandates = cur.execute("SELECT * FROM SCANHISTORY WHERE NAME = ?, YEAR = ?", (searchparams['name'], searchparams['year'])).fetchall()

			else:

				scandates = cur.execute("SELECT * FROM SCANHISTORY WHERE NAME = ?, MONTH = ?, YEAR = ?", (searchparams['name'], searchparams['month'], searchparams['year'])).fetchall()

	srtdb.close()								# database connection no longer needed

	scanlist = []

	for scan in scandates:							# build list of search results

		scanlist.append({'id': scan['id'], 'name': scan['name'], "date": str(scan['month']) + '/' + str(scan['day']) + '/' + str(scan['year'])})

	responsejson = json.JSONEncoder().encode(scanlist)		# convert result list into json

	response = make_response(responsejson)					# convert json to Flask Response object

	return response


@app.route('/deletescans', methods=['POST'])
def delete_scan():

	scanids = request.get_json()				# get json-formatted list of scan names

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	for scanid in scanids:						# delete scans from the database

		cur.execute("DELETE FROM SCANRESULTS WHERE ID = ?", (scanid,))
		cur.execute("DELETE FROM SCANHISTORY WHERE ID = ?", (scanid,))
		cur.execute("DELETE FROM SCANPARAMS WHERE ID = ?", (scanid,))
		cur.execute("DELETE FROM SCANIDS WHERE ID = ?", (scanid,))

	srtdb.commit()

	srtdb.close()								# database connection no longer needed

	return make_response("completed")


@app.route('/scanstatus', methods=['GET','POST'])
def get_scanstatus():

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	if request.method == 'POST':

		newstatus = request.get_json()

		valid = True

		valid = valid and (re.fullmatch('1[0-9]*', str(newstatus['id'])) != None) and newstatus['id'] >= 1 and newstatus['id'] <= 1000000000000

		if valid:

			currentstatus = cur.execute("SELECT * FROM STATUS LIMIT 1").fetchone()

			if currentstatus['id'] == newstatus['id'] and currentstatus['code'] != 'ok':

				cur.execute("UPDATE STATUS SET CODE = ?", ('ok',))
				srtdb.commit()

	currentstatus = cur.execute("SELECT * FROM STATUS").fetchone()

	responsepython = {'id': currentstatus['id'], 'code': currentstatus['code']}

	responsejson = json.JSONEncoder().encode(responsepython)

	response = make_response(responsejson)

	return response


@app.route('/gethistory', methods=['POST'])
def get_history():

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	history = cur.execute("SELECT * FROM SCANHISTORY").fetchall();

	today = date.today()

	historylist = []

	for scan in history:

		status = cur.execute("SELECT * FROM SCANIDS WHERE ID = ?", (scan['id'],))

		if not (scan['year'] < today.year or scan['month'] < today.month or today.day - scan['day'] > 3):

			historylist.append({'name': scan['name'], 'type': scan['type'], 'date': str(scan['month']) + '/' + str(scan['day']) + '/' + str(scan['year']), 'status': status['status']})

		else:

			hasdata = cur.execute("SELECT ID FROM SCANRESULTS WHERE ID = ?", (scan['id'],)).fetchone()

			if hasdata == None:

				cur.execute("DELETE FROM SCANHISTORY WHERE ID = ?", (scan['id'],))
				cur.execute("DELETE FROM SCANPARAMS WHERE ID = ?", (scan['id'],))
				cur.execut("DELETE FROM SCANIDS WHERE ID = ?", (scan['id'],))
				srtdb.commit()

	srtdb.close()

	responsejson = json.JSONEncoder().encode(historylist)

	response = make_response(responsejson)

	return response





'''
Function that gets the scan schedule and current scan from the database and returns it as a Flask Response object containing json.

:return response: Flask Response object with json-encoded scan queue
'''
def scheduleGetter():

	srtdb = sqlite3.connect('srtdata.db')	# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	schedule = cur.execute("SELECT * FROM SCHEDULE ORDER BY STARTTIME ASC").fetchall()	# get scheduled scans in ascending order by starttime

	firstchecked = False

	scanlist = []

	for block in schedule:

		scan = cur.execute("SELECT * FROM SCANPARAMS WHERE ID = ?", (block['id'],))		# get scan params from the db

		if not firstchecked:

			firstscan = cur.execute("SELECT * FROM SCANID WHERE ID = ?", (block['id'],)).fetchone()		# first scan in the schedule must be checked for running status

			if firstscan['status'] == 'running':	# if it is running mark 'current' field as True

				scan['current'] = True

			else:

				scan['current'] = False

			firstchecked = True

		else:						# all other scans are necessarily not the current scan and are marked False

			scan['current'] = False

		scan['starttime'] = block['starttime']		# add start and end times to the scan params
		scan['endtime'] = block['endtime']

		scanlist.append(scan)						# add scan to response

	responsejson = json.JSONEncoder().encode(scanlist)	# convert response to json

	response = make_response(responsejson)				# convert response to Flask Response object

	return response

'''
Function that gets source data from the databse and returns it as a Flask Response object containing json.

:return response: Flask Response object with json-encoded source data
'''
def sourceGetter():

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	sources = cur.execute("SELECT * FROM SOURCES").fetchall()		# retrieve all sources from the database

	srtdb.close()								# database connection no longer needed

	sourcelist = []

	for source in sources:						# add each source name to the response

		sourcelist.append({'name': source['name'], 'ras': source['ras'], 'dec': source['dec']})

	responsejson = json.JSONEncoder().encode(sourcelist)	# convert response to json

	response = make_response(responsejson)					# convert response to Flask Response object

	return response

'''
Function that gets configuration parameters from the database and returns them as a Flask Response object containing json.

:param section: keyword indicating which subset of parameters to send
:return response: Flask Response object with json-encoded config params
'''
def configGetter( section ):

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	config = cur.execute("SELECT * FROM CONFIG").fetchone()

	srtdb.close()

	if section == 'nameloc':

		configlist = [config['name'], config['lat'], config['lon'], config['height']]

	elif section == 'movelimits':

		configlist = [config['azlower'], config['azupper'], config['allower'], config['alupper']]

	elif section == 'freqlimits':

		configlist = [config['freqlower'], config['frequpper']]

	else:

		configlist = []

	responsejson = json.JSONEncoder().encode(configlist)	# convert response to json

	response = make_response(responsejson)					# convert response to Flask Response object

	return response
