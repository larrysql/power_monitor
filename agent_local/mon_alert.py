#!/usr/local/bin/python
# -*- coding: utf-8
from __future__ import division
import cx_Oracle
import sys
import urllib
import types
import os
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
#from  utils.utility import *
from chkfunc import pm_os,pm_db_other,pm_db_tbs,pm_db_runstat
from  utils.utility import *


#调用执行main函数
if __name__=="__main__":
	b_alert = ''
	while True:
		cpu_used = pm_os.cpu_usage('os','cpu','cpu')
		pm_os.fs_usage('os','filesystem')
		pm_os.mem_usage('os','memory','memory')
		pm_db_other.chk_lsnr_status('runstat','listener')
		pm_db_other.chk_file_size('os','filesize')
		#check alert log 
		e_alert = pm_db_other.chk_alert_log()
		alert = list(set(e_alert).difference(set(b_alert)))
		b_alert = e_alert
		if len(alert) > 0:
			d = get_inst_info()
			inst_id = d['inst_id']
			d = get_mul_lim_val(inst_id,'log','alert')
			print '*******************************************************' , d
			content = "次要告警:oracle alert日志告警:" + ''.join(alert)
			alert_id = d['db_alert'][3]
			lv = 1
			alert_info = {'alert_id':alert_id,'content':content,'level':lv}
			wr_alert(alert_info)
		###check rman backup log and expdb log
		pm_db_other.chk_rman_log('log','rman_log')
		pm_db_other.chk_exp_log('log','exp_log')
		#check tablespace 
		pm_db_tbs.chk_tbs_usage('tablespace','tablespace')
		pm_db_tbs.chk_temp_tbs_usage('tablespace','temp_tablespace')
		#pm_db_tbs.chk_undo_tbs_usage('UNDO')
		#pm_db_tbs.rcybin_space_usage('RECYCLEBIN','PERCENT')
		#pm_db_tbs.rcybin_obj_cnt('RECYCLEBIN','COUNT')
		#pm_db_tbs.chk_db_file_cnt('DBFILES','DBFILES')
		#pm_db_runstat.chk_inst_status()
		#sep_info = "\n---------------------------------------------------------------------------\n"
		#wr_alert(sep_info)
		time.sleep(10)
