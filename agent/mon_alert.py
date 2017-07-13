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
import socket 
#from  utils.utility import * 
from chkfunc import pm_os,pm_db_other,pm_db_tbs,pm_db_runstat,pm_db_grid,pm_db_asm
from  utils.utility import *


#调用执行main函数
if __name__=="__main__":
	b_alert = ''
	d = get_inst_info()
	if d:
		inst_id = d['inst_id']
	else:
		print '该实例没有在监控系统中注册！退出监控程序....'
		sys.exit()
	d = get_mul_lim_val(inst_id,'log','alert')
	#取得采样时间间隔
	si = get_snap_interval(inst_id)
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
		#print 'alert=',alert
		if len(alert) > 0:
			print 'd=*******************************************************' , d
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
		pm_db_tbs.chk_undo_tbs_usage('tablespace','undo_tablespace')
		pm_db_tbs.rcybin_space_usage('tablespace','recyclebin','used_pct')
		#pm_db_tbs.rcybin_obj_cnt('tablespace','recyclebin','obj_cnt')
		#pm_db_tbs.chk_db_file_cnt('DBFILES','DBFILES')
		pm_db_runstat.chk_inst_status()
                pm_db_grid.chk_grid_status('grid','state')
                pm_db_asm.chk_asm_status()
		#sep_info = "\n---------------------------------------------------------------------------\n"
		#wr_alert(sep_info)
		time.sleep(si)
