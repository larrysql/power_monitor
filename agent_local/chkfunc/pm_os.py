#!/usr/local/bin/python
# -*- coding: utf-8
from __future__ import division
import cx_Oracle
import sys
import urllib
import types
import os
import subprocess
import time
import datetime
import string
import utils.ora_conn
import smtplib
import socket
from email.mime.text import MIMEText
from email.header import Header
from email.MIMEMultipart import MIMEMultipart
import base64
from  utils.utility import *
reload(sys) 
sys.setdefaultencoding('utf8')

conf_fname = 'config/powerm.conf'

#获取cpu使用率
def cpu_usage(cls,type,name):
    d = get_inst_info()
    inst_id = d['inst_id']
    lim_val = get_lim_val(inst_id,cls,type,name) 
    if lim_val is None:
        #lim_val = [70,80,90]
        return 1
    else:
        lv1,lv2,lv3 = int(lim_val[0]),int(lim_val[1]),int(lim_val[2])
    #print "lim_val = " +  lim_val
        alert_id = lim_val[3]
        alert_info = {}
    f = subprocess.Popen('vmstat 1 2',shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    for i in f.stdout.readlines():
       s = i
    cpu_used = 100 - int(s.split()[14])
    print 'lv1=' + str(lv1) + 'lv2=' + str(lv2) + 'lv3=' + str(lv3)
    print cpu_used >= lv1
    #print "cpu使用率: " + str(cpu_used)
    if cpu_used >= lv1 and  cpu_used < lv2 and lim_val[4] == 1:
        content = "次要告警:当前cpu使用率为" + str(cpu_used) + "||告警阈值" + str(lv1) +"%."
        lv = 1
        alert_info = {'alert_id':alert_id,'content':content,'level':lv}
        wr_alert(alert_info)
    elif cpu_used >= lv2 and cpu_used < lv3 and lim_val[4] == 1:
        content = "主要告警:当前cpu使用率为" + str(cpu_used) + "||告警阈值" + str(lv2) +"%."
        lv = 2
        alert_info = {'alert_id':alert_id,'content':content,'level':lv}
        wr_alert(alert_info)
    elif cpu_used >=lv3 and lim_val[4] == 1:
        content = "严重告警:当前cpu使用率为" + str(cpu_used) + "||告警阈值" + str(lv3) +"%."
        lv =3
        alert_info = {'alert_id':alert_id,'content':content,'level':lv}
        wr_alert(alert_info)
    else:
        print 'CPU使用率检查:正常' + str(cpu_used)
    return cpu_used
#获取文件系统使用率
def fs_usage(cls,type):
    d = get_inst_info()
    inst_id = d['inst_id']
    d = get_mul_lim_val(inst_id,cls,type)
    if d is None:
        return 1
    f = subprocess.Popen('df -k',shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    for line in f.stdout.readlines():
        for k in d:
            if d[k][4] == 0:
                continue
            if k == line.split()[-1]:
                fs_used = int(line.split()[-2].strip('%'))
                #print k + '==========================' + str(fs_used)
                if  fs_used >= int(d[k][0]) and fs_used < int(d[k][1]):
                    content = "次要告警:文件系统" + k + "使用率" + str(fs_used) + "%||告警阈值" + d[k][0] +"%."
                    alert_id = d[k][3]
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif fs_used >= int(d[k][1]) and fs_used < int(d[k][2]):
                     content = "主要告警:文件系统" + k + "使用率" + str(fs_used) + "%||告警阈值" + d[k][1] +"%."
                     alert_id = d[k][3]
                     lv = 2 
                     alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                     wr_alert(alert_info)
                elif fs_used >= int(d[k][2]):
                     content = "严重告警:文件系统" + k + "使用率" + str(fs_used) + "%||告警阈值" + d[k][2] +"%."
                     alert_id = d[k][3]
                     lv = 3 
                     alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                     wr_alert(alert_info)
                else:
                    print '文件系统使用率检查:正常'
#获取内存使用率
def mem_usage(cls,type,name):
    d = get_inst_info()
    inst_id = d['inst_id']
    lim_val = get_lim_val(inst_id,cls,type,name)
    if lim_val is None:
        #lim_val = [70,80,90]
        return 1
    else:
        lv1,lv2,lv3 = int(lim_val[0]),int(lim_val[1]),int(lim_val[2])
    #print "lim_val = " +  lim_val
        alert_id = lim_val[3]
        alert_info = {}
    fd = open('/proc/meminfo')
    lines = fd.readlines()
    for line in lines:
        line = line.strip().replace(' ','')
        if line[-2:]=='kB':
            d[line[:-2].split(':')[0]] = line[:-2].split(':')[1]
        else:
            d[line.split(':')[0]] = line.split(':')[1]
    mem_used = 100*(1-(int(d['MemFree'])+int(d['Buffers'])+int(d['Cached']))/int(d['MemTotal']))
    print "mem_used=" + ('%.2f' % mem_used)
    if mem_used >= lv1 and mem_used < lv2:
        content = "次要告警:当前内存使用率为" + '%.2f' % mem_used + "||告警阈值" + str(lv1) +"%."
        lv = 1 
        alert_info = {'alert_id':alert_id,'content':content,'level':lv} 
        wr_alert(alert_info)
    elif mem_used >= lv2 and mem_used < lv3:
        content = "主要告警:当前内存使用率为" + '%.2f' % mem_used + "||告警阈值" + str(lv2) +"%."
        lv = 1 
        alert_info = {'alert_id':alert_id,'content':content,'level':lv}
        wr_alert(alert_info)
    elif mem_used >= lv3:
        content = "严重告警:当前内存使用率为" + '%.2f' % mem_used + "||告警阈值" + str(lv3) +"%."
        lv = 1
        alert_info = {'alert_id':alert_id,'content':content,'level':lv}
        wr_alert(alert_info)
    else:
        print '内存使用率检查:正常'
