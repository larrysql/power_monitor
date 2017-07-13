#!/usr/local/bin/python
# -*- coding: utf-8
from __future__ import division
import cx_Oracle
import sys
import urllib
import types
import os
import subprocess
import commands
import time
import string
import datetime
import logging
from  utils.utility import *

conf_fname = 'config/powerm.conf'

#check listener status
def chk_lsnr_status(cls,type):
    d = get_inst_info()
    inst_id = d['inst_id']
    d = get_mul_lim_val(inst_id,cls,type)
    if d is None:
        return 1
    print d
    for k in d:
        cmd = 'ps -ef|grep ' + k + '|grep -v grep|wc -l'
	#print cmd
        f = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        for line in f.stdout.readlines():
            if int(line) > 0:
                print '监听进程' + k + '已启动!'
            else:
		#print '监听进程' + k + '未启动!'
                content = "监听进程" + k + "未启动!"
                lv = 1
                alert_id = d[k][3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)

#check listener log size
def chk_file_size(cls,type):
    d = get_inst_info()
    inst_id = d['inst_id']
    d = get_mul_lim_val(inst_id,cls,type)
    if d is None:
        return 1
    print d
    for k in d:
        log_name = k
        if os.path.exists(log_name):
            cmd = 'du -sm ' + log_name
            f = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).stdout.read()
            log_size = int(string.strip(f.split()[0]))
            if log_size >= int(d[k][0]) and log_size <int(d[k][1]):
                content = "次要告警:listener日志文件" + log_name + "过大！"
                lv = 1
                alert_id = d[k][3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
			#	print commands.getoutput(cmd)
        else:
            content = "次要告警:listener日志" + log_name + "不存在!"
            lv = 1
            alert_id = d[k][3]
            alert_info = {'alert_id':alert_id,'content':content,'level':lv}
            wr_alert(alert_info)
			#log_size = commands.getoutput(cmd).split()[0]
			#print log_size

	    
         
def chk_alert_log():
	lweek = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
	lmonth = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
	alert_key = ['deadlock detected','bad header','abnormal','abort',
				'ora-','bad block','error','waited too long',
				'not complete','corrupt','offline','fail'
				]
	try:
		db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA)	
		cursor = db.cursor()
		cursor.execute("select value from v$parameter where name = 'background_dump_dest'")
		rs = cursor.fetchone()
		alt_dir = rs[0]
		cursor.execute("select value from v$parameter where name='instance_name'")
		rs = cursor.fetchone()
		alt_file = rs[0]
		alt_log = alt_dir + '/alert_' + alt_file + '.log'#取得alert日志绝对路径
	#print alt_log
		cursor.close()
		db.close()
		nl = []
		v = ''
		k = ''
		if os.path.exists(alt_log):
			f = open(alt_log)
			for line in f:
				l_line = line.split()
				if len(l_line) < 2:
					l_line = ['null','null']
			#print l_line
				if (l_line[0] in lweek and l_line[1] in lmonth):
					if "ORA-" in v :
						s = k + "|" + v 
				#	print "ORA- in s***************************************************************\n************************\n " + s
						nl.append(s)
						v = ''
						k = line
					else:
						v = ''
				else:
					v = v + '|' + line
			f.close()
		#print v
			if "ORA-" in v or "Errors" in v or "Deadlock" in v:
				s = k + "|" + v
				nl.append(s)
		return nl
	except Exception,e:
		nl = []
		print "check alert 连接数据库失败:"
		return nl
def chk_rman_log(cls,type):
	d = get_inst_info()
	inst_id = d['inst_id']
	d = get_mul_lim_val(inst_id,cls,type)
	if d is None:
		return 1
	for k in d:
		log = k
		print "log ======" + log
		cmd = 'ps -ef|grep ora_smon|grep -v grep'
		day = get_time('day')
		f = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).stdout.readlines()
		if len(f) > 0:
			for line in f:
				sid = line.split()[-1:][0].split('_')[-1:][0].strip()
				logname = log.replace('{sid}',sid).replace('{date}',day).strip()
				print logname
				if os.path.exists(logname):
					cmdr = 'grep RMAN- ' + logname
					fr = subprocess.Popen(cmdr,stdout=subprocess.PIPE,shell=True).stdout.readlines()
					if len(fr) > 0:
						content = "RMAN备份报警:" + ','.join(fr).replace('\n',',')
						lv = 1
						alert_id = d[k][3] 
						alert_info = {'alert_id':alert_id,'content':content,'level':lv}
						wr_alert(alert_info)
					else:
						print "rman备份日志检查正常"
				else:
					content = "RMAN备份报警:rman备份日志不存在"
					lv = 1
					alert_id = d[k][3]
					alert_info = {'alert_id':alert_id,'content':content,'level':lv}
					wr_alert(alert_info)
		else:
			content = "RMAN备份报警:ORACLE后台进程不存在,请检查"
			lv = 1
			alert_id = d[k][3]
			alert_info = {'alert_id':alert_id,'content':content,'level':lv}
			wr_alert(alert_info)

def chk_exp_log(cls,type):
	d = get_inst_info()
	inst_id = d['inst_id']
	d = get_mul_lim_val(inst_id,cls,type)
	if d is None:
		return 1
	for k in d:
		log = k		
		cmd = 'ps -ef|grep ora_smon|grep -v grep'
		day = get_time('day')
		f = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).stdout.readlines()
		if len(f) > 0:
			for line in f:
				sid = line.split()[-1:][0].split('_')[-1:][0].strip()
				logname = log.replace('{sid}',sid).replace('{date}',day).strip()
				print logname
			if os.path.exists(logname): 
				cmdr = "egrep 'ORA-|EXP-' " + logname
				fr = subprocess.Popen(cmdr,stdout=subprocess.PIPE,shell=True).stdout.readlines()
				if len(fr) > 0:
					content = "次要告警:EXP备份报警:" + ','.join(fr).replace('\n',',')
					lv = 1
					alert_id = d[k][3]
					alert_info = {'alert_id':alert_id,'content':content,'level':lv}
					wr_alert(alert_info)
				else:
					print "expdp备份日志正常"
			else:
				content = "EXPDP备份报警:expdp备份日志不存在"
				lv = 1
				alert_id = d[k][3]
				alert_info = {'alert_id':alert_id,'content':content,'level':lv}
				wr_alert(alert_info)
		else:
			content = "EXP备份报警:ORACLE后台进程不存在,请检查"
			lv = 1
			alert_id = d[k][3]
			alert_info = {'alert_id':alert_id,'content':content,'level':lv}
			wr_alert(alert_info)
			

	
	
		
