#!/usr/bin/env python
# coding=utf-8

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import calendar

class Climate(callbacks.Plugin):
    """ Supybot -> climate.py interface. `get` is the main function. """

    """ In case of problems:
    - climate missing: copy or create a link to climate.py in the Climate 
    plugin directory (where plugin.py, __init.py__, config.py also live)
    - cache missing: same as above, only for cache.py

    - unicode blargs in callbacks.py in irc.reply():
    older versions of supybot don't like unicode replies.
    If you don't want to update the whole package, make a change like 
    the following in $supybot_src/callbacks.py:
    https://github.com/jamessan/Supybot/commit/5bb6fdcd5202fcdeb9d4f6f1f865ff21160f1f9e
    (basically, replace
        s = str(s)
    with
        if not isinstance(s, basestring):
            # avoid trying to str() unicode
            s = str(s) # Allow non-string esses.
    """

    def get(self, irc, msg, args, strings):
        """ <text> (including <places>, <months>, <categories>)
        Gets climate data for <places> during <months> for <categories>.
        Normally at least one each of place and month are required,
        except script will pick most contrasting month if two cities are given.
        Category will default to average high temperature if not specified.
        Get the list of recognized <categories> with `@climate categories`.
        Places, months, and categories can be mixed within <text> in any order.
        Unrecognized words will be silently ignored (this means you can write
        e.g. "Toronto and Sydney high for December"). """

        import climate

        query = climate.parse_text_query(strings)

        cities = query['cities']
        months = query['months']
        categories = query['categories']

        has_category = False
        has_month = False

        for month in months:
            has_month = has_month or month

        for category in categories:
            has_category = has_category or categories[category]

        if has_category is False:
            # default to showing high temperature if no category is specified
            categories['high C'] = True
            has_category = True

        if has_month is True:
            data = climate.get_comparison_data(cities, months, categories)
        elif len(cities) == 2:
            # get data for all, and pick most interesting one automagically
            # criterion is biggest difference between the numerical values
            # among chosen categories for the chosen cities

            # for now only two cities are supported
            # TODO: expand to arbitrary amount - will need to round-robin
            # the calculations or something

            for i in range(len(months)):
                months[i] = True

            data = climate.get_comparison_data(cities, months, categories)

            # get cities' names directly from data - they are likely 
            # different than in request (capitalization, redirects, etc)
            data_cities = data[data.keys()[0]].keys()

            comparisons = {}
            sums = {}
            for i in range(len(data_cities)):
                city = data_cities[i]
                for category,category_include in categories.items():
                    if not category_include:
                        continue

                    if category == 'location':
                        # only non-numerical 'category' so far. cannot 
                        # be compared. detect this case more robustly if we
                        # get more non-numerical categories
                        continue

                    if category not in comparisons:
                        comparisons[category] = {}
                        sums[category] = []

                    for month,month_include in enumerate(months):
                        if not month_include:
                            continue

                        if not month in comparisons[category]:
                            comparisons[category][month] = {}

                        comparisons[category][month][city] = \
                            data[month][city][category]

                    if i > 0:
                        for m,dummy_var in enumerate(months):
                            # calculate difference between the two cities for
                            # each month

                            # order within sums[category] list will be created
                            # automagically
                            sums[category].append(abs( \
                                comparisons[category][m][data_cities[i-1]] - \
                                comparisons[category][m][data_cities[i]]))

            max_month = -1
            max_value = float('-inf')
            for category in categories:
                if category in sums:
                    category_max = max(sums[category])
                    category_index = sums[category].index(category_max)
                    if category_max > max_value:
                        max_value = category_max
                        max_month = category_index

            filtered_data = {}
            if max_month > -1:
                filtered_data[max_month] = data[max_month]
            data = filtered_data
        else:
            # not supported, return empty
            data = {}

        # output format is roughly:
        """October: Toronto high 10, Melbourne high 20; April: Toronto high 10, Melbourne high 15

October: Toronto high 10, low 5, Melbourne high 20, low 12; April: Toronto high 10, low 3, Melbourne high 15, low 8"""
        # so each month first, then each city with its categories grouped

        output = []
        for month,month_data in data.items():
            month_line = calendar.month_name[month+1] + ': '

            city_lines = []
            for city,city_data in month_data.items():
                city_line = city + ' '

                category_lines = []
                for category,category_data in city_data.items():
                    if category in climate.PRINTED_ROW_TITLES:
                        category_lines.append(
                            climate.PRINTED_ROW_TITLES[category]
                            + ' ' + str(int(round(category_data, 0))))

                city_line += ', '.join(category_lines)
                city_lines.append(city_line)

            month_line += ', '.join(city_lines)
            output.append(month_line)

        output = '; '.join(output)

        response = ''
        if len(output) > 0:
            response = output
        elif len(cities) == 1 and 'location' in categories \
            and categories['location'] == True:
            data = climate.get_climate_data(cities[0])
            if 'location' in data and len(data['location']) > 0:
                response = data['title'] + ': ' + data['location']
        
        if len(response) == 0:
            response = 'No data found or invalid query. Try @help climate get.'

        irc.reply(response.encode('utf-8'), prefixNick = False)

    def categories(self, irc, msg, args):
        """ <none>
        Prints the climate categories recognized by `@climate get` """

        import climate

        result = 'Supported categories: '
        cats = []

        for category in climate.ROWS:
            aliases = []

            if category in climate.PRINTED_ROW_TITLES:
                alias = climate.PRINTED_ROW_TITLES[category]
                if not alias == category:
                    if alias.find(' ') > -1:
                        aliases.append('"%s"' % alias)
                    else:
                        aliases.append(alias)

            if category.find(' ') > -1:
                aliases.append('"%s"' % category)
            else:
                aliases.append(category)

            cats.append('/'.join(aliases))

        result += ', '.join(cats)

        irc.reply(result, prefixNick = False)
 
    get = wrap(get, [many('anything')])
    categories = wrap(categories)

Class = Climate

