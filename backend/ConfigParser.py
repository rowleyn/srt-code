"""
This class parses configuration files. These are .json files used to configure the telescope.
The telescope will always have an initial srtconfig.json file which has the default configuration for the telescope.
New config info can be added and current info can be changed and removed by sended config files to the server.

Author: Nathan Rowley
"""

import json

class ConfigParser:

	def __init__(self):
		