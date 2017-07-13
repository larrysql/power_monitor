#!/usr/local/bin/python
# -*- coding: utf-8
from __future__ import division
import sys
import os
import subprocess
import time
import string
import datetime
from  utils.utility import *

#check listener status
def chk_lsnr_status(cls,type):
    funcName = sys._getframe().f_code.co_name
    msg = funcName + ':开始执行listener状态检查'
    wr_log('info',msg)
    d = get_inst_info()
    if d:
        inst_id = d['inst_id']
    else:
        msg = funcName + ':该实例没有在监控系统中注册！'
        wr_log('warning',msg)
        return 1
    d = get_mul_lim_val(inst_id,cls,type)
    if d is None:
        msg = funcName + ':该实例在监控系统中没有注册监控指标！'
        wr_log('warning',msg)
        return 1
    print d
    for k in d:
        if d[k][4] == 0:
            continue
        cmd = 'ps -ef|grep tnsl|grep -i ' + k + '|grep -v grep|wc -l'
	#print cmd
        f = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        for line in f.stdout.readlines():
            if int(line) > 0:
                msg = funcName + '监听进程' + k + '已启动!'
                wr_log('info',msg)
            else:
		#print '监听进程' + k + '未启动!'
                content = "监听进程" + k + "未启动!"
                lv = 1
                alert_id = d[k][3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)

#check listener log size
def chk_file_size(cls,type):
    funcName = sys._getframe().f_code.co_name
    msg = funcName + ':开始执行文件大小检查'
    wr_log('info',msg)
    d = get_inst_info()
    if d:
        inst_id = d['inst_id']
    else:
        msg = funcName + ':该实例没有在监控系统中注册！'
        wr_log('warning',msg)
        return 1
    d = get_mul_lim_val(inst_id,cls,type)
    if d is None:
        return 1
    #print d
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
	funcName = sys._getframe().f_code.co_name
	msg = funcName + ':开始执行alert日志检查'
	wr_log('info',msg)
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
		#print 'alert_log===============',alt_log
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
					if chk_key_in_str(alert_key,v):
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
			if chk_key_in_str(alert_key,v):
				s = k + "|" + v
				nl.append(s)
		#print "nl=================",nl
		return nl
	except Exception,e:
		nl = []
		msg = funcName + ":数据库警告日志检查失败:" + str(e)
                wr_log('warning',msg) 
		return nl
def chk_rman_log(cls,type):
        funcName = sys._getframe().f_code.co_name
        msg = funcName + ':开始执行rman日志检查'
        wr_log('info',msg)
	d = get_inst_info()
	if d:
		inst_id = d['inst_id']
		db_name = d['db_name']
	else:
		msg = funcName + ':该实例没有在监控系统中注册！'
		wr_log('warning',msg)
		return 1
	d = get_mul_lim_val(inst_id,cls,type)
	#print "d========",d 
	if d is None:
		msg = funcName + ':该实例在监控系统中没有注册监控指标！'
                wr_log('warning',msg)
		return 1
	for k in d:
		#print 'd[k][4]=========',d[k][4]
		if d[k][4]  != 1:
			continue
		log = k
		#print "log ======" + log
		cmd = 'ps -ef|grep ora_smon|grep ' + db_name + ' |grep -v grep'
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
						msg = funcName + ":rman备份日志检查正常"
						wr_log('info',msg)
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
        funcName = sys._getframe().f_code.co_name
        msg = funcName + ':开始执行exp日志检查'
        wr_log('info',msg)
	d = get_inst_info()
	if d:
		inst_id = d['inst_id']
	else:
		funcName = sys._getframe().f_code.co_name
		msg = funcName + ':该实例没有在监控系统中注册！'
		wr_log('warning',msg)
		return 1
	d = get_mul_lim_val(inst_id,cls,type)
	if d is None:
		msg = funcName + ':没有找到该检查项的监控指标!'
		wr_log('warning',msg)
		return 1
	for k in d:
		#print 'd[k]======================',d[k]
		if d[k][4]  != 1:
			msg = funcName + ':没有启用该项监控指标,略过检查'
			wr_log('warning',msg)
			continue
		log = k		
		cmd = 'ps -ef|grep ora_smon|grep -v grep'
		day = get_time('day')
		f = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).stdout.readlines()
		if len(f) > 0:
			for line in f:
				sid = line.split()[-1:][0].split('_')[-1:][0].strip()
				logname = log.replace('{sid}',sid).replace('{date}',day).strip()
				#print logname
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
					msg = funcName + ":expdp备份日志正常"
					wr_log('info',msg)
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
			

	
	
		
