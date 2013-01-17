#!/usr/bin/env python
# coding=utf-8

import cgi
import os
import sys
import urllib
import pycurl
import StringIO
import simplejson as json
import time

timer = []

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
NUM_MONTHS = len(MONTHS)

ROWS = ['record high', 'high', 'mean', 'low', 'record low']
# TODO: add support for precipitation in/mm/days, sunshine hours, etc

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

def get_page_source(page):
	url = API_URL % urllib.quote_plus(page)
	text = get_URL(url)
	data = json.loads(text)

	# TODO: gracefully handle errors here
	page = data['query']['pages'].itervalues().next()

	page_title = page['title']
	page_text = page['revisions'][0]['*']
	
	return page_title,page_text

def get_city():
	city = 'Melbourne'

	# look for http param first
	# if http param not present, look for command line param
	
	param = None
	arguments = cgi.FieldStorage()

	if 'city' in arguments:
		city = str(arguments['city'].value).capitalize()
	elif len(sys.argv) > 1:
		city = sys.argv[1].capitalize()

	return city

def parse(string):
	string = string.strip().replace(u'−', '-')
	return float(string)

def FtoC(f):
	return round((f - 32)*(5.0/9.0), 1)

def get_climate_data(place):
	result = {}
	for row_name in ROWS:
		result[row_name] = []

	def find_weatherbox_template(data):
		index1 = data.find('{{Weather box')
		# TODO: this actually catches end of any first template. could be cite template 
		# or something else. add code to count {{ and }} to find the right one
		index2 = data.find('}}', index1)

		if index1 > -1 and index2 > -1:
			return data[index1:index2]
		else:
			return ''

	result['place'],data = get_page_source(place)

	weatherbox = find_weatherbox_template(data).strip()

	if len(weatherbox) == 0:
		index2 = data.find('weatherbox}}')
		index1 = data.rfind('{{', 0, index2)

		if index1 > -1 and index2 > -1:
			# there's a weather box template we can look at
			template_name = 'Template:' + data[index1+2:index2+10]

			weatherbox_title,data = get_page_source(template_name)
			weatherbox = find_weatherbox_template(data)

	weatherbox_items = weatherbox.split('|')

	for line in weatherbox_items:
		line = line.strip()
		month = line[:3]
		if month in MONTHS:
			celsius = line.find(' C', 4)
			fahrenheit = line.find(' F', 4)
			
			# TODO: this parsing will need to be expanded to support
			# mm, in, days/hours/percent, etc, as needed for ROWS
			if celsius > -1:
				category = line[4:celsius]
				if category in result:
					value = parse(line[line.find('=')+1:]) 
					result[category].append(value)
			elif fahrenheit > -1:
				category = line[4:fahrenheit]
				if category in result:
					value = parse(line[line.find('=')+1:])
					value = FtoC(value)
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

	def print_one_row(row):
		return '|' + '|'.join(row[i].rjust(max_lengths[i]) for i in range(NUM_MONTHS)) + '|'
	
	result = []
	for row_name in ROWS:
		if row_name in data and len(data[row_name]) == NUM_MONTHS:
			result.append(print_one_row(data[row_name]))

	if len(result) > 0:
		print data['place']
		print '\n'.join(result)
	else:
		print data['place'] + ': no information found'


if __name__ == '__main__':
	city = get_city()
	data = get_climate_data(city)
	print_data_as_text(data)

