#!/usr/bin/env python
# coding=utf-8

from __future__ import unicode_literals
import os
import glob
import urllib2
import simplejson as json
from datetime import datetime
from datetime import timedelta
import time

timer = []

CACHE_PERIOD_DAYS = 7
CACHE_DIR  = 'cache_data'
CACHE_FILE = 'climate.py_cache_%s'

def get_file_name(page_name):
    return os.path.join(CACHE_DIR, CACHE_FILE % page_name)

def get_age(page_name):
    # default to something that times out.
    # optimally we'd return infinity or something but meh
    age = timedelta(days = CACHE_PERIOD_DAYS, seconds = 0)

    file_name = get_file_name(page_name)
    if os.path.exists(file_name):
        timestamp = os.path.getmtime(file_name)
        age = datetime.now() - datetime.fromtimestamp(timestamp)

    return age

def exists(page_name):
    result = False

    age = get_age(page_name)
    if age.days < CACHE_PERIOD_DAYS:
        result = True

    return result

def get_URL(url, page_name, force_download = False):
    htime1 = time.time()

    text = None

    cached_data_file_name = get_file_name(page_name)

    if exists(page_name) and not force_download:
        f = open(cached_data_file_name, 'r')
        text = f.read()
        f.close()

        timer.append(['%s: file load time, ms' % page_name,
            (time.time()-htime1)*1000.0])

        timer.append(['%s: using cached data, age in days' % page_name,
            get_age(page_name).days])

    if text is None:
        text = urllib2.urlopen(url).read()

        if os.path.exists(CACHE_DIR) == False:
            os.makedirs(CACHE_DIR)

        # save text for future use
        f = open(cached_data_file_name, 'w')
        print >> f, text
        f.close()

        timer.append(['%s: http get and file save, ms' % page_name,
            (time.time()-htime1)*1000.0])

    return text

def clear(page_name):
    to_be_removed = get_file_name(page_name)

    if os.path.exists(to_be_removed):
        os.remove(to_be_removed)

    return [ to_be_removed ]

def clear_all():
    cached_data_files = glob.glob(get_file_name('*'))

    for fl in cached_data_files:
        os.remove(fl)

    return cached_data_files

