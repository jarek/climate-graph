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
    - xltrtr missing: copy or create a link to xltrtr.py in the Transliterator 
    directory (where plugin.py, __init.py__, config.py also live)

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
        At least one each of place and month are required.
        Category will default to average high temperature if not specified.
        Get the list of recognized <categories> with `@climate categories`.
        Places, months, and categories can be mixed within <text> in any order.
        Unrecognized words will be silently ignored (this means you can write
        e.g. "Toronto and Sydney high for December"). """

        import climate

        KEYWORDS = ['in', 'vs', 'versus', 'and', 'for']

        cities = []
        months = [False]*12
        categories = dict((k,False) for k in climate.ROWS)
        category_aliases = dict((v,k) for k,v in \
            climate.PRINTED_ROW_TITLES.iteritems())

        has_category = False
        # has_month = False
        # TODO: automagically pick a month with largest differences for chosen
        # category/ies if no month is specified

        for param in strings:
            # classify each param
            param = param.decode('utf-8')

            classified = False

            month_param = param.title()
            if month_param in calendar.month_abbr:
                month_number = list(calendar.month_abbr).index(month_param)
                months[month_number - 1] = True
                classified = True
            if month_param in calendar.month_name:
                month_number = list(calendar.month_name).index(month_param)
                months[month_number - 1] = True
                classified = True

            category_param = param.lower()
            if category_param in climate.ROWS:
                categories[category_param] = True
                has_category = True
                classified = True
            if category_param in category_aliases:
                categories[category_aliases[category_param]] = True
                has_category = True
                classified = True

            if classified is False and not param.lower() in KEYWORDS:
                cities.append(param)

        if has_category is False:
            # default to showing high temperature if no category is specified
            categories['high C'] = True
            has_category = True

        data = climate.get_comparison_data(cities, months, categories)

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
                    category_lines.append(climate.PRINTED_ROW_TITLES[category]
                        + ' ' + str(int(round(category_data, 0))))

                city_line += ', '.join(category_lines)
                city_lines.append(city_line)

            month_line += ', '.join(city_lines)
            output.append(month_line)

        output = '; '.join(output)

        irc.reply(output, prefixNick = False)

    def categories(self, irc, msg, args):
        """ <none>
        Prints the climate categories recognized by `@climate get` """

        import climate

        result = 'Supported categories: '
        cats = []

        for category in climate.ROWS:
            aliases = []

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

