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
from  utils.utility import *

conf_fname = 'config/powerm.conf'

#检查表空间使用率
def chk_tbs_usage(cls,type):
    d = get_inst_info()
    inst_id = d['inst_id']
    d = get_mul_lim_val(inst_id,cls,type)
    if d is None:
        return 1
    #print d
    sql = '''
SELECT
    d.tablespace_name                                   name
  , d.status                                            status
  , d.contents                                          type
  , d.extent_management                                 extent_mgt
  , d.segment_space_management                          segment_mgt
  , NVL(a.bytes, 0)/1024/1024                           ts_size
  , NVL(f.bytes, 0)/1024/1024                           free
  , NVL(a.bytes - NVL(f.bytes, 0), 0)/1024/1024         used
  , round(NVL((a.bytes - NVL(f.bytes, 0)) / a.bytes * 100, 0))
                                                        pct_used
FROM 
    sys.dba_tablespaces d
  , ( select tablespace_name, sum(bytes) bytes
      from dba_data_files
      group by tablespace_name
    ) a
  , ( select tablespace_name, sum(bytes) bytes
      from dba_free_space
      group by tablespace_name
    ) f
WHERE
      d.tablespace_name = a.tablespace_name(+)
  AND d.tablespace_name = f.tablespace_name(+)
  AND NOT (
    d.extent_management like 'LOCAL'
    AND
    d.contents like 'TEMPORARY'
  )
UNION ALL 
SELECT
   d.tablespace_name                            name
  ,  d.status                                    status
  , d.contents                                   type
  , d.extent_management                          extent_mgt
  , d.segment_space_management                   segment_mgt
  , NVL(a.bytes, 0)/1024/1024                    ts_size
  , NVL(a.bytes - NVL(t.bytes,0), 0)/1024/1024   free
  , NVL(t.bytes, 0)/1024/1024                    used
  , TRUNC(NVL(t.bytes / a.bytes * 100, 0))       pct_used 
FROM
    sys.dba_tablespaces d
  , ( select tablespace_name, sum(bytes) bytes
      from dba_temp_files
      group by tablespace_name
    ) a
  , ( select tablespace_name, sum(bytes_cached) bytes
      from v$temp_extent_pool
      group by tablespace_name
    ) t
WHERE
      d.tablespace_name = a.tablespace_name(+)
  AND d.tablespace_name = t.tablespace_name(+)
  AND d.extent_management like 'LOCAL'
  AND d.contents like 'TEMPORARY'
'''
    try:
        db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA) 
        cursor = db.cursor()
        cursor.execute(sql)
        rs = cursor.fetchall()
        for row in rs:
       #print row[0] + '   ' + row[1] + '   ' + row[2] + '   ' + row[3] + '   ' + row[4] + '   ' + str(row[5]) + '   ' + str(row[6]) + '   ' + str(row[7]) + '   ' + str(row[8])
            #print 'row[0] ===' + row[0]
            #print d.keys()
            if row[0] in d.keys():
                k = row[0]
                lv1,lv2,lv3 = int(d[k][0]),int(d[k][1]),int(d[k][2])
                print 'row[8] = ' + str(row[8]) + 'lv1=' + str(lv1)
                if row[8] >=lv1 and row[8] < lv2:
                    content = "次要告警:表空间" + row[0] + "空间使用率" + str(row[8]) + "%,告警阈值" + str(lv1) + "%."
                    alert_id = d[k][3]
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[8] >=lv2 and row[8] < lv3:
                    content = "主要告警:表空间" + row[0] + "空间使用率" + str(row[8]) + "%,告警阈值" + str(lv2) + "%."
                    alert_id = d[k][3]
                    lv = 2
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[8] >=lv3:
                    content = "严重告警:表空间" + row[0] + "空间使用率" + str(row[8]) + "%,告警阈值" + str(lv3) + "%."
                    alert_id = d[k][3]
                    lv = 3
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    print "表空间" + row[0] + "使用率正常，已使用" + str(row[8]) + "%"
            else:
                lv1,lv2,lv3 = 70,80,90 
                if row[8] >=lv1 and row[8] < lv2:
                    content = "次要告警:表空间" + row[0] + "空间使用率" + str(row[8]) + "%,告警阈值" + str(lv1) + "%."
                    alert_id = None 
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[8] >=lv2 and row[8] < lv3:
                    content = "主要告警:表空间" + row[0] + "空间使用率" + str(row[8]) + "%,告警阈值" + str(lv2) + "%."
                    alert_id = None
                    lv = 2
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[8] >=lv3:
                    content = "严重告警:表空间" + row[0] + "空间使用率" + str(row[8]) + "%,告警阈值" + str(lv3) + "%."
                    alert_id = None
                    lv = 3
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    print "表空间" + row[0] + "使用率正常，已使用" + str(row[8]) + "%"

        cursor.close()
        db.close()
    except StandardError,e:
        content = "chk_tbs_usage:数据库状态异常!"
        alert_id = None
        lv = 1
        alert_info = {'alert_id':alert_id,'content':content,'level':lv}
        wr_alert(alert_info)
        #sys.exit()
def chk_temp_tbs_usage(cls,type):
    d = get_inst_info()
    inst_id = d['inst_id']
    d = get_mul_lim_val(inst_id,cls,type)
    if d is None:
        return 1 
    sql = '''SELECT A.tablespace_name tablespace, 
	   D.mb_total,
	   SUM (A.used_blocks * D.block_size) / 1024 / 1024 mb_used,
	   D.mb_total - SUM (A.used_blocks * D.block_size) / 1024 / 1024 mb_free,
	   round((SUM (A.used_blocks * D.block_size) / 1024 / 1024/D.mb_total),2) pct_used
FROM v$sort_segment A,
	(
	SELECT B.name, C.block_size, SUM (C.bytes) / 1024 / 1024 mb_total
	FROM v$tablespace B, v$tempfile C
	WHERE B.ts#= C.ts#
	GROUP BY B.name, C.block_size
	) D
WHERE A.tablespace_name = D.name
GROUP by A.tablespace_name, D.mb_total''' 
    try:
        db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA)
        cursor = db.cursor()
        cursor.execute(sql)
        rs = cursor.fetchall()
        for row in rs:
            if row[0] in d.keys():
                k = row[0]
                lv1,lv2,lv3 = int(d[k][0]),int(d[k][1]),int(d[k][2])
                print 'row[4] = ' + str(row[4]) + 'lv1=' + str(lv1)
                if row[4] >=lv1 and row[4] < lv2: 
                    content = "次要告警:临时表空间" + row[0] + "空间使用率" + str(row[4]) + "%,告警阈值" + str(lv1) + "%."
                    alert_id = d[k][3]
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[4] >=lv2 and row[4] < lv3:
                    content = "主要告警:临时表空间" + row[0] + "空间使用率" + str(row[4]) + "%,告警阈值" + str(lv2) + "%."
                    alert_id = d[k][3]
                    lv = 2
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[4] >=lv3:
                    content = "严重告警:临时表空间" + row[0] + "空间使用率" + str(row[4]) + "%,告警阈值" + str(lv3) + "%."
                    alert_id = d[k][3]
                    lv = 3
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    print "临时表空间" + row[0] + "使用率正常，已使用" + str(row[4]) + "%"
            else:
                lv1,lv2,lv3 = 70,80,90 
                if row[4] >=lv1 and row[4] < lv2:
                    content = "次要告警:临时表空间" + row[0] + "空间使用率" + str(row[4]) + "%,告警阈值" + str(lv1) + "%."
                    alert_id = None 
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[4] >=lv2 and row[4] < lv3:
                    content = "主要告警:临时表空间" + row[0] + "空间使用率" + str(row[4]) + "%,告警阈值" + str(lv2) + "%."
                    alert_id = None
                    lv = 2
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[4] >=lv3:
                    content = "严重告警:临时表空间" + row[0] + "空间使用率" + str(row[4]) + "%,告警阈值" + str(lv3) + "%."
                    alert_id = None
                    lv = 3
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    print "临时表空间" + row[0] + "使用率正常，已使用" + str(row[4]) + "%"            
        cursor.close()
        db.close()
    except Exception,e:
        #content = "chk_tbs_usage:数据库状态异常!"
        content = str(e)
        alert_id = None
        lv = 1 
        alert_info = {'alert_id':alert_id,'content':content,'level':lv}
        wr_alert(alert_info)
def chk_undo_tbs_usage(cls):
    d = get_conf_mul_val(conf_fname,cls)
    sql = '''
        select a.tablespace_name tablespace
      ,b.status                             status
      ,b.bytes                              sizeb
      ,a.bytes                              sizea
      ,round(100*(b.bytes/a.bytes),2)       pct
from 
   (select tablespace_name
          ,sum(bytes)/1024/1024 bytes 
    from dba_data_files 
    group by tablespace_name) a,
   (select tablespace_name
          ,status
          ,sum(bytes)/1024/1024 bytes 
    from dba_undo_extents 
    group by tablespace_name,status) b
where a.tablespace_name=b.tablespace_name
order by 1,2
    '''
    try:
        db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA)
        cursor = db.cursor()
        cursor.execute(sql)
        rs = cursor.fetchall()
        for row in rs:
            if row[0] in d.keys() and row[1] == 'ACTIVE':
                pct_lim = int(d[row[0]])
                if row[4] > pct_lim:
                    alert_info = "UNDO表空间使用率告警:" + row[0] + "活动空间使用率" + str(row[4]) + "%,告警阈值" + str(pct_lim) + "%"
                    wr_alert(alert_info)
                else:
                    print "undo表空间使用正常:" + row[0] + "活动空间使用率" + str(row[4])
            elif row[1] == 'ACTIVE':
                pct_lim = 50
                if row[4] > pct_lim:
                    alert_info = "UNDO表空间使用率告警:" + row[0] + "活动空间使用率" + str(row[4]) + "%,告警阈值50%"            
                    wr_alert(alert_info)
                else:
                    print "undo表空间使用正常:" + row[0] + "活动空间使用率" + str(row[4]) 
            else:
                pass
        cursor.close()
        db.close()
    except Exception,e:
        alert_info = "chk_undo_tbs_usage:数据库连接失败!请检查"
        wr_alert(alert_info)
def rcybin_space_usage(cls,val):
    lim_val = get_conf_val(conf_fname,cls,val)
    if lim_val is None:
        lim_val = 5
    else:
        lim_val = int(lim_val)
    sql = '''
select a.tablespace_name,
      round(nvl(100*b.bytes/a.bytes,0)) pct
from ( select tablespace_name, sum(bytes) bytes
       from dba_data_files
       group by tablespace_name) a
    ,( select tablespace_name, sum(bytes) bytes
       from dba_segments
       where segment_name like 'BIN$%==$0'
       group by tablespace_name) b
where a.tablespace_name = b.tablespace_name(+)
   ''' 
    try:
        db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA)
        cursor = db.cursor()
        cursor.execute(sql)
        rs = cursor.fetchall() 
        for row in rs:
            if row[1] > lim_val:
                alert_info = "回收站占用比例告警:表空间" + row[0] + "回收站使用空间" + str(row[1]) + "%,告警阈值" + str(lim_val) + "%"
                wr_alert(alert_info)
            else:
                print "回收站占用表空间比例正常,表空间" + row[0] + "回收站使用空间占比" + str(row[1]) + "%"
    except Exception,e:
        alert_info = "rcybin_space_usage:数据库连接失败!请检查"
        wr_alert(alert_info)
def rcybin_obj_cnt(cls,val):
    lim_val = get_conf_val(conf_fname,cls,val)
    if lim_val is None:
        lim_val = 2000
    else:
        lim_val = str(lim_val)
    sql = '''
    select tablespace_name, count(*) cnt
       from dba_segments
       where segment_name like 'BIN$%==$0'
       group by tablespace_name
    '''
    try:
        db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA)
        cursor = db.cursor()
        cursor.execute(sql)
        rs = cursor.fetchall() 
        for row in rs:
            if row[1] > lim_val:
                alert_info = "回收站对象数量告警:表空间" + row[0] + "的回收站对象数量为" + str(row[1]) + ",告警阈值" + str(lim_val)
                wr_alert(alert_info)
            else:
                print "回收站对象数量正常,表空间" + row[0] + "的回收站对象数量为" + str(row[1])
    except Exception,e:
        alert_info = "rcybin_obj_cnt:数据库连接失败!请检查"
        wr_alert(alert_info)
def chk_db_file_cnt(cls,val):
    lim_val = get_conf_val(conf_fname,cls,val)
    if lim_val is None: 
        lim_val = 80
    else:
        lim_val = str(lim_val)
    sql = '''
    select cnt1+cnt2 used_cnt, c.value max_cnt ,(cnt1+cnt2)/c.value*100
from 
    (select count(*) cnt1 
	 from dba_data_files) a,
	 (select count(*) cnt2
	 from dba_temp_files
	 ) b,
     (select value from v$parameter where name='db_files') 
	 c
    '''
    try:
        db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA)
        cursor = db.cursor()
        cursor.execute(sql)
        rs = cursor.fetchall()
        for row in rs:
            if row[2] > lim_val:
                alert_info = "数据文件数量告警,数据库数据文件数量" + str(row[0]) + ",最大数据文件数量为" + str(row[1]) + ",告警阈值" + str(lim_val) + "%"
                wr_alert(alert_info)
            else:
                print "数据文件数量正常,当前数据文件数量" + str(row[0]) + ",最大数据文件数量为" + str(row[1])
    except Exception,e:
        alert_info = "chk_db_file_cnt:数据库连接失败!请检查"
        wr_alert(alert_info)
#if __name__=="__main__":
    #chk_temp_tbs_usage('TEMP')
    #chk_tbs_usage('TABLESPACE')
