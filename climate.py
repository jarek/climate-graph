#!/usr/bin/env python
# coding=utf-8

import cgi
import os
import sys
import pycurl
import StringIO
import simplejson as json
import time

timer = []

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
NUM_MONTHS = len(MONTHS)

ROWS = ['record high', 'high', 'mean', 'low', 'record low']

API_URL = 'http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=%s&redirects=true&rvprop=content&format=json'

def get_URL(url):
	htime1 = time.time()

	c = pycurl.Curl()
	c.setopt(pycurl.URL, url)

	b = StringIO.StringIO()
	c.setopt(pycurl.WRITEFUNCTION, b.write)
	c.perform()

	htime2 = time.time()
	timer.append(['http get, ms', (htime2-htime1)*1000.0])

	html = b.getvalue()
	b.close()
	
	return html

def get_city():
	city = 'Melbourne'

	# look for http param first
	# if http param not present, look for command line param
	
	param = None
	arguments = cgi.FieldStorage()

	if 'city' in arguments:
		city = str(arguments['city'].value).lower()
	elif len(sys.argv) > 1:
		city = sys.argv[1].lower()

	return city

def parse(string):
	string = string.replace(u'−', '-')
	return float(string)

def FtoC(f):
	return round((f - 32)*(5.0/9.0), 2)

def get_climate_data(place):
	result = {}
	for row_name in ROWS:
		result[row_name] = []

	text = get_URL(API_URL % place)
	data = json.loads(text)

	# TODO: gracefully handle errors here
	result['place'] = data['query']['pages'].itervalues().next()['title']

	data = data['query']['pages'].itervalues().next()['revisions'][0]['*']
	# TODO: some pages have a separate custom template like {{Toronto weatherbox}}
	index1 = data.find('{{Weather box')
	# TODO: this actually catches end of any first template. could be cite template 
	# or something else. add code to count {{ and }} to find the right one
	index2 = data.find('}}', index1)
	
	infobox_items = data[index1:index2].split('|')

	for line in infobox_items:
		month = line[:3]
		if month in MONTHS:
			category = line[4:line.find(' C')] # TODO: expand to F, mm
			if category in result:
				value = parse(line[line.find('=')+1:]) 
				# note: this will break when there's not exactly one space between = and value
				# need to make this more robust ;)
				result[category].append(value)

	return result

def print_data_as_text(provided_data):
	data = provided_data
	max_lengths = [0]*NUM_MONTHS

	for category in ROWS:
		if len(data[category]) == NUM_MONTHS and isinstance(data[category][0], float):
			for i in range(NUM_MONTHS):
				data[category][i] = str(data[category][i])
				max_lengths[i] = max(max_lengths[i], len(data[category][i]))

	print data['place']

	def print_one_row(row):
		print '|' + '|'.join(row[i].rjust(max_lengths[i]) for i in range(NUM_MONTHS)) + '|'
	
	for row_name in ROWS:
		if row_name in data and len(data[row_name]) == NUM_MONTHS:
			print_one_row(data[row_name])


if __name__ == '__main__':
	city = get_city()
	data = get_climate_data(city)
	print_data_as_text(data)

