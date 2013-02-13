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

def get_page_source(page_name):
	url = API_URL % urllib.quote_plus(page_name)
	text = get_URL(url)
	data = json.loads(text)

	try:
		page = data['query']['pages'].itervalues().next()
		page_title = page['title']
	except:
		return 'unknown error occurred',False

	try:
		# this line will error for a non-existent page
		page_text = page['revisions'][0]['*']
	
		return page_title,page_text
	except:
		return str(page_name) + ': location not found',False

def get_cities():
	cities = []

	# look for http param first
	# if http param not present, look for command line param
	
	param = None
	arguments = cgi.FieldStorage()

	if 'city' in arguments:
		cities = [str(arguments['city'].value)]
	elif 'cities' in arguments:
		cities = str(arguments['cities'].value).split(';')
	elif len(sys.argv) > 1:
		cities = sys.argv[1:]

	return cities

def get_climate_data(place):
	def find_weatherbox_template(data):
		if data is False:
			return ''

		index1 = data.find('{{Weather box')

		if index1 > -1:
			# there's a weather box - find its extent

			index2 = index1
			loop_end = False

			while not loop_end:
				# count template open and close tags to grab
				# full extent of weatherbox template.
				# avoids incomplete data due to cite or convert
				# templates.
				index2 = data.find('}}', index2)+2
				open_count = data[index1:index2].count('{{') 
				clos_count = data[index1:index2].count('}}')

				loop_end = open_count == clos_count # do..while

			# TODO: malformed pages with no closing template could
			# send me into endless loop. add another variable to 
			# make sure i'm advancing index2 with each iteration,
			# if it's not changing break

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


	result = {'page_error': False}
	for row_name in ROWS:
		result[row_name] = []

	result['title'],data = get_page_source(place)

	weatherbox = find_weatherbox_template(data).strip()

	if data is False:
		# indicates a problem getting data - signal it so output
		# can be formatted accordingly
		result['page_error'] = True
		return result

	if len(weatherbox) == 0:
		# weatherbox not found directly on page
		# see there's a dedicated city weather template we can look at
		index2 = data.find('weatherbox}}')

		if index2 > -1:
			index1 = data.rfind('{{', 0, index2)
			template_name = 'Template:' + data[index1+2:index2+10]

			# there is separate template - get it and process it
			weatherbox_title,data = get_page_source(template_name)
			if data is False:
				result['page_error'] = True
				result['title'] = weatherbox_title
				return result
			else:
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

def format_data_as_text(provided_data):
	if provided_data['page_error'] is True:
		# on page error, only print error message
		return provided_data['title']

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
		output = data['title'] + '\n'
		output = output + '\n'.join(result)
	else:
		output = data['title'] + ': no information found'

	return output


if __name__ == '__main__':
	cities = get_cities()
	
	for city in cities:
		data = get_climate_data(city)
		print format_data_as_text(data)

