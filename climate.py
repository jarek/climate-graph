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
import calendar

timer = []

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
NUM_MONTHS = len(MONTHS)

ROWS = ['record high', 'high', 'mean', 'low', 'record low', 'sun', 
	'precipitation days', 'precipitation mm',
	'rain days', 'rain mm', 'snow days', 'snow cm']
# TODO: add support for other data of interest

PRINTED_ROW_TITLES = {'record high': 'r-high', 'high': 'high', 'mean': 'mean',
	'low': 'low', 'record low': 'r-low', 'sun': 'sun',
	'precipitation days': 'prep days', 'precipitation mm': 'prep mm',
	'rain days': 'rain days', 'rain mm': 'rain mm',
	'snow days': 'snow days', 'snow cm': 'snow cm'}

ROWS_TO_PRINT = ['record high', 'high', 'low', 'record low', 'sun']
	
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

	def parse(string):
		string = string.strip().replace(u'−', '-')
		return float(string)

	def F_to_C(f):
		return round((f - 32)*(5.0/9.0), 1)

	def daily_to_monthly(daily, month):
		# convert text month to number
		month = MONTHS.index(month) + 1

		# use a non-leap year since I suspect monthly numbers are given
		# for non-leap Februarys
		days = calendar.monthrange(2013, month)[1]

		return daily * days


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
			category,value = (x.strip() for x in line.split('='))
			category = category[3:].strip() # take out the month

			if category in result:
				# straightforward putting the data in
				value = parse(value)
				result[category].append(value)
			elif category[-2:] == ' C' and category[:-2] in result:
				value = parse(value)
				result[category[:-2]].append(value)
			elif category[-2:] == ' F' and category[:-2] in result:
				value = F_to_C(parse(value))
				result[category[:-2]].append(value)
			elif category == 'd sun':
				value = daily_to_monthly(parse(value), month)
				result['sun'].append(value)

			# TODO: add in support for other data 
			# using mm, in, etc as needed
		
	return result

def print_data_as_text(provided_data):
	row_titles = dict((row,PRINTED_ROW_TITLES[row]) 
		for row in PRINTED_ROW_TITLES if row in ROWS_TO_PRINT)
	max_row_title = 0

	data = provided_data
	max_lengths = [0]*NUM_MONTHS

	for category in ROWS:
		if len(data[category]) == NUM_MONTHS and isinstance(data[category][0], float):
			for i in range(NUM_MONTHS):
				data[category][i] = str(data[category][i])
				max_lengths[i] = max(max_lengths[i], len(data[category][i]))

			if category in row_titles:
				max_row_title = max(max_row_title, len(row_titles[category]))

	def print_one_row(row, title):
		result = row_titles[title].rjust(max_row_title) + '|'
		result = result + '|'.join(row[i].rjust(max_lengths[i]) for i in range(NUM_MONTHS)) + '|'
		return result
	
	result = []
	for row_name in ROWS:
		if row_name in row_titles and row_name in data and len(data[row_name]) == NUM_MONTHS:
			result.append(print_one_row(data[row_name], row_name))

	if len(result) > 0:
		print data['place']
		print '\n'.join(result)
	else:
		print data['place'] + ': no information found'


if __name__ == '__main__':
	city = get_city()
	data = get_climate_data(city)
	print_data_as_text(data)

