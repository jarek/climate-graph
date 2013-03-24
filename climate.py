#!/usr/bin/env python
# coding=utf-8

from __future__ import unicode_literals
import cgi
import sys
import urllib
import simplejson as json
import time
import calendar

import cache

timer = []

# hardcode rather than using calendar.month_abbr to avoid 
# potential locale problems - wikipedia always uses the English abbrs
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
NUM_MONTHS = len(MONTHS)

ROWS = ['record high C', 'high C', 'mean C', 'low C', 'record low C', 'sun', 
    'precipitation days', 'precipitation mm',
    'rain days', 'rain mm', 'snow days', 'snow cm']
# TODO: add support for other data of interest

PRINTED_ROW_TITLES = {'record high C': 'r-high', 'high C': 'high',
    'mean C': 'mean', 'low C': 'low', 'record low C': 'r-low', 'sun': 'sun',
    'precipitation days': 'prep days', 'precipitation mm': 'prep mm',
    'rain days': 'rain days', 'rain mm': 'rain mm',
    'snow days': 'snow days', 'snow cm': 'snow cm'}

ROWS_TO_PRINT = ['record high C', 'high C', 'low C', 'record low C', 'sun']
# , 'snow days', 'snow cm', 'precipitation days', 'precipitation mm', 'rain days', 'rain mm']

MSG_LOCATION_NOT_FOUND  = ': location not found'
MSG_NO_INFO_FOUND       = ': no information found'

UNIT_CONVERSIONS = {
    'F': {
        'C': (lambda f: round((f - 32)*(5.0/9.0), 1))
    },
    'inch': {
        'mm': (lambda x: round(x*25.4, 1)),
        'cm': (lambda x: round(x*2.54, 1))
    },
    'mm': { 'cm': (lambda x: x*10) },
    'cm': { 'mm': (lambda x: x/10.0) }
    }

ABSOLUTE_ROWS = ['sun', 'snow days', 'snow cm', 'rain days', 'rain mm',
    'precipitation days', 'precipitation mm']

API_URL = 'http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=%s&redirects=true&rvprop=content&format=json'

def get_page_source(page_name):
    url = API_URL % urllib.quote_plus(page_name.encode('utf-8'))
    text = cache.get_URL(url, page_name)
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
        return unicode(page_name) + MSG_LOCATION_NOT_FOUND,False

def get_cities():
    cities = []

    # cgi arguments commented out because i have no way of testing them 
    # right now - don't want anything potentially shaky in live code
    """arguments = cgi.FieldStorage()

    if 'city' in arguments:
        cities = [unicode(arguments['city'].value)]
    elif 'cities' in arguments:
        cities = unicode(arguments['cities'].value).split(';')
    el"""
    if len(sys.argv) > 1:
        cities = sys.argv[1:]
        
    cities = [arg.decode('utf-8') for arg in cities]

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
                prev_index2 = index2

                index2 = data.find('}}', index2)+2
                open_count = data[index1:index2].count('{{') 
                clos_count = data[index1:index2].count('}}')

                # to end loop, check for two things:
                # - open count = close count: we found the 
                # complete template, can stop looking
                # - previous index is same as current index:
                # loop is not advancing, might be a malformed
                # page, avoid endless loop by breaking

                loop_end = (open_count == clos_count) and \
                    (index2 != prev_index2) # do..while

            return data[index1:index2]
        else:
            return ''

    def find_separate_weatherbox_template(data):
        if data is False:
            return ''

        # {{cityname weatherbox}} seems to be the usual template name.
        # I'll just look for any template ending with weatherbox.
        # I've not seen a page this breaks on yet.

        # New York City includes its weatherbox through a reference 
        # to {{New York City weatherbox/cached}}, where the /cached 
        # template contains rendered HTML tables. I want to look at 
        # "Template:New York City weatherbox" instead. Not sure how 
        # common this is, but NYC is pretty major and handling it
        # is easy, so might as well.
        index2 = max(data.find('weatherbox}}'),
            data.find('weatherbox/cached}}'))

        if index2 > -1:
            # there is separate template - get it and process it
            index1 = data.rfind('{{', 0, index2)
            template_name = 'Template:' + data[index1+2:index2+10]

            weatherbox_title,data = get_page_source(template_name)
            if data is not False:
                return find_weatherbox_template(data)

        # if we didn't find template, or we couldn't get it, fall back
        return ''

    def parse(string):
        string = string.strip().replace(u'−', '-')
        return float(string)

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
        weatherbox = find_separate_weatherbox_template(data).strip()

    weatherbox_items = weatherbox.split('|')

    for i in range(len(weatherbox_items)):
        line = weatherbox_items[i].strip()
        line = line.strip()

        # try to parse out location data - usually specifies a neighbourhood,
        # weather station, year range info, etc
        if line.startswith('location'):
            points = line.split('=', 1)
            if len(points) == 2:
                location = points[1].strip()

                # complete the location field in case it contains an aliased
                # wikilink, e.g. [[Vancouver International Airport|YVR]].
                # otherwise text after the | would end up in the next 'line'
                # and not be included in location

                # this is a bit messy and would be better served by a more 
                # comprehensive wikisource parser to find opening and closing
                # braces, | that aren't template dividers, etc

                j = i
                while location.count('[[') > location.count(']]'):
                    location += '|' + weatherbox_items[j+1].strip()
                    j += 1

                if '[[' in location and '|' in location and ']]' in location:
                    location = location[0:location.find('[[')+2] \
                        + location[location.find('|')+1:]

                # finally, trim off wikilink markers, the most common 
                # wiki syntax in this field
                result['location'] = location.replace('[', '').replace(']', '')

        month = line[:3]
        if month in MONTHS:
            category,value = (x.strip() for x in line.split('='))
            category = category[3:].strip() # take out the month
            value = parse(value) # parse as number

            # last token of category name is sometimes the unit
            # (C, F, mm, inch, etc)
            unit = category.rsplit(None, 1)[-1]

            if category in result:
                # straightforward putting the data in
                result[category].append(value)

            elif unit in UNIT_CONVERSIONS:
                # try to convert units to known ones
                for target_unit in UNIT_CONVERSIONS[unit]:
                    # try to find a category we collect that 
                    # we know how to convert into
                    converted_category = category.replace(unit, target_unit)
                    if converted_category in result:
                        converted = UNIT_CONVERSIONS[unit][target_unit](value)
                        result[converted_category].append(converted)
                        break

            elif category == 'd sun':
                # special handling for daily sun hours
                value = daily_to_monthly(value, month)
                result['sun'].append(value)

    return result

def get_comparison_data(places, months, categories):
    """ Return data for a number of places, categories, and months.
     Takes a list of place names, list of 12 boolean values where True
    means the month is requested, and a dictionary of categoryname=boolean
    pairs (True means the category is requested) and returns the data as 
    long as it exists. Return data format is
    dict(month: dict(city: dict(category: data))) """

    data = {}
    for place in places:
        place_data = get_climate_data(place)

        if place_data['page_error'] is False:
            data[place_data['title']] = place_data

    result = {}
    for month,month_include in enumerate(months):
        if month_include:
            month_data = {}

            for place in data:
                place_data = {}

                for category,category_include in categories.items():
                    if category_include:
                        try:
                            # data might not contain info for the requested
                            # combination of place, category, and month. 
                            # if it doesn't, just pass by silently.
                            category_data = data[place][category][month]
                            place_data[category] = category_data
                        except:
                            # fail silently
                            pass

                month_data[place] = place_data

            result[month] = month_data

    return result

def has_printable_data(data):
    # This reflects the logic used in format_data_as_text(),
    # boiling it down to the minimum necessary to find out
    # if something will be printed. If format_data_as_text() 
    # is changed, this might need to be updated as well.

    has_data = False

    for row_name in PRINTED_ROW_TITLES:
        if row_name in data and len(data[row_name]) == NUM_MONTHS:
            has_data = True

    return has_data

def format_data_as_text(provided_data, print_all = False):
    if provided_data['page_error'] is True:
        # on page error, only print error message
        return provided_data['title']

    row_titles = dict((row,PRINTED_ROW_TITLES[row]) 
        for row in PRINTED_ROW_TITLES if row in ROWS_TO_PRINT or print_all)
    max_row_title = 0

    data = provided_data
    max_lengths = [0]*NUM_MONTHS

    for category in ROWS:
        if len(data[category]) == NUM_MONTHS \
            and isinstance(data[category][0], float):
            for i in range(NUM_MONTHS):
                data[category][i] = str(data[category][i])
                max_lengths[i] = max(max_lengths[i], len(data[category][i]))

            if category in row_titles:
                max_row_title = max(max_row_title, len(row_titles[category]))

    def format_one_row(row, title):
        # for categories holding absolute data like prep days, snow cm, etc
        # (rather than relative data like temperature or pressure),
        # print '0.0' as '-' or empty
        if title in ABSOLUTE_ROWS:
            row = [value if value != '0.0' else '-' for value in row]

        # pad row so all entries are right width for display
        row = [row[i].rjust(max_lengths[i]) for i in range(NUM_MONTHS)]

        result = row_titles[title].rjust(max_row_title) + '|'
        result = result + '|'.join(row) + '|'
        return result
    
    result = []
    for row_name in ROWS:
        if row_name in row_titles and row_name in data \
            and len(data[row_name]) == NUM_MONTHS:
            result.append(format_one_row(data[row_name], row_name))

    # add month indicators to top line
    # to make finding e.g. September easy
    month_names = format_one_row([month[0] for month in MONTHS], 'low C')
    
    title_length = len(data['title'])
    title_min_padding = 8

    title_padding = max(24, title_length + title_min_padding)

    if month_names[title_padding] == '|':
        # avoid having just a lone |
        title_padding += 1

    space_length = title_padding - title_length

    month_names = month_names[title_padding:]
    month_names = (' ' * space_length) + month_names

    if len(result) > 0:
        output = data['title'] + month_names + '\n'
        output = output + '\n'.join(result)

        if print_all and len(data['location']) > 0 \
            and data['title'] != data['location']:
            output = output + '\n' + data['location']
    else:
        output = data['title'] + MSG_NO_INFO_FOUND

    return output

def format_timer_info():
    output = ''

    if len(timer) > 0:
        output += '\n'.join(l[0] + ': ' + str(l[1]) for l in timer)

    if len(cache.timer) > 0:
        output += '\n'.join(l[0] + ': ' + str(l[1]) for l in cache.timer)

    return output

def parse_text_query(strings):
    """ Takes in an array of strings and extracts recognized months, 
    categories, and cities with climate data. Case- and order-insensitive,
    except city names must appear together.
    The logic used to try to stitch together multi-word city 
    Wikipedia article names (e.g. "Hamilton, New Zealand") is essentially 
    brute-force testing everything (so "Hamilton", "Hamilton New", 
    "Hamilton, New", "Hamilton New Zealand", "Hamilton New Zealand" until a 
    match is found or combinations are exhausted. Because of this, 
    the first lookup for a query with a long or unrecognized city name
    might take a while as we're sending a number of HTTP queries to Wikipedia.
    If caching is active, subsequent lookups should be near-instant. 
    However, if caching is not active, each lookup might be particularly slow 
    as the city-name-searching algorithm sends a number of queries and 
    the actual data retrieval makes further queries.
    So have caching on. (Or change the code.) """

    KEYWORDS = ['in', 'vs', 'versus', 'and', 'for']

    def city_has_data(city):
        data = get_climate_data(city)
        has_data = has_printable_data(data)

        return has_data

    result = {'cities': [], 'months': [], 'categories': []}

    result['months'] = [False]*12
    result['categories'] = dict((k,False) for k in ROWS)
    category_aliases = dict((v,k) for k,v in PRINTED_ROW_TITLES.iteritems())
    cities = []

    for param in strings:
        # classify each param
        param = param.decode('utf-8')

        classified = False

        # find months
        month_param = param.title()
        if month_param in calendar.month_abbr:
            month_number = list(calendar.month_abbr).index(month_param)
            result['months'][month_number - 1] = True
            classified = True
        if month_param in calendar.month_name:
            month_number = list(calendar.month_name).index(month_param)
            result['months'][month_number - 1] = True
            classified = True

        # find categories
        category_param = param.lower()
        if category_param in result['categories']:
            result['categories'][category_param] = True
            classified = True
        if category_param in category_aliases:
            result['categories'][category_aliases[category_param]] = True
            classified = True
        if category_param == 'location':
            result['categories']['location'] = True
            classified = True

        if classified is False and not param.lower() in KEYWORDS:
            cities.append(param)

    # find cities that we can find climate data for
    i = 0
    while i < len(cities):
        # first, try each string on its own
        city = cities[i].title()
        has_data = city_has_data(city)

        j = i
        while has_data == False and j < len(cities) - 1:
            # Single string was not recognized.
            # Try to build a page name we can recognize by adding in
            # strings that follow this one in the array

            # try using only spaces
            new_city = ' '.join(cities[i:j+2]).title()
            has_data = city_has_data(new_city)

            k = j+1
            while has_data == False and k < len(cities):
                # if just spaces didn't result in anything recognizable,
                # try using commas in any possible position
                new_city = ' '.join(cities[i:j+1]) + ', ' \
                    + ' '.join(cities[j+1:k+1])
                new_city = new_city.title()
                has_data = city_has_data(new_city)
                k += 1

            if has_data == True:
                city = new_city
                i = j + 1 # skip strings we've used this time
            else:
                j += 1 # look one more position further in the array

        if has_data == True:
            # we have a recognized city name, add it to the collection
            result['cities'].append(city)

        i += 1

    return result


if __name__ == '__main__':
    cities = get_cities()

    print_all_rows = '-a' in cities
    print_debug = '-t' in cities

    if print_all_rows:
        cities.remove('-a')
    if print_debug:
        cities.remove('-t')

    parsed_cities = parse_text_query(cities)['cities']

    if len(parsed_cities) > 0:
        print_cities = parsed_cities
    else:
        print_cities = cities

    for city in print_cities:
        data = get_climate_data(city)
        print format_data_as_text(data, print_all = print_all_rows)

    if print_debug:
        print format_timer_info()

