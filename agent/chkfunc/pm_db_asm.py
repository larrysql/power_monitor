#!/usr/local/bin/python
# -*- coding: utf-8
from __future__ import division
import cx_Oracle
import sys
import subprocess
import time
sys.path.append("..")
from  utils.utility import *

def chk_asm_status():
    funcName = sys._getframe().f_code.co_name
    msg = funcName + ':*******************************开始ASM状态检查.***************************************'
    wr_log('info',msg)
    d = get_inst_info()
    if d:
        inst_id = d['inst_id']
    else:
        msg = funcName + ':该实例没有在监控系统中注册！'
        wr_log('info',msg)
        return 1
    #创建数据库连接
    try:
        db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA)
    except Exception,e:
        content = ":数据库连接失败!请检查" + str(e)
        msg = funcName + ':' + content
        wr_log('warning',msg)
        alert_id = inst_id
        lv = 3
        alert_info = {'alert_id':alert_id,'content':content,'level':lv}
        wr_alert(alert_info)
        return 1
    cursor = db.cursor()
    cursor.execute('''select decode(count(*),0,'NOASM','ASM')  check_asm from   v$controlfile where name like '+%' ''')
    rs = cursor.fetchone()
    if rs[0] == 'NOASM':
        msg = funcName + ':没有使用ASM存储,略过检查'
        wr_log('info',msg)
        return 1
    #ASM磁盘组使用率检查
    d = get_lim_val(inst_id,'asm','dg','used_pct')
    if d is None or d[4] == 0:
        msg = funcName + ':ASM磁盘组使用率检查已屏蔽,略过检查'
        wr_log('warning',msg)
    else:
        cursor.execute('''select decode(count(*),0,'NOASM','ASM')  check_asm from   v$controlfile where name like '+%' ''')
        rs = cursor.fetchone()
        if rs[0] == 'NOASM':
            pass
        else:
            lv1,lv2,lv3 = int(d[0]),int(d[1]),int(d[2])
            cursor.execute('''select name,total_m,usable_m,nvl(round(100*(total_m-usable_m)/total_m),0) used_pct
                              from (select a.name
                                   ,a.total_mb/decode(a.type,'EXTERN',1,count(distinct b.failgroup)) total_m
                                   ,a.usable_file_mb                       usable_m
                                   from v$asm_diskgroup a,
                                   v$asm_disk      b
                                   where a.group_number=b.group_number
                                   and   a.database_compatibility<>'0.0.0.0.0'
                             	   --and   a.name ='DATA'
                                   group by a.name,a.total_mb,a.free_mb,a.usable_file_mb,a.type)
                            ''')
            rs = cursor.fetchall() 
            for row in rs:
                if row[3] >=lv1 and row[3] < lv2:   
                    content = "次要告警:磁盘组" + row[0] + "空间使用率" + str(row[3]) + "%,告警阈值" + str(lv1) + "%."
                    alert_id = d[3]
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[3] >=lv2 and row[3] < lv3:
                    content = "主要告警:磁盘组" + row[0] + "空间使用率" + str(row[3]) + "%,告警阈值" + str(lv2) + "%."
                    alert_id = d[3]
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[3] >=lv3:
                    content = "严重告警:磁盘组" + row[0] + "空间使用率" + str(row[3]) + "%,告警阈值" + str(lv3) + "%."
                    alert_id = d[3]
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ":磁盘组" + row[0] + "空间使用率" + str(row[3]) + "%,正常" 
                    wr_log('info',msg)
    #ASM磁盘组状态检查
    d = get_lim_val(inst_id,'asm','dg','state')
    if d is None or d[4] == 0:
        msg = funcName + ':ASM磁盘组状态检查已屏蔽,略过检查'
        wr_log('warning',msg)
    else:
        cursor.execute('''select name,state,type,compatibility,database_compatibility from v$asm_diskgroup''')
        rs = cursor.fetchall()
        for row in rs:
            if row[1] in ['CONNECTED','MOUNTED']:
                msg = funcName + ":磁盘组" + row[0] + "状态为" + str(row[1]) + ",正常"
                wr_log('info',msg) 
            else:
                msg = funcName + ":磁盘组" + row[0] + "状态为" + str(row[1]) + ",异常"
                wr_log('info',msg)
    #ASM磁盘组磁盘大小一致性检查  
    d = get_lim_val(inst_id,'asm','dg','disksize')  
    if d is None or d[4] == 0:
        msg = funcName + ':ASM磁盘组磁盘大小一致性状态检查已屏蔽,略过检查'
        wr_log('warning',msg)
    else:
        cursor.execute('''select a.name,count(distinct b.total_mb) 
                          from v$asm_diskgroup a,v$asm_disk b
                          where a.group_number=b.group_number
                          group by a.name''')
        rs = cursor.fetchall()
        for row in rs:
            if row[1] > 1:
                msg = funcName + ":磁盘组" + row[0] + "磁盘大小不一致"
                wr_log('info',msg)
            else:
                msg = funcName + ":磁盘组" + row[0] + "磁盘大小一致"
                wr_log('info',msg)
    msg = funcName + ':*******************************结束ASM状态检查.***************************************'
    wr_log('info',msg)
                
    
