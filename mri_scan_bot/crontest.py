#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime

cron_log = '/Users/manusdonahue/Desktop/cron_log.txt'
with open(cron_log, 'a+') as f:
    f.write(f'\ncronjob is running. time is {datetime.datetime.now()}')