'''
This is the web app that handles requests for data and actions from the web page.
It uses Flask to handle these requests and send back updates.

Author: Nathan Rowley
Date: June 2018
'''

from flask import Flask, render_template, make_response, send_file, request, redirect, url_for
import json
import sqlite3
import Scan

app = Flask(__name__)

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
	responsepython['config'] = {'az': configdata['az'], 'al': configdata['al']}

	scandata = cur.execute("SELECT * FROM QUEUE LIMIT 1").fetchone()				# retrieve first scan in scan queue and add it to the response

	responsepython['scanqueue'] = {'id':scandata['id'], 'name':scandata['name'], 'type': scandata['type'], 'source': scandata['source'], 'lat': scandata['gallat'], 'lon': scandata['gallon'], 'center': scandata['center']}

	srtdb.close()												# database connection no longer needed

	responsejson = json.JSONEncoder().encode(responsepython)	# convert response into json

	response = make_response(responsejson)						# convert response into a Flask Response object

	return response

# url for uploading a new scan, returns the newly updated list of scans
@app.route('/uploadscan', methods=['POST'])
def queue_scan():

	newscan = request.get_json(force=True)	# get json-formatted scan parameters

	srtdb = sqlite3.connect('srtdata.db')	# establish a connection and a cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	# build a new row for the database containing scan parameters
	r = (newscan['id'], newscan['name'], newscan['type'], newscan['source'], newscan['lat'], newscan['lon'], newscan['duration'], newscan['center'], newscan['stepnumber'], newscan['stepsize'])

	cur.execute("INSERT INTO QUEUE VALUES (?,?,?,?,?,?,?,?,?,?)", r)	# insert new scan into database and commit change
	srtdb.commit()

	srtdb.close()	# database connection no longer needed

	return queueGetter()

# url for updating the list of queued scans, activated periodically via automatic ajax calls by the scan page
@app.route('/queue', methods=['GET','POST'])
def get_queue():

	return queueGetter()

# url for removing a scan, returns the newly updated list of scans
@app.route('/removescan', methods=['POST'])
def remove_scan():

	scanid = request.get_data() 			# get id of scan to be removed

	srtdb = sqlite3.connect('srtdata.db')	# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	cur.execute("DELETE FROM QUEUE WHERE ID = ?", (int(scanid),))	# remove scan with matching id and commit change
	srtdb.commit()

	srtdb.close()	# database connection no longer needed

	return queueGetter()

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

	source = cur.execute("SELECT NAME FROM SOURCES WHERE NAME = ? LIMIT 1", (newsource['name'],)).fetchone()										# check database for preexisting source

	if source == None:

		cur.execute("INSERT INTO SOURCES VALUES (?,?,?)", (newsource['name'], newsource['gallat'], newsource['gallon']))							# insert new source if preexisting is not found

	else:

		cur.execute("UPDATE SOURCES SET GALLAT = ?, GALLON = ? WHERE NAME = ?", (newsource['gallat'], newsource['gallon'], newsource['name']))		# otherwise update existing source

	srtdb.commit()

	srtdb.close()				# database connection no longer needed

	return sourceGetter()

# url for removing a source from the database, returns the newly updated source list
@app.route('/removesource', methods=['POST'])
def remove_source():

	sourcename = request.get_data() 			# get name of source to be removed

	srtdb = sqlite3.connect('srtdata.db')		# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	cur.execute("DELETE FROM SOURCES WHERE NAME = ?", (sourcename.decode('ascii'),))	# remove source with matching name and commit change
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

	# return subsets of config params based on keyword
	if newconfig[0] == "nameloc":

		cur.execute("UPDATE CONFIG SET NAME = ?, LAT = ?, LON = ?, HEIGHT = ?", (newconfig[1], newconfig[2], newconfig[3], newconfig[4]))

	elif newconfig[0] == "movelimits":

		cur.execute("UPDATE CONFIG SET AZLOWER = ?, AZUPPER = ?, ALLOWER = ?, ALUPPER = ?", (newconfig[1], newconfig[2], newconfig[3], newconfig[4]))

	else:

		cur.execute("UPDATE CONFIG SET FREQLOWER = ?, FREQUPPER = ?", (newconfig[1], newconfig[2]))

	srtdb.commit()

	srtdb.close()								# database connection no longer needed

	return configGetter(newconfig[0])

@app.route('/getconfig', methods=['POST'])
def get_config():

	return configGetter(request.get_data().decode('ascii'))





'''
Function that gets the scan queue from the database and returns it as a Flask Response object containing json.

:return response: Flask Response object with json-encoded scan queue
'''
def queueGetter():

	srtdb = sqlite3.connect('srtdata.db')	# establish a connection and cursor into the database
	srtdb.row_factory = sqlite3.Row
	cur = srtdb.cursor()

	scans = cur.execute("SELECT * FROM QUEUE").fetchall()	# retrieve the entire scan queue

	srtdb.close()					# database connection no longer needed

	newqueue = []

	for scan in scans:				# add each row from the database into the response

		newqueue.append({'id': scan['id'], 'name': scan['name'], 'type': scan['type'], 'source': scan['source'], 'lat': scan['gallat'], 'lon': scan['gallon'], 'duration': scan['duration'], 'center': scan['center']})

	responsejson = json.JSONEncoder().encode(newqueue)	# convert response to json

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

		sourcelist.append({'name': source['name'], 'gallat': source['gallat'], 'gallon': source['gallon']})

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

	if section == "nameloc":

		configlist = [config['name'], config['lat'], config['lon'], config['height']]

	elif section == "movelimits":

		configlist = [config['azlower'], config['azupper'], config['allower'], config['alupper']]

	else:

		configlist = [config['freqlower'], config['frequpper']]

	responsejson = json.JSONEncoder().encode(configlist)	# convert response to json

	response = make_response(responsejson)					# convert response to Flask Response object

	return response