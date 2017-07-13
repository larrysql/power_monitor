#!/usr/local/bin/python
# -*- coding: utf-8
import sys,time
sys.path.append("..")
from datetime import datetime,timedelta
def init_data(dh = 1):
    l = []
    now = datetime.now()
    btime = now - timedelta(hours=dh)
    while (btime + timedelta(seconds=10)) < now:
        btime = btime + timedelta(seconds=10)
        ltime = btime.strftime('%Y/%m/%d %H:%M:%S')
        ltime = time.mktime(time.strptime(ltime,'%Y/%m/%d %H:%M:%S'))*1000
        l.append([ltime,0])
    print l
    return l
